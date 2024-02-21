from django import forms
from .models import Product

class MyForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['quantity']
