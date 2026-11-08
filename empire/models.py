from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from empire.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(190), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(32), default="")
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    poop_coins = db.Column(db.Integer, default=0, nullable=False)
    invest_kop = db.Column(db.Integer, default=100_000_000, nullable=False)
    xp = db.Column(db.Integer, default=0, nullable=False)
    extra_spins = db.Column(db.Integer, default=0, nullable=False)
    free_deliveries = db.Column(db.Integer, default=0, nullable=False)
    last_daily_spin = db.Column(db.Date, nullable=True)
    last_daily_coins = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    card = db.relationship("PoopCard", back_populates="user", uselist=False)
    orders = db.relationship("Order", back_populates="user")
    addresses = db.relationship("Address", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    sort_order = db.Column(db.Integer, default=0)
    products = db.relationship("Product", back_populates="category")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    slug = db.Column(db.String(190), unique=True, nullable=False)
    sku = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(190), nullable=False)
    short = db.Column(db.String(400), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    composition = db.Column(db.Text, default="")
    price_kop = db.Column(db.Integer, nullable=False)
    old_price_kop = db.Column(db.Integer)
    cost_kop = db.Column(db.Integer, nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    rating = db.Column(db.Float, default=0)
    review_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    purchasable = db.Column(db.Boolean, default=True, nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    is_cereal = db.Column(db.Boolean, default=False, nullable=False)
    age_restricted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    category = db.relationship("Category", back_populates="products")
    images = db.relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )
    reviews = db.relationship("Review", back_populates="product")


class ProductImage(db.Model):
    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    product = db.relationship("Product", back_populates="images")


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = db.Column(db.String(120), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    approved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    product = db.relationship("Product", back_populates="reviews")
    user = db.relationship("User")


class PromoCode(db.Model):
    __tablename__ = "promo_codes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False)
    min_kop = db.Column(db.Integer, default=0, nullable=False)
    max_uses = db.Column(db.Integer, default=0, nullable=False)
    used_count = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class DeliveryMethod(db.Model):
    __tablename__ = "delivery_methods"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(300), default="")
    fee_kop = db.Column(db.Integer, nullable=False, default=0)
    days = db.Column(db.String(40), default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    email = db.Column(db.String(190), nullable=False)
    customer_name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(40), default="")
    city = db.Column(db.String(120), default="")
    address = db.Column(db.String(300), default="")
    delivery_name = db.Column(db.String(120), default="")
    delivery_fee_kop = db.Column(db.Integer, default=0, nullable=False)
    payment_type = db.Column(db.String(40), default="demo")
    subtotal_kop = db.Column(db.Integer, nullable=False)
    card_discount_kop = db.Column(db.Integer, default=0, nullable=False)
    promo_code = db.Column(db.String(40), default="")
    promo_discount_kop = db.Column(db.Integer, default=0, nullable=False)
    bonus_spent_kop = db.Column(db.Integer, default=0, nullable=False)
    total_kop = db.Column(db.Integer, nullable=False)
    card_number = db.Column(db.String(32), default="")
    status = db.Column(db.String(24), default="new", nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False)
    note = db.Column(db.Text, default="")
    delivery_stage = db.Column(db.Integer, default=0, nullable=False)
    next_stage_at = db.Column(db.DateTime, nullable=True)
    stage_updated_at = db.Column(db.DateTime, nullable=True)
    delivery_demo = db.Column(db.Boolean, default=True, nullable=False)
    courier_name = db.Column(db.String(120), default="")
    courier_id = db.Column(db.Integer, nullable=True)
    pickup_notified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    name = db.Column(db.String(190), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    price_kop = db.Column(db.Integer, nullable=False)
    cost_kop = db.Column(db.Integer, nullable=False, default=0)
    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")


class Favorite(db.Model):
    __tablename__ = "favorites"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="uq_fav"),)
    product = db.relationship("Product")


class Address(db.Model):
    __tablename__ = "addresses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    label = db.Column(db.String(80), default="Дом")
    city = db.Column(db.String(120), nullable=False)
    line = db.Column(db.String(300), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    user = db.relationship("User", back_populates="addresses")


class Donation(db.Model):
    __tablename__ = "donations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    donor_name = db.Column(db.String(120), nullable=False)
    amount_kop = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(400), default="")
    created_at = db.Column(db.DateTime, default=utcnow)
    user = db.relationship("User")


class NewsPost(db.Model):
    __tablename__ = "news_posts"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(190), unique=True, nullable=False)
    title = db.Column(db.String(220), nullable=False)
    excerpt = db.Column(db.String(400), default="")
    body = db.Column(db.Text, nullable=False)
    company_slug = db.Column(db.String(80), default="", index=True)
    category = db.Column(db.String(80), default="империя")
    image = db.Column(db.String(255), default="")
    is_published = db.Column(db.Boolean, default=True)
    publish_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    @classmethod
    def live(cls):
        now = utcnow()
        return cls.query.filter(cls.is_published.is_(True)).filter(
            db.or_(cls.publish_at.is_(None), cls.publish_at <= now)
        )

    def is_live(self):
        if not self.is_published:
            return False
        return self.publish_at is None or self.publish_at <= utcnow()


