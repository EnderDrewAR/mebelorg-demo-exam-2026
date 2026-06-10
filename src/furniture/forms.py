from django import forms
from django.forms import inlineformset_factory

from .models import Order, OrderItem, Product, Role, User


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "article",
            "name",
            "category",
            "description",
            "manufacturer",
            "supplier",
            "price",
            "unit",
            "stock_quantity",
            "discount",
            "image",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "price": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
            "stock_quantity": forms.NumberInput(attrs={"min": 0}),
            "discount": forms.NumberInput(attrs={"min": 0, "max": 100, "step": "0.01"}),
            "image": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Размер изображения не должен превышать 5 МБ.")
        return image


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "status",
            "pickup_point",
            "customer",
            "order_date",
            "delivery_date",
            "pickup_code",
        ]
        widgets = {
            "order_date": forms.DateInput(attrs={"type": "date"}),
            "delivery_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = User.objects.filter(
            role__code=Role.Codes.CLIENT,
        ).order_by("full_name")


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 1}),
        }


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)

