from django.urls import path

from .views import (
    CancelView,
    CreateStripeCheckoutSessionView,
    ProductDetailView,
    ProductListView,
    StripeWebhookView,
    SuccessView,
    ContactView
)

app_name = "products"

urlpatterns = [
    path("", ProductListView.as_view(), name="product-list"),
    path("<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path(
        "create-checkout-session/<int:pk>/<int:quantity>",
        CreateStripeCheckoutSessionView.as_view(),
        name="create-checkout-session",
    ),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("success/", SuccessView.as_view(), name="success"),
    path("cancel/", CancelView.as_view(), name="cancel"),
    path("contact/", ContactView.as_view(), name="product")
]
