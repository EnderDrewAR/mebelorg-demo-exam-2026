from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import roles_required
from .forms import OrderForm, OrderItemFormSet, ProductForm
from .models import Order, Product, Role


def product_list(request):
    products = Product.objects.select_related(
        "category",
        "manufacturer",
        "supplier",
        "unit",
    )
    role_code = request.user.role_code if request.user.is_authenticated else ""
    can_manage = role_code in {Role.Codes.MANAGER, Role.Codes.ADMIN}

    query = request.GET.get("q", "").strip()
    discount_range = request.GET.get("discount", "all")
    sort = request.GET.get("sort", "")

    if can_manage:
        for term in query.split():
            products = products.filter(
                Q(article__icontains=term)
                | Q(name__icontains=term)
                | Q(description__icontains=term)
                | Q(category__name__icontains=term)
                | Q(manufacturer__name__icontains=term)
                | Q(supplier__name__icontains=term)
                | Q(unit__name__icontains=term)
            )

        discount_filters = {
            "0-10": Q(discount__gte=0, discount__lt=11),
            "11-14": Q(discount__gte=11, discount__lt=15),
            "15+": Q(discount__gte=15),
        }
        if discount_range in discount_filters:
            products = products.filter(discount_filters[discount_range])

        sort_fields = {
            "price_asc": "price",
            "price_desc": "-price",
            "stock_asc": "stock_quantity",
            "stock_desc": "-stock_quantity",
        }
        if sort in sort_fields:
            products = products.order_by(sort_fields[sort], "id")

    return render(
        request,
        "furniture/product_list.html",
        {
            "products": products,
            "query": query if can_manage else "",
            "discount_range": discount_range if can_manage else "all",
            "sort": sort if can_manage else "",
        },
    )


@roles_required(Role.Codes.ADMIN)
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        messages.success(request, f"Товар «{product.name}» добавлен.")
        return redirect("product_list")
    return render(
        request,
        "furniture/product_form.html",
        {"form": form, "title": "Добавление товара", "product": None},
    )


@roles_required(Role.Codes.ADMIN)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Товар «{product.name}» обновлен.")
        return redirect("product_list")
    return render(
        request,
        "furniture/product_form.html",
        {"form": form, "title": "Редактирование товара", "product": product},
    )


@roles_required(Role.Codes.ADMIN)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        try:
            product.delete()
        except ProtectedError:
            messages.error(
                request,
                "Товар нельзя удалить, потому что он присутствует в заказе.",
            )
        else:
            messages.success(request, "Товар удален.")
        return redirect("product_list")
    return render(
        request,
        "furniture/confirm_delete.html",
        {
            "title": "Удаление товара",
            "object_name": product.name,
            "cancel_url": "product_list",
        },
    )


@roles_required(Role.Codes.MANAGER, Role.Codes.ADMIN)
def order_list(request):
    orders = Order.objects.select_related(
        "status",
        "pickup_point",
        "customer",
    ).prefetch_related("items__product")
    return render(request, "furniture/order_list.html", {"orders": orders})


@roles_required(Role.Codes.ADMIN)
@transaction.atomic
def order_create(request):
    order = Order()
    form = OrderForm(request.POST or None, instance=order)
    formset = OrderItemFormSet(request.POST or None, instance=order)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        order = form.save()
        formset.instance = order
        formset.save()
        messages.success(request, f"Заказ №{order.pk} добавлен.")
        return redirect("order_list")
    return render(
        request,
        "furniture/order_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Добавление заказа",
            "order": None,
        },
    )


@roles_required(Role.Codes.ADMIN)
@transaction.atomic
def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    form = OrderForm(request.POST or None, instance=order)
    formset = OrderItemFormSet(request.POST or None, instance=order)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, f"Заказ №{order.pk} обновлен.")
        return redirect("order_list")
    return render(
        request,
        "furniture/order_form.html",
        {
            "form": form,
            "formset": formset,
            "title": f"Редактирование заказа №{order.pk}",
            "order": order,
        },
    )


@roles_required(Role.Codes.ADMIN)
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.delete()
        messages.success(request, "Заказ удален.")
        return redirect("order_list")
    return render(
        request,
        "furniture/confirm_delete.html",
        {
            "title": f"Удаление заказа №{order.pk}",
            "object_name": f"заказ №{order.pk}",
            "cancel_url": "order_list",
        },
    )

