import stripe
import json
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import FormMixin

from .models import PaymentHistory, Price, Product, Image, ImageAlbum
from .forms import MyForm

stripe.api_key = settings.STRIPE_SECRET_KEY


class ProductListView(ListView):
    model = Product
    context_object_name = "products"
    template_name = "products/product_list.html"

    def get_queryset(self):
        # Filter prodicts with quantity > 0
        return Product.objects.filter(quantity__gt=0)    


class ProductDetailView(FormMixin, DetailView):
    model = Product
    form_class = MyForm
    context_object_name = "product"
    template_name = "products/product_detail.html"

    def get_context_data(self, **kwargs):
        context = super(ProductDetailView, self).get_context_data()
        context["prices"] = Price.objects.filter(product=self.get_object())
        context['form'] = self.form_class()
        product = self.get_object()
        images_by_products = Image.objects.filter(album=product.album)
        context["image_model"] = Image.objects.filter(album=product.album)
        max_quantity = product.quantity
        context['form']['quantity'].field.widget.attrs.update({'max': max_quantity})
        return context


class CreateStripeCheckoutSessionView(View):
    """
    Create a checkout session and redirect the user to Stripe's checkout page
    """

    def post(self, request, *args, **kwargs):
        price = Price.objects.get(id=self.kwargs["pk"])
        price.product.quantity = int(request.POST['quantity'])
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
             shipping_options=[
                {
                  "shipping_rate_data": {
                    "type": "fixed_amount",
                    "fixed_amount": {"amount": 600, "currency": "usd"},
                    "display_name": "USPS First Class",
                    "delivery_estimate": {
                      "minimum": {"unit": "business_day", "value": 5},
                      "maximum": {"unit": "business_day", "value": 7},
                    },
                  },
                },
            ],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(price.price) * 100,
                        "product_data": {
                            "name": price.product.name,
                            "description": price.product.desc,
                        },
                    },
                    "quantity": price.product.quantity,
                }
            ],
            metadata={"product_id": price.product.id, "quantity": price.product.quantity},
            mode="payment",
            success_url=settings.PAYMENT_SUCCESS_URL,
            cancel_url=settings.PAYMENT_CANCEL_URL,
            shipping_address_collection={
                "allowed_countries": ['US']
            },
        )
        return redirect(checkout_session.url)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    """
    Stripe webhook view to handle checkout session completed event.
    """

    def post(self, request, format=None):
        payload = request.body
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
        event = None

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError as e:
            # Invalid payload
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return HttpResponse(status=400)

        if event["type"] == "checkout.session.completed":
            print("Payment successful")
            session = event["data"]["object"]
            customer_email = session["customer_details"]["email"]
            product_id = session["metadata"]["product_id"]
            product = get_object_or_404(Product, id=product_id)

            send_mail(
                subject="Here is your product",
                message=f"Thanks for your purchase. The URL is: {product.url}",
                recipient_list=[customer_email],
                from_email="jchiefelk@gmail.com",
            )

            # Update Product Quantity after a successful order
            data = json.loads(request.body)
            ordered_quantity = data['data']['object']['metadata']['quantity']
            product = Product.objects.get(pk=product_id)
            product_values = Product.objects.filter(pk=product_id).values()
            old_quantity = product_values[0]['quantity']
            product.quantity = old_quantity - int(ordered_quantity)
            product.save()

            PaymentHistory.objects.create(
                email=customer_email, product=product, payment_status="completed"
            )
            
        # Can handle other events here.

        return HttpResponse(status=200)


class SuccessView(TemplateView):
    template_name = "products/success.html"


class CancelView(TemplateView):
    template_name = "products/cancel.html"


class ContactView(TemplateView):
    template_name = "products/contact.html"
