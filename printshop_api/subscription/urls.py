# subscription/urls.py

from django.urls import path

from . import views

app_name = "subscription"

urlpatterns = [
    path(
        "shops/<slug:shop_slug>/subscription/",
        views.subscription_detail,
        name="subscription-detail",
    ),
    path(
        "shops/<slug:shop_slug>/payments/mpesa/stk-push/",
        views.stk_push_initiate,
        name="stk-push",
    ),
    path(
        "plans/",
        views.plans_list,
        name="plans-list",
    ),
    path(
        "payments/<int:pk>/status/",
        views.payment_status,
        name="payment-status",
    ),
    path(
        "payments/mpesa/callback/",
        views.mpesa_callback,
        name="mpesa-callback",
    ),
]