class Partner(db.Model):
    __tablename__ = "partners"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Text, nullable=False, default="")
    bio = db.Column(db.Text, nullable=False, default="")
    joke = db.Column(db.Text, default="")
    photo = db.Column(db.String(255), default="")
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


class CardTier(db.Model):
    __tablename__ = "card_tiers"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False)
    tagline = db.Column(db.String(200), default="")
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    cards = db.relationship("PoopCard", back_populates="tier")


class PoopCard(db.Model):
    __tablename__ = "poop_cards"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    tier_id = db.Column(db.Integer, db.ForeignKey("card_tiers.id"), nullable=False)
    holder_name = db.Column(db.String(40), nullable=False)
    number = db.Column(db.String(24), unique=True, nullable=False)
    design = db.Column(db.String(32), nullable=False)
    bonus_kop = db.Column(db.Integer, default=0, nullable=False)
    image = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=utcnow)
    user = db.relationship("User", back_populates="card")
    tier = db.relationship("CardTier", back_populates="cards")


class CardLedger(db.Model):
    """Рублёвые бонусы какашечной карты. Не POOP COINS и не инвестиционный счёт."""

    __tablename__ = "card_ledger"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    card_id = db.Column(db.Integer, db.ForeignKey("poop_cards.id"), nullable=False, index=True)
    kind = db.Column(db.String(24), nullable=False)
    amount_kop = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(240), default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class SiteSetting(db.Model):
    __tablename__ = "site_settings"
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")


class Banner(db.Model):
    __tablename__ = "banners"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    subtitle = db.Column(db.String(300), default="")
    image = db.Column(db.String(255), default="")
    link = db.Column(db.String(255), default="/")
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)


class FinanceRecord(db.Model):
    """Шуточные вымышленные показатели триллионера. Не смешиваются с заказами магазина."""

    __tablename__ = "finance_records"
    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    amount_rub = db.Column(db.BigInteger, nullable=False, default=0)
    note = db.Column(db.String(400), default="")
    period = db.Column(db.String(40), default="")
    is_fiction = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class Subscriber(db.Model):
    __tablename__ = "subscribers"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(190), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class DeliveryEvent(db.Model):
    __tablename__ = "delivery_events"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    stage = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    order = db.relationship("Order", back_populates="events")


Order.events = db.relationship(
    DeliveryEvent,
    back_populates="order",
    cascade="all, delete-orphan",
    order_by=DeliveryEvent.id,
)


class WheelPrize(db.Model):
    __tablename__ = "wheel_prizes"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    kind = db.Column(db.String(32), nullable=False)
    amount = db.Column(db.Integer, nullable=False, default=0)
    weight = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)


class WheelSpin(db.Model):
    __tablename__ = "wheel_spins"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    prize_id = db.Column(db.Integer, db.ForeignKey("wheel_prizes.id"))
    result_text = db.Column(db.String(300), nullable=False)
    promo_code = db.Column(db.String(40), default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    prize = db.relationship("WheelPrize")
    user = db.relationship("User")


class CasinoRound(db.Model):
    __tablename__ = "casino_rounds"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    game = db.Column(db.String(40), nullable=False)
    bet = db.Column(db.Integer, nullable=False)
    payout = db.Column(db.Integer, nullable=False)
    detail = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    user = db.relationship("User")


class Achievement(db.Model):
    __tablename__ = "achievements"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(300), default="")
    xp = db.Column(db.Integer, default=10, nullable=False)


class UserAchievement(db.Model):
    __tablename__ = "user_achievements"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "code", name="uq_user_ach"),)


