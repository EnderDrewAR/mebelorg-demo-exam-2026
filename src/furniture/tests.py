from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Order, Product, Role, User


class DemoImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_demo_data")

    def test_import_counts(self):
        self.assertEqual(User.objects.count(), 10)
        self.assertEqual(Product.objects.count(), 10)
        self.assertEqual(Order.objects.count(), 10)

    def test_passwords_are_hashed_and_work(self):
        user = User.objects.get(username="94d5ous@gmail.com")
        self.assertNotEqual(user.password, "uzWC67")
        self.assertTrue(user.check_password("uzWC67"))

    def test_discounted_price(self):
        product = Product.objects.get(article="G843H5")
        self.assertEqual(product.discounted_price, Decimal("6602.25"))


class AccessAndCatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_demo_data")

    def login_as(self, role_code):
        user = User.objects.filter(role__code=role_code).first()
        self.client.force_login(user)
        return user

    def test_guest_can_view_products_without_filters(self):
        response = self.client.get(reverse("product_list"), {"q": "диван"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["products"]), 10)
        self.assertNotContains(response, 'data-live-filter')

    def test_manager_can_search_and_filter(self):
        self.login_as(Role.Codes.MANAGER)
        response = self.client.get(
            reverse("product_list"),
            {"q": "Инвуд Диван", "discount": "15+", "sort": "price_desc"},
        )
        self.assertEqual(response.status_code, 200)
        articles = list(response.context["products"].values_list("article", flat=True))
        self.assertEqual(articles, ["F325D4"])

    def test_manager_cannot_add_product(self):
        self.login_as(Role.Codes.MANAGER)
        response = self.client.get(reverse("product_create"))
        self.assertRedirects(response, reverse("product_list"))

    def test_admin_can_open_product_form(self):
        self.login_as(Role.Codes.ADMIN)
        response = self.client.get(reverse("product_create"))
        self.assertEqual(response.status_code, 200)

    def test_product_in_order_cannot_be_deleted(self):
        self.login_as(Role.Codes.ADMIN)
        product = Product.objects.first()
        response = self.client.post(reverse("product_delete", args=[product.pk]))
        self.assertRedirects(response, reverse("product_list"))
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

