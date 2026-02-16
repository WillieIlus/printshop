# subscription/views.py

from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from shops.models import Shop
from shops.permissions import IsShopManagerOrOwner, IsShopMember

from .models import MpesaStkRequest, Subscription, SubscriptionPlan
from .mpesa_services import MPesaStkPushService


def get_subscription_for_shop(shop: Shop):
    """Get or create a subscription for the shop with default plan."""
    try:
        return shop.subscription
    except Subscription.DoesNotExist:
        plan = SubscriptionPlan.objects.filter(is_active=True).order_by("price").first()
        if not plan:
            return None
        now = timezone.now()
        period_end = now + timedelta(days=plan.days_in_period)
        return Subscription.objects.create(
            shop=shop,
            plan=plan,
            status=Subscription.Status.TRIAL,
            current_period_start=now,
            current_period_end=period_end,
            next_billing_date=period_end,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsShopMember])
def subscription_detail(request, shop_slug):
    """
    GET /api/shops/:slug/subscription/
    Returns plan, limits, usage, expires_at, status for the shop.
    """
    shop = get_object_or_404(Shop, slug=shop_slug)
    sub = get_subscription_for_shop(shop)
    if not sub:
        return Response({
            "plan": None,
            "plan_name": "Free",
            "status": "TRIAL",
            "limits": {
                "max_printing_machines": 1,
                "max_finishing_machines": 0,
            },
            "usage": {
                "printing_machines": 0,
                "finishing_machines": 0,
            },
            "expires_at": None,
            "can_add_printing_machine": True,
            "can_add_finishing_machine": False,
        })

    from inventory.models import Machine

    printing_count = Machine.objects.filter(
        shop=shop,
        machine_type__in=[Machine.MachineType.DIGITAL, Machine.MachineType.LARGE_FORMAT, Machine.MachineType.OFFSET],
    ).count()
    finishing_count = Machine.objects.filter(
        shop=shop,
        machine_type=Machine.MachineType.FINISHING,
    ).count()

    plan = sub.plan
    max_printing = plan.max_printing_machines
    max_finishing = plan.max_finishing_machines

    is_active = sub.status in [Subscription.Status.ACTIVE, Subscription.Status.TRIAL]
    not_expired = sub.current_period_end and sub.current_period_end > timezone.now()

    can_add_printing = is_active and not_expired and (max_printing == 0 or printing_count < max_printing)
    can_add_finishing = is_active and not_expired and (max_finishing == 0 or finishing_count < max_finishing)

    return Response({
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "plan_type": plan.plan_type,
            "price": str(plan.price),
            "billing_period": plan.billing_period,
        },
        "plan_name": plan.name,
        "status": sub.status,
        "limits": {
            "max_printing_machines": max_printing,
            "max_finishing_machines": max_finishing,
        },
        "usage": {
            "printing_machines": printing_count,
            "finishing_machines": finishing_count,
        },
        "expires_at": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "can_add_printing_machine": can_add_printing,
        "can_add_finishing_machine": can_add_finishing,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def plans_list(request):
    """
    GET /api/plans/
    List available subscription plans for upgrade.
    """
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by("price")
    return Response([
        {
            "id": p.id,
            "name": p.name,
            "plan_type": p.plan_type,
            "price": str(p.price),
            "billing_period": p.billing_period,
            "max_printing_machines": p.max_printing_machines,
            "max_finishing_machines": p.max_finishing_machines,
        }
        for p in plans
    ])


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsShopManagerOrOwner])
def stk_push_initiate(request, shop_slug):
    """
    POST /api/shops/:slug/payments/mpesa/stk-push/
    Body: { "plan_id": 1, "phone": "0712345678" }
    Initiates M-Pesa STK push for subscription upgrade.
    """
    shop = get_object_or_404(Shop, slug=shop_slug)
    plan_id = request.data.get("plan_id")
    phone = request.data.get("phone", "").strip()
    if not plan_id or not phone:
        return Response(
            {"error": "plan_id and phone are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    amount = plan.price

    stk_service = MPesaStkPushService()
    try:
        result = stk_service.initiate_stk_push(
            phone=phone,
            amount=amount,
            account_ref=f"shop-{shop.id}-plan-{plan.id}",
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    merchant_request_id = result.get("MerchantRequestID", "")
    checkout_request_id = result.get("CheckoutRequestID", "")
    response_code = result.get("ResponseCode", "")
    if response_code != "0":
        return Response(
            {"error": result.get("CustomerMessage", "STK push failed")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    stk_request = MpesaStkRequest.objects.create(
        shop=shop,
        user=request.user,
        plan=plan,
        amount=amount,
        phone=phone,
        checkout_request_id=checkout_request_id,
        merchant_request_id=merchant_request_id,
        status=MpesaStkRequest.Status.INITIATED,
        raw_request_payload=result,
    )

    return Response({
        "id": stk_request.id,
        "checkout_request_id": checkout_request_id,
        "message": "Complete payment on your phone",
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_status(request, pk):
    """
    GET /api/payments/:id/status/
    Poll payment status. Returns status and subscription info on success.
    """
    stk = get_object_or_404(MpesaStkRequest, pk=pk, user=request.user)
    return Response({
        "id": stk.id,
        "status": stk.status,
        "shop_slug": stk.shop.slug,
    })


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])  # No auth - Daraja callback
def mpesa_callback(request):
    """
    POST /api/payments/mpesa/callback/
    Daraja STK push callback. Updates MpesaStkRequest and activates subscription on success.
    """
    data = request.data
    body = data.get("Body", {})
    stk_callback = body.get("stkCallback", {})
    checkout_request_id = stk_callback.get("CheckoutRequestID", "")
    result_code = stk_callback.get("ResultCode", -1)
    result_desc = stk_callback.get("ResultDesc", "")

    try:
        stk = MpesaStkRequest.objects.get(
            checkout_request_id=checkout_request_id,
            status=MpesaStkRequest.Status.INITIATED,
        )
    except MpesaStkRequest.DoesNotExist:
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

    stk.raw_callback_payload = data
    stk.save()

    if result_code == 0:
        callback_metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        receipt = ""
        for item in callback_metadata:
            if item.get("Name") == "MpesaReceiptNumber":
                receipt = str(item.get("Value", ""))
                break

        stk.status = MpesaStkRequest.Status.SUCCESS
        stk.mpesa_receipt_number = receipt
        stk.save()

        # Activate subscription
        shop = stk.shop
        plan = stk.plan
        sub = get_subscription_for_shop(shop)
        if sub:
            now = timezone.now()
            period_end = now + timedelta(days=plan.days_in_period)
            sub.plan = plan
            sub.status = Subscription.Status.ACTIVE
            sub.current_period_start = now
            sub.current_period_end = period_end
            sub.next_billing_date = period_end
            sub.last_payment_date = now
            sub.save()

        from .models import Payment

        if sub:
            Payment.objects.create(
                subscription=sub,
                amount=stk.amount,
                payment_method=Payment.PaymentMethod.MPESA_C2B,
                status=Payment.PaymentStatus.COMPLETED,
                mpesa_receipt_number=receipt,
                mpesa_phone_number=stk.phone,
                mpesa_request_id=checkout_request_id,
                payment_date=now,
                period_start=sub.current_period_start,
                period_end=sub.current_period_end,
                description=f"Upgrade to {plan.name}",
                metadata={"mpesa_stk_request_id": stk.id},
            )
    else:
        stk.status = MpesaStkRequest.Status.FAILED
        stk.save()

    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