class Factory(db.Model):
    __tablename__ = "factories"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    region = db.Column(db.String(120), nullable=False)
    founded = db.Column(db.Integer, nullable=False, default=2020)
    boss = db.Column(db.String(120), default="")
    staff = db.Column(db.Integer, default=0, nullable=False)
    capacity = db.Column(db.String(160), default="")
    products = db.Column(db.Text, default="")
    innovation = db.Column(db.Text, default="")
    revenue_rub = db.Column(db.BigInteger, default=0, nullable=False)
    status = db.Column(db.String(80), default="Работает")
    kind = db.Column(db.String(80), default="Завод")
    pos_x = db.Column(db.Float, default=50)
    pos_y = db.Column(db.Float, default=50)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class ListedCompany(db.Model):
    __tablename__ = "listed_companies"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    ticker = db.Column(db.String(12), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    tagline = db.Column(db.String(240), default="")
    summary = db.Column(db.Text, default="")
    story = db.Column(db.Text, default="")
    boss = db.Column(db.String(160), default="")
    boss_photo = db.Column(db.String(255), default="")
    theme = db.Column(db.String(40), default="poop")
    in_holding = db.Column(db.Boolean, default=False, nullable=False)
    listed = db.Column(db.Boolean, default=True, nullable=False)
    shares = db.Column(db.BigInteger, default=1, nullable=False)
    price_kop = db.Column(db.Integer, default=10000, nullable=False)
    day_open_kop = db.Column(db.Integer, default=10000, nullable=False)
    volume = db.Column(db.Integer, default=0, nullable=False)
    staff = db.Column(db.Integer, default=0, nullable=False)
    sites = db.Column(db.Integer, default=1, nullable=False)
    revenue_demo = db.Column(db.BigInteger, default=0, nullable=False)
    branches = db.Column(db.Text, default="")
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    @property
    def cap_rub(self):
        return int((self.price_kop or 0) / 100 * (self.shares or 0))


class StockTick(db.Model):
    __tablename__ = "stock_ticks"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("listed_companies.id"), nullable=False, index=True)
    price_kop = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    company = db.relationship("ListedCompany")


class MarketNews(db.Model):
    __tablename__ = "market_news"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("listed_companies.id"))
    title = db.Column(db.String(220), nullable=False)
    body = db.Column(db.Text, default="")
    region = db.Column(db.String(16), default="world")
    impact_bps = db.Column(db.Integer, default=0, nullable=False)
    publish_at = db.Column(db.DateTime, nullable=True)
    applied = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    company = db.relationship("ListedCompany")

    @property
    def is_due(self):
        return self.publish_at is None or self.publish_at <= utcnow()


class StockHolding(db.Model):
    __tablename__ = "stock_holdings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("listed_companies.id"), nullable=False)
    qty = db.Column(db.Integer, default=0, nullable=False)
    avg_kop = db.Column(db.Integer, default=0, nullable=False)
    company = db.relationship("ListedCompany")
    __table_args__ = (db.UniqueConstraint("user_id", "company_id", name="uq_holding"),)


class StockTrade(db.Model):
    __tablename__ = "stock_trades"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("listed_companies.id"), nullable=False)
    side = db.Column(db.String(8), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    price_kop = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    company = db.relationship("ListedCompany")


class InvestLedger(db.Model):
    __tablename__ = "invest_ledger"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    kind = db.Column(db.String(24), nullable=False)
    amount_kop = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(240), default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Airframe(db.Model):
    __tablename__ = "airframes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    model = db.Column(db.String(120), default="")
    tail = db.Column(db.String(40), default="")
    seats = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(80), default="DEMO")
    note = db.Column(db.String(240), default="")


class AirRoute(db.Model):
    __tablename__ = "air_routes"
    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(80), nullable=False)
    destination = db.Column(db.String(80), nullable=False)
    per_week = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(80), default="DEMO")
    note = db.Column(db.String(240), default="")


class ConflictZone(db.Model):
    __tablename__ = "conflict_zones"
    id = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    foe = db.Column(db.String(160), default="")
    status = db.Column(db.String(80), default="")
    troops = db.Column(db.Integer, default=0, nullable=False)
    influence = db.Column(db.Integer, default=50, nullable=False)
    story = db.Column(db.Text, default="")
    updated_label = db.Column(db.String(40), default="DEMO")
    lat = db.Column(db.Float, default=55)
    lng = db.Column(db.Float, default=37)


class TimelineEvent(db.Model):
    __tablename__ = "timeline_events"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(180), nullable=False)
    company_slug = db.Column(db.String(80), default="")
    boss = db.Column(db.String(160), default="")
    body = db.Column(db.Text, default="")
    sort_order = db.Column(db.Integer, default=0)


class CoinLedger(db.Model):
    __tablename__ = "coin_ledger"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    kind = db.Column(db.String(24), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(240), default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Notice(db.Model):
    __tablename__ = "notices"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    order_number = db.Column(db.String(32), default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    seen = db.Column(db.Boolean, default=False, nullable=False)


class Courier(db.Model):
    __tablename__ = "couriers"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    nickname = db.Column(db.String(80), default="")
    bio = db.Column(db.Text, default="")
    specialty = db.Column(db.String(160), default="")
    rating = db.Column(db.Float, default=4.8)
    done_count = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(24), default="свободен")
    eta = db.Column(db.String(40), default="30–50 мин")
    mark = db.Column(db.String(8), default="🛵")
    photo = db.Column(db.String(255), default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class ChatLine(db.Model):
    __tablename__ = "chat_lines"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(12), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class PandaFact(db.Model):
    __tablename__ = "panda_facts"
    id = db.Column(db.Integer, primary_key=True)
    company_slug = db.Column(db.String(80), default="")
    keys = db.Column(db.String(300), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(180), default="")
    link_label = db.Column(db.String(80), default="")
