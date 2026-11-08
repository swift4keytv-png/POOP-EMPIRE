"""Колесо, казино, каталог и демонстрационная доставка."""

import unittest

from empire import create_app
from empire.config import TestConfig
from empire.extensions import db
from empire.models import Factory, Order, Product, PromoCode, User
from empire.services import set_setting


class NewWings(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_catalog_keeps_old_and_adds_new(self):
        self.assertIsNotNone(Product.query.filter_by(slug="tishkiny-hlopya").first())
        self.assertGreaterEqual(Product.query.count(), 60)
        vodka = Product.query.filter_by(slug="poop-vodka").one()
        self.assertFalse(vodka.purchasable)
        page = self.client.get("/catalog?category=poop-energy")
        self.assertIn("POOP ENERGY", page.get_data(as_text=True))
        blocked = self.client.post("/cart/add", data={"product_id": vodka.id}, follow_redirects=True)
        self.assertIn("витрине", blocked.get_data(as_text=True))

    def test_wheel_server_and_casino_coins(self):
        self.client.post("/register", data={"name": "Игрок", "email": "play@poop.empire", "password": "secret1", "phone": "+79990001122"})
        first = self.client.post("/api/wheel/spin", json={})
        self.assertEqual(first.status_code, 200)
        body = first.get_json()
        self.assertTrue(body["ok"])
        self.assertIn("index", body)
        second = self.client.post("/api/wheel/spin", json={})
        self.assertEqual(second.status_code, 400)
        user = User.query.filter_by(email="play@poop.empire").one()
        self.assertEqual(user.extra_spins, 0)
        daily = self.client.post("/api/casino/daily", json={})
        self.assertEqual(daily.status_code, 200)
        user = User.query.filter_by(email="play@poop.empire").one()
        self.assertGreaterEqual(user.poop_coins, 200)
        before = user.poop_coins
        played = self.client.post("/api/casino/slots", json={"game": "slots", "bet": 10})
        self.assertEqual(played.status_code, 200)
        user = User.query.filter_by(email="play@poop.empire").one()
        self.assertNotEqual(user.poop_coins, before)
        broke = self.client.post("/api/casino/slots", json={"game": "slots", "bet": 10_000_000})
        self.assertEqual(broke.status_code, 400)
        self.assertFalse(PromoCode.query.filter(PromoCode.code.like("BUYCOIN%")).count())

    def test_factory_and_delivery_timer(self):
        page = self.client.get("/industry")
        self.assertIn("Казань", page.get_data(as_text=True))
        self.assertGreaterEqual(Factory.query.count(), 10)
        self.client.post("/register", data={"name": "Курьерский", "email": "ship@poop.empire", "password": "secret1", "phone": "+79990001122"})
        set_setting("delivery_step_min", "0")
        set_setting("delivery_step_max", "0")
        db.session.commit()
        product = Product.query.filter_by(slug="classic-poop").one()
        self.client.post("/cart/add", data={"product_id": product.id, "qty": 1})
        placed = self.client.post(
            "/checkout",
            data={"name": "Курьерский", "email": "ship@poop.empire", "phone": "+79990001122", "city": "Уфа", "address": "Кабинет 2", "delivery": "pickup", "payment": "demo"},
            follow_redirects=True,
        )
        self.assertIn("POOP DELIVERY", placed.get_data(as_text=True))
        order = Order.query.filter_by(email="ship@poop.empire", is_demo=False).order_by(Order.id.desc()).first()
        track = self.client.get(f"/api/delivery/{order.number}")
        data = track.get_json()
        self.assertTrue(data["done"])
        self.assertIn("ЖОПКА", data["banner"])
        self.assertIn("не GPS", data["note"])
        user = User.query.filter_by(email="ship@poop.empire").one()
        self.assertGreaterEqual(user.extra_spins, 1)
        team = self.client.get("/team/sergey")
        self.assertIn("POOP DELIVERY", team.get_data(as_text=True))
        ruslan = self.client.get("/team/ruslan")
        self.assertIn("Триллионеркин", ruslan.get_data(as_text=True))
        self.assertNotIn("Миллиардеркин", ruslan.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
