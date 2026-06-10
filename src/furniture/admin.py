from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Category,
    Manufacturer,
    Order,
    OrderItem,
    OrderStatus,
    PickupPoint,
    Product,
    Role,
    Supplier,
    Unit,
    User,
)


@admin.register(User)
class FurnitureUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("МебельОрг", {"fields": ("full_name", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("МебельОрг", {"fields": ("full_name", "role")}),
    )
    list_display = ("username", "full_name", "role", "is_active")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "order_date", "delivery_date", "customer", "status")
    inlines = [OrderItemInline]


admin.site.register(Role)
admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Manufacturer)
admin.site.register(Unit)
admin.site.register(Product)
admin.site.register(PickupPoint)
admin.site.register(OrderStatus)

