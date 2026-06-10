import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from shutil import copy2

from django.conf import settings
from django.core.management import BaseCommand
from django.core.management.color import no_style
from django.db import connection, transaction

from furniture.models import (
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


class Command(BaseCommand):
    help = "Импортирует нормализованные CSV-файлы демонстрационного экзамена."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Повторно установить исходные пароли всем импортированным пользователям.",
        )

    def read_csv(self, name):
        csv_path = Path(settings.PROJECT_ROOT) / "data" / "csv" / f"{name}.csv"
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))

    @transaction.atomic
    def handle(self, *args, **options):
        self.prepare_media()

        roles = {}
        for row in self.read_csv("roles"):
            role, _ = Role.objects.update_or_create(
                id=int(row["id"]),
                defaults={"code": row["code"], "name": row["name"]},
            )
            roles[role.id] = role

        users = {}
        for row in self.read_csv("users"):
            user, created = User.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "username": row["username"],
                    "email": row["username"],
                    "full_name": row["full_name"],
                    "role": roles[int(row["role_id"])],
                    "is_active": True,
                    "is_staff": roles[int(row["role_id"])].code == Role.Codes.ADMIN,
                },
            )
            if created or options["reset_passwords"] or not user.password:
                user.set_password(row["initial_password"])
                user.save(update_fields=["password"])
            users[user.id] = user

        categories = self.import_reference("categories", Category)
        suppliers = self.import_reference("suppliers", Supplier)
        manufacturers = self.import_reference("manufacturers", Manufacturer)
        units = self.import_reference("units", Unit)
        statuses = self.import_reference("order_statuses", OrderStatus)

        pickup_points = {}
        for row in self.read_csv("pickup_points"):
            point, _ = PickupPoint.objects.update_or_create(
                id=int(row["id"]),
                defaults={"address": row["address"]},
            )
            pickup_points[point.id] = point

        products = {}
        for row in self.read_csv("products"):
            product, _ = Product.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "article": row["article"],
                    "name": row["name"],
                    "unit": units[int(row["unit_id"])],
                    "price": Decimal(row["price"]),
                    "supplier": suppliers[int(row["supplier_id"])],
                    "manufacturer": manufacturers[int(row["manufacturer_id"])],
                    "category": categories[int(row["category_id"])],
                    "discount": Decimal(row["discount"]),
                    "stock_quantity": int(row["stock_quantity"]),
                    "description": row["description"],
                    "image": f"products/{row['image_path']}" if row["image_path"] else "",
                },
            )
            products[product.id] = product

        orders = {}
        for row in self.read_csv("orders"):
            order, _ = Order.objects.update_or_create(
                id=int(row["id"]),
                defaults={
                    "order_date": date.fromisoformat(row["order_date"]),
                    "delivery_date": date.fromisoformat(row["delivery_date"]),
                    "pickup_point": pickup_points[int(row["pickup_point_id"])],
                    "customer": users[int(row["customer_id"])],
                    "pickup_code": int(row["pickup_code"]),
                    "status": statuses[int(row["status_id"])],
                },
            )
            orders[order.id] = order

        imported_item_ids = []
        for row in self.read_csv("order_items"):
            item_id = int(row["id"])
            OrderItem.objects.update_or_create(
                id=item_id,
                defaults={
                    "order": orders[int(row["order_id"])],
                    "product": products[int(row["product_id"])],
                    "quantity": int(row["quantity"]),
                },
            )
            imported_item_ids.append(item_id)

        OrderItem.objects.exclude(id__in=imported_item_ids).delete()
        self.reset_sequences()
        self.stdout.write(
            self.style.SUCCESS(
                "Импорт завершен: 10 пользователей, 10 товаров, 10 заказов.",
            )
        )

    def import_reference(self, csv_name, model):
        objects = {}
        for row in self.read_csv(csv_name):
            instance, _ = model.objects.update_or_create(
                id=int(row["id"]),
                defaults={"name": row["name"]},
            )
            objects[instance.id] = instance
        return objects

    def prepare_media(self):
        source_dir = Path(settings.PROJECT_ROOT) / "seed_media" / "products"
        target_dir = Path(settings.MEDIA_ROOT) / "products"
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in source_dir.iterdir():
            if source.is_file():
                target = target_dir / source.name
                if not target.exists():
                    copy2(source, target)

    def reset_sequences(self):
        models = [
            Role,
            User,
            Category,
            Supplier,
            Manufacturer,
            Unit,
            Product,
            PickupPoint,
            OrderStatus,
            Order,
            OrderItem,
        ]
        statements = connection.ops.sequence_reset_sql(no_style(), models)
        if statements:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
