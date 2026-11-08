import os
import unittest

from empire import create_app
from empire.config import TestConfig
from empire.extensions import db
from empire.models import CardTier, Order, PoopCard, Product
from empire.seed import ADMIN_EMAIL, ADMIN_PASSWORD


class EmpireFlow(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_home_brand_and_photos(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Какашечная Империя Руслана Триллионеркина", html)
        self.assertIn("Мы не просто продаём какашки. Мы управляем какашечной экономикой мира.", html)
        self.assertIn("ПОЛУЧИ СВОЮ КАКАШЕЧНУЮ КАРТУ", html)
        self.assertIn("images/ruslan.jpg", html)
        self.assertIn("images/tishka.jpg", html)
        self.assertIn("Тишка лично рекомендует свои хлопья!", html)

    def test_card_discount_and_bonus(self):
        self.client.post("/register", data={"name": "Тест Миллиардер", "email": "t@poop.empire", "password": "secret1", "phone": "+79990001122"})
        issued = self.client.post("/card/issue", data={"design": "gold", "holder": "Тест Миллиардер"}, follow_redirects=True)
        self.assertIn("POOP GOLD", issued.get_data(as_text=True))
        card = PoopCard.query.filter_by(holder_name="ТЕСТ МИЛЛИАРДЕР").one()
        self.assertEqual(len(card.number.replace(" ", "")), 16)
        product = Product.query.filter_by(slug="tishkiny-hlopya").one()
        blocked = self.client.post("/cart/add", data={"product_id": Product.query.filter_by(slug="konjak").one().id}, follow_redirects=True)
        self.assertIn("витрине", blocked.get_data(as_text=True))
        self.client.post("/cart/add", data={"product_id": product.id, "qty": 1})
        order_page = self.client.post(
            "/checkout",
            data={
                "name": "Тест Миллиардер",
                "email": "t@poop.empire",
                "phone": "+79990001122",
                "city": "Уфа",
                "address": "Кабинет 1",
                "delivery": "pickup",
                "payment": "demo",
            },
            follow_redirects=True,
        )
        self.assertEqual(order_page.status_code, 200)
        order = Order.query.filter_by(email="t@poop.empire", is_demo=False).one()
        self.assertEqual(order.subtotal_kop, 54900)
        self.assertEqual(order.card_discount_kop, 5490)
        self.assertEqual(order.total_kop, 49410)
        self.assertEqual(card.bonus_kop, 988)

        tier = CardTier.query.filter_by(slug="gold").one()
        self.client.post("/logout")
        self.client.post("/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        saved = self.client.post("/admin/tiers", data={"id": tier.id, "name": tier.name, "discount": 20, "tagline": tier.tagline, "active": "1"})
        self.assertEqual(saved.status_code, 302)
        self.client.post("/logout")
        self.client.post("/login", data={"email": "t@poop.empire", "password": "secret1"})
        self.client.post("/cart/add", data={"product_id": product.id, "qty": 1})
        self.client.post(
            "/checkout",
            data={
                "name": "Тест Миллиардер",
                "email": "t@poop.empire",
                "phone": "+79990001122",
                "city": "Уфа",
                "address": "Кабинет 1",
                "delivery": "pickup",
                "payment": "demo",
                "spend_bonus": "1",
            },
            follow_redirects=True,
        )
        second = Order.query.filter_by(email="t@poop.empire", is_demo=False).order_by(Order.id.desc()).first()
        self.assertEqual(second.card_discount_kop, 10980)
        self.assertEqual(second.bonus_spent_kop, 988)
        self.assertEqual(second.total_kop, 54900 - 10980 - 988)

    def test_finance_team_cereal_ad(self):
        finance = self.client.get("/finance")
        self.assertEqual(finance.status_code, 200)
        page = finance.get_data(as_text=True)
        self.assertIn("Показатели магазина", page)
        self.assertIn("badge-fiction", page)
        self.assertIn("chartRevenue", page)
        team = self.client.get("/team/tishka")
        self.assertIn("Почётный пушистый партнёр", team.get_data(as_text=True))
        cereal = self.client.get("/product/tishkiny-hlopya")
        self.assertIn("Тишка одобряет!", cereal.get_data(as_text=True))
        self.client.post("/api/ad/close")
        hidden = self.client.get("/")
        self.assertNotIn('id="tishka-ad"', hidden.get_data(as_text=True))
        self.client.post("/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        self.client.post("/admin/ads", data={"text": "Новый текст Тишки", "link": "/product/tishkiny-hlopya"})
        self.client.post("/logout")
        again = self.client.get("/")
        self.assertNotIn('id="tishka-ad"', again.get_data(as_text=True))

    def test_catalog_compare_charity_news(self):
        found = self.client.get("/catalog?q=хлопья")
        self.assertIn("Тишкины хлопья", found.get_data(as_text=True))
        product = Product.query.filter_by(slug="cap").one()
        self.client.post(f"/compare/add/{product.id}")
        compared = self.client.get("/compare")
        self.assertIn("Кепка", compared.get_data(as_text=True))
        gift = self.client.post("/charity", data={"name": "Аноним", "amount": "25", "message": "Панде"}, follow_redirects=True)
        self.assertIn("Перевода фонду нет", gift.get_data(as_text=True))
        self.assertEqual(self.client.get("/news").status_code, 200)
        self.client.post("/register", data={"name": "Отзыв", "email": "r@poop.empire", "password": "secret1"})
        cereal = Product.query.filter_by(slug="tishkiny-hlopya").one()
        review = self.client.post(f"/product/{cereal.slug}", data={"rating": 5, "text": "Хрустит имперски"}, follow_redirects=True)
        self.assertIn("модерацию", review.get_data(as_text=True))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    unittest.main()
