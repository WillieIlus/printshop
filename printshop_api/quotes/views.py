# quotes/views.py

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from shops.models import Shop
from shops.permissions import IsShopMember, IsShopManagerOrOwner, IsShopOwner

from .models import (
    ProductTemplate,
    Quote,
    QuoteItem,
    QuoteItemPart,
    QuoteItemFinishing,
)
from .serializers import (
    ProductTemplateSerializer,
    ProductTemplateListSerializer,
    QuoteListSerializer,
    QuoteDetailSerializer,
    QuoteCreateSerializer,
    QuoteStatusUpdateSerializer,
    QuoteItemSerializer,
    QuoteItemCreateSerializer,
    QuoteItemPartSerializer,
    QuoteItemFinishingSerializer,
    CustomerQuoteRequestSerializer,
)
from .services import QuoteCalculator


# =============================================================================
# Base Mixin for Shop-scoped ViewSets
# =============================================================================

class ShopScopedMixin:
    """Mixin to handle shop scoping for quote viewsets."""
    
    def get_shop(self):
        """Get and cache the shop from URL."""
        if not hasattr(self, "_shop"):
            self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context


# =============================================================================
# Product Template ViewSet (Shop-scoped)
# =============================================================================

class ProductTemplateViewSet(ShopScopedMixin, viewsets.ModelViewSet):
    """
    Manage shop product templates (presets for quick quoting).
    Endpoint: /api/shops/{shop_slug}/product-templates/
    """
    
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProductTemplateListSerializer
        return ProductTemplateSerializer

    def get_queryset(self):
        return ProductTemplate.objects.filter(shop=self.get_shop())

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), IsShopMember()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]


# =============================================================================
# Quote ViewSet (Shop-scoped)
# =============================================================================

class QuoteViewSet(ShopScopedMixin, viewsets.ModelViewSet):
    """
    Manage quotes for a shop.
    Endpoint: /api/shops/{shop_slug}/quotes/
    
    Features:
    - List/filter quotes by status
    - Create new quotes
    - Update quote details
    - Calculate/recalculate totals
    - Change status
    """
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "user"]
    search_fields = ["reference", "title", "user__email"]
    ordering_fields = ["created_at", "grand_total", "valid_until"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return QuoteListSerializer
        if self.action == "create":
            return QuoteCreateSerializer
        return QuoteDetailSerializer

    def get_queryset(self):
        return Quote.objects.filter(
            shop=self.get_shop()
        ).select_related(
            "shop", "user", "source_template"
        ).prefetch_related(
            "items__parts",
            "items__finishing"
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), IsShopMember()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]

    @action(detail=True, methods=["post"])
    def calculate(self, request, shop_slug=None, pk=None):
        """
        Recalculate quote totals.
        POST /api/shops/{shop_slug}/quotes/{id}/calculate/
        """
        quote = self.get_object()
        calculator = QuoteCalculator()
        
        try:
            total = calculator.calculate_quote_total(quote)
            quote.refresh_from_db()
            return Response({
                "message": "Quote recalculated successfully",
                "net_total": str(quote.net_total),
                "tax_amount": str(quote.tax_amount),
                "grand_total": str(quote.grand_total),
            })
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def update_status(self, request, shop_slug=None, pk=None):
        """
        Update quote status.
        POST /api/shops/{shop_slug}/quotes/{id}/update-status/
        {
            "status": "SENT",
            "internal_notes": "Sent via email"
        }
        """
        quote = self.get_object()
        serializer = QuoteStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        quote.status = serializer.validated_data["status"]
        if "internal_notes" in serializer.validated_data:
            quote.internal_notes = serializer.validated_data["internal_notes"]
        quote.save()
        
        return Response({
            "message": f"Quote status updated to {quote.get_status_display()}",
            "status": quote.status,
        })

    @action(detail=True, methods=["post"])
    def duplicate(self, request, shop_slug=None, pk=None):
        """
        Duplicate a quote.
        POST /api/shops/{shop_slug}/quotes/{id}/duplicate/
        """
        original = self.get_object()
        
        # Create new quote
        new_quote = Quote.objects.create(
            shop=original.shop,
            user=original.user,
            source_template=original.source_template,
            title=f"{original.title} (Copy)",
            customer_notes=original.customer_notes,
            status=Quote.Status.DRAFT,
        )
        
        # Duplicate items
        for item in original.items.all():
            new_item = QuoteItem.objects.create(
                quote=new_quote,
                name=item.name,
                quantity=item.quantity,
            )
            
            # Duplicate parts
            for part in item.parts.all():
                QuoteItemPart.objects.create(
                    item=new_item,
                    name=part.name,
                    final_width=part.final_width,
                    final_height=part.final_height,
                    material=part.material,
                    preferred_stock=part.preferred_stock,
                    machine=part.machine,
                    print_sides=part.print_sides,
                )
            
            # Duplicate finishing
            for finishing in item.finishing.all():
                QuoteItemFinishing.objects.create(
                    item=new_item,
                    finishing_price=finishing.finishing_price,
                )
        
        # Calculate totals
        calculator = QuoteCalculator()
        calculator.calculate_quote_total(new_quote)
        
        return Response({
            "message": "Quote duplicated successfully",
            "new_quote_id": new_quote.id,
            "new_quote_reference": new_quote.reference,
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# Quote Item ViewSet (Nested under Quote)
# =============================================================================

class QuoteItemViewSet(viewsets.ModelViewSet):
    """
    Manage items within a quote.
    Endpoint: /api/shops/{shop_slug}/quotes/{quote_id}/items/
    """
    
    def get_quote(self):
        if not hasattr(self, "_quote"):
            shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
            self._quote = get_object_or_404(
                Quote, 
                id=self.kwargs["quote_id"],
                shop=shop
            )
        return self._quote

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return QuoteItemCreateSerializer
        return QuoteItemSerializer

    def get_queryset(self):
        return QuoteItem.objects.filter(
            quote=self.get_quote()
        ).prefetch_related("parts", "finishing")

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), IsShopMember()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]

    def perform_create(self, serializer):
        serializer.save(quote=self.get_quote())

    def perform_update(self, serializer):
        serializer.save()
        # Recalculate quote after item update
        calculator = QuoteCalculator()
        calculator.calculate_quote_total(self.get_quote())

    def perform_destroy(self, instance):
        quote = self.get_quote()
        instance.delete()
        # Recalculate quote after item deletion
        calculator = QuoteCalculator()
        calculator.calculate_quote_total(quote)


