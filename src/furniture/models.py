from decimal import Decimal
from io import BytesIO

from PIL import Image
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Role(models.Model):
    class Codes(models.TextChoices):
        ADMIN = "admin", "Администратор"
        MANAGER = "manager", "Менеджер"
        CLIENT = "client", "Авторизованный клиент"

    code = models.CharField("Код", max_length=20, unique=True, choices=Codes.choices)
    name = models.CharField("Название", max_length=80, unique=True)

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        ordering = ["id"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    full_name = models.CharField("ФИО", max_length=255)
    role = models.ForeignKey(
        Role,
        verbose_name="Роль",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def get_full_name(self):
        return self.full_name or self.username

    @property
    def role_code(self):
        return self.role.code if self.role_id else ""


class NamedReference(models.Model):
    name = models.CharField("Название", max_length=255, unique=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(NamedReference):
    class Meta(NamedReference.Meta):
        verbose_name = "Категория"
        verbose_name_plural = "Категории"


class Supplier(NamedReference):
    class Meta(NamedReference.Meta):
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"


class Manufacturer(NamedReference):
    class Meta(NamedReference.Meta):
        verbose_name = "Производитель"
        verbose_name_plural = "Производители"


class Unit(NamedReference):
    class Meta(NamedReference.Meta):
        verbose_name = "Единица измерения"
        verbose_name_plural = "Единицы измерения"


class Product(models.Model):
    article = models.CharField("Артикул", max_length=30, unique=True)
    name = models.CharField("Наименование", max_length=500)
    unit = models.ForeignKey(Unit, verbose_name="Единица измерения", on_delete=models.PROTECT)
    price = models.DecimalField(
        "Цена",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    supplier = models.ForeignKey(
        Supplier,
        verbose_name="Поставщик",
        on_delete=models.PROTECT,
    )
    manufacturer = models.ForeignKey(
        Manufacturer,
        verbose_name="Производитель",
        on_delete=models.PROTECT,
    )
    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        on_delete=models.PROTECT,
    )
    discount = models.DecimalField(
        "Действующая скидка, %",
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    stock_quantity = models.PositiveIntegerField("Количество на складе", default=0)
    description = models.TextField("Описание", blank=True)
    image = models.ImageField("Фото", upload_to="products/", blank=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["id"]

    def __str__(self):
        return f"{self.article} — {self.name}"

    @property
    def discounted_price(self):
        multiplier = Decimal("1") - self.discount / Decimal("100")
        return (self.price * multiplier).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        old_image_name = None
        if self.pk:
            old_image_name = (
                Product.objects.filter(pk=self.pk)
                .values_list("image", flat=True)
                .first()
            )

        if self.image and not self.image._committed:
            source = Image.open(self.image)
            source.thumbnail((300, 200))
            if source.mode not in ("RGB", "L"):
                source = source.convert("RGB")
            output = BytesIO()
            image_format = "PNG" if self.image.name.lower().endswith(".png") else "JPEG"
            source.save(output, format=image_format, quality=88, optimize=True)
            self.image.save(
                self.image.name,
                ContentFile(output.getvalue()),
                save=False,
            )

        super().save(*args, **kwargs)

        if old_image_name and old_image_name != self.image.name:
            self.image.storage.delete(old_image_name)

    def delete(self, *args, **kwargs):
        image_name = self.image.name
        storage = self.image.storage if image_name else None
        super().delete(*args, **kwargs)
        if storage and image_name:
            storage.delete(image_name)


class PickupPoint(models.Model):
    address = models.CharField("Адрес", max_length=500, unique=True)

    class Meta:
        verbose_name = "Пункт выдачи"
        verbose_name_plural = "Пункты выдачи"
        ordering = ["id"]

    def __str__(self):
        return self.address


class OrderStatus(NamedReference):
    class Meta(NamedReference.Meta):
        verbose_name = "Статус заказа"
        verbose_name_plural = "Статусы заказов"


class Order(models.Model):
    order_date = models.DateField("Дата заказа")
    delivery_date = models.DateField("Дата выдачи")
    pickup_point = models.ForeignKey(
        PickupPoint,
        verbose_name="Пункт выдачи",
        on_delete=models.PROTECT,
    )
    customer = models.ForeignKey(
        User,
        verbose_name="Клиент",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    pickup_code = models.PositiveIntegerField("Код получения", unique=True)
    status = models.ForeignKey(
        OrderStatus,
        verbose_name="Статус",
        on_delete=models.PROTECT,
    )
    products = models.ManyToManyField(Product, through="OrderItem", related_name="orders")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["id"]

    def __str__(self):
        return f"Заказ №{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(
        "Количество",
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="unique_product_in_order",
            )
        ]

    def __str__(self):
        return f"{self.order}: {self.product.article} × {self.quantity}"