# =============================================================================
# Customer Quote Request View (Public)
# =============================================================================

class CustomerQuoteRequestView(APIView):
    """
    Public endpoint for customers to request quotes without authentication.
    Endpoint: POST /api/shops/{shop_slug}/request-quote/
    
    Creates a quote in PENDING status for shop to review.
    """
    
    permission_classes = [permissions.AllowAny]

    def post(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        
        serializer = CustomerQuoteRequestSerializer(data={
            **request.data,
            "shop_id": shop.id
        })
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Get or create user (simplified - in production would have proper flow)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user, created = User.objects.get_or_create(
            email=data["customer_email"],
            defaults={
                "first_name": data["customer_name"].split()[0] if data["customer_name"] else "",
                "last_name": " ".join(data["customer_name"].split()[1:]) if len(data["customer_name"].split()) > 1 else "",
            }
        )
        
        # Build description with specs
        description = data.get("description", "")
        specs = []
        if data.get("width_mm") and data.get("height_mm"):
            specs.append(f"Size: {data['width_mm']}mm × {data['height_mm']}mm")
        if data.get("paper_gsm"):
            specs.append(f"Paper: {data['paper_gsm']}gsm")
        if data.get("print_sides"):
            specs.append(f"Sides: {data['print_sides']}")
        if data.get("customer_phone"):
            specs.append(f"Phone: {data['customer_phone']}")
        
        if specs:
            description = f"{description}\n\nSpecifications:\n" + "\n".join(specs)
        
        # Create quote
        quote = Quote.objects.create(
            shop=shop,
            user=user,
            title=data["product_name"],
            customer_notes=description.strip(),
            status=Quote.Status.PENDING,
        )
        
        # Create item
        QuoteItem.objects.create(
            quote=quote,
            name=data["product_name"],
            quantity=data["quantity"],
        )
        
        return Response({
            "message": "Quote request submitted successfully",
            "quote_reference": quote.reference,
            "status": "We will contact you shortly with a quote.",
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# My Quotes View (For authenticated customers)
# =============================================================================

class MyQuotesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View quotes for the authenticated user (customer view).
    Endpoint: /api/my-quotes/
    """
    
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "shop"]
    ordering_fields = ["created_at", "grand_total"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return QuoteListSerializer
        return QuoteDetailSerializer

    def get_queryset(self):
        return Quote.objects.filter(
            user=self.request.user
        ).select_related(
            "shop", "source_template"
        ).prefetch_related(
            "items"
        )

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Customer accepts a quote."""
        quote = self.get_object()
        if quote.status != Quote.Status.SENT:
            return Response({
                "error": "Can only accept quotes that have been sent"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        quote.status = Quote.Status.ACCEPTED
        quote.save()
        
        return Response({
            "message": "Quote accepted",
            "status": quote.status,
        })

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Customer rejects a quote."""
        quote = self.get_object()
        if quote.status != Quote.Status.SENT:
            return Response({
                "error": "Can only reject quotes that have been sent"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        quote.status = Quote.Status.REJECTED
        quote.save()
        
        return Response({
            "message": "Quote rejected",
            "status": quote.status,
        })
