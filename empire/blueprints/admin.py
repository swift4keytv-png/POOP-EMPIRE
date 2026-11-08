import os
import uuid
from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from PIL import Image

from empire.art import render_personal_card
from empire.config import ROOT
from empire.extensions import db
from empire.models import (
    Banner,
    CardTier,
    Category,
    ContactMessage,
    DeliveryMethod,
    Donation,
    Factory,
    FinanceRecord,
    NewsPost,
    Order,
    Partner,
    PoopCard,
    Product,
    ProductImage,
    PromoCode,
    Review,
    User,
    WheelPrize,
)
from empire.services import finance_dashboard, set_setting, setting

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def parse_rub(raw):
    return int(round(float((raw or "0").replace(" ", "").replace(",", ".")) * 100))


def save_upload(file_storage, folder):
    if not file_storage or not file_storage.filename:
        return ""
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp", "gif"}:
        raise ValueError("Нужен jpg, png, webp или gif")
    name = f"{uuid.uuid4().hex}.{ext}"
    relative = f"uploads/{folder}/{name}"
    dest_dir = os.path.join(ROOT, "static", "uploads", folder)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, name)
    file_storage.save(dest)
    Image.open(dest).verify()
    return relative


@bp.route("/")
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        orders=Order.query.count(),
        live=Order.query.filter_by(is_demo=False).count(),
        cards=PoopCard.query.count(),
        users=User.query.count(),
        products=Product.query.count(),
        fin=finance_dashboard(),
    )


@bp.route("/cards", methods=["GET", "POST"])
@admin_required
def cards():
    if request.method == "POST":
        card = db.session.get(PoopCard, request.form.get("id", type=int))
        if card:
            tier = db.session.get(CardTier, request.form.get("tier_id", type=int))
            if tier:
                card.tier_id = tier.id
                card.design = tier.slug
            card.holder_name = (request.form.get("holder") or card.holder_name).upper()[:26]
            try:
                new_bonus = parse_rub(request.form.get("bonus"))
            except ValueError:
                flash("Бонус введён криво.", "error")
                return redirect(url_for("admin.cards"))
            delta = new_bonus - int(card.bonus_kop or 0)
            if delta:
                from empire.services import card_move

                card_move(card, "adjust", delta, "Корректировка бонусов в админке. Не банковская операция.")
            else:
                card.bonus_kop = new_bonus
            card.image = render_personal_card(
                card.holder_name, card.number, card.design, f"uploads/cards/{card.id}.png"
            )
            db.session.commit()
            flash("Карта обновлена.")
        return redirect(url_for("admin.cards"))
    return render_template(
        "admin/cards.html",
        cards=PoopCard.query.order_by(PoopCard.id.desc()).all(),
        tiers=CardTier.query.order_by(CardTier.sort_order).all(),
    )


@bp.route("/tiers", methods=["POST"])
@admin_required
def save_tier():
    tier = db.session.get(CardTier, request.form.get("id", type=int))
    if tier:
        tier.name = request.form.get("name") or tier.name
        tier.discount_percent = max(0, min(90, request.form.get("discount", type=int) or 0))
        tier.tagline = request.form.get("tagline") or ""
        tier.is_active = request.form.get("active") == "1"
        db.session.commit()
        flash("Уровень скидки сохранён. Новые заказы уже считают этот процент.")
    return redirect(url_for("admin.cards"))


@bp.route("/finance", methods=["GET", "POST"])
@admin_required
def finance():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "delete":
            row = db.session.get(FinanceRecord, request.form.get("id", type=int))
            if row:
                db.session.delete(row)
                db.session.commit()
                flash("Запись убрана из легенды.")
        else:
            try:
                amount = int((request.form.get("amount") or "0").replace(" ", ""))
            except ValueError:
                flash("Сумма должна быть целым числом рублей.", "error")
                return redirect(url_for("admin.finance"))
            row = db.session.get(FinanceRecord, request.form.get("id", type=int)) if request.form.get("id") else None
            if row is None:
                row = FinanceRecord(is_fiction=True)
                db.session.add(row)
            row.section = request.form.get("section") or "operation"
            row.title = request.form.get("title") or "Без названия"
            row.amount_rub = amount
            row.note = request.form.get("note") or ""
            row.period = request.form.get("period") or ""
            db.session.commit()
            flash("Финансовая легенда записана в SQLite.")
        return redirect(url_for("admin.finance"))
    return render_template(
        "admin/finance.html",
        rows=FinanceRecord.query.order_by(FinanceRecord.section, FinanceRecord.sort_order).all(),
        fin=finance_dashboard(),
    )


@bp.route("/ads", methods=["GET", "POST"])
@admin_required
def ads():
    if request.method == "POST":
        set_setting("ad_enabled", "1" if request.form.get("enabled") == "1" else "0")
        set_setting("ad_text", request.form.get("text") or "Тишка лично рекомендует свои хлопья!")
        set_setting("ad_link", request.form.get("link") or "/product/tishkiny-hlopya")
        db.session.commit()
        flash("Реклама Тишки сохранена.")
        return redirect(url_for("admin.ads"))
    return render_template(
        "admin/ads.html",
        enabled=setting("ad_enabled", "1"),
        text=setting("ad_text"),
        link=setting("ad_link"),
    )


@bp.route("/cereal", methods=["GET", "POST"])
@admin_required
def cereal():
    item = Product.query.filter_by(slug="tishkiny-hlopya").first()
    if request.method == "POST" and item:
        item.name = request.form.get("name") or item.name
        item.short = request.form.get("short") or item.short
        item.description = request.form.get("description") or item.description
        item.composition = request.form.get("composition") or ""
        item.price_kop = parse_rub(request.form.get("price"))
        item.stock = request.form.get("stock", type=int) or 0
        item.is_active = request.form.get("active") == "1"
        file = request.files.get("image")
        if file and file.filename:
            path = save_upload(file, "cereal")
            db.session.add(ProductImage(product_id=item.id, path=path, sort_order=len(item.images)))
        db.session.commit()
        flash("Тишкины хлопья обновлены.")
        return redirect(url_for("admin.cereal"))
    return render_template("admin/cereal.html", item=item)


@bp.route("/partners", methods=["GET", "POST"])
@admin_required
def partners():
    if request.method == "POST":
        row = db.session.get(Partner, request.form.get("id", type=int)) if request.form.get("id") else None
        if row is None:
            slug = (request.form.get("slug") or "partner").strip().lower()
            row = Partner(slug=slug)
            db.session.add(row)
        row.name = request.form.get("name") or row.name
        row.title = request.form.get("title") or ""
        row.role = request.form.get("role") or ""
        row.bio = request.form.get("bio") or ""
        row.joke = request.form.get("joke") or ""
        row.is_active = request.form.get("active") == "1"
        file = request.files.get("photo")
        if file and file.filename:
            row.photo = save_upload(file, "partners")
        db.session.commit()
        flash("Карточка партнёра сохранена.")
        return redirect(url_for("admin.partners"))
    return render_template("admin/partners.html", people=Partner.query.order_by(Partner.sort_order).all())


@bp.route("/banners", methods=["GET", "POST"])
@admin_required
def banners():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "delete":
            row = db.session.get(Banner, request.form.get("id", type=int))
            if row:
                db.session.delete(row)
                db.session.commit()
        else:
            row = db.session.get(Banner, request.form.get("id", type=int)) if request.form.get("id") else Banner()
            if row.id is None:
                db.session.add(row)
            row.title = request.form.get("title") or "Баннер"
            row.subtitle = request.form.get("subtitle") or ""
            row.link = request.form.get("link") or "/"
            row.is_active = request.form.get("active") == "1"
            file = request.files.get("image")
            if file and file.filename:
                row.image = save_upload(file, "banners")
            db.session.commit()
        flash("Баннеры обновлены.")
        return redirect(url_for("admin.banners"))
    return render_template("admin/banners.html", banners=Banner.query.order_by(Banner.sort_order).all())


@bp.route("/products", methods=["GET", "POST"])
@admin_required
def products():
    if request.method == "POST":
        item = db.session.get(Product, request.form.get("id", type=int))
        if item:
            item.name = request.form.get("name") or item.name
            item.price_kop = parse_rub(request.form.get("price"))
            item.stock = request.form.get("stock", type=int) or 0
            item.is_active = request.form.get("active") == "1"
            item.purchasable = request.form.get("purchasable") == "1"
            item.is_featured = request.form.get("featured") == "1"
            db.session.commit()
            flash("Товар сохранён.")
        return redirect(url_for("admin.products"))
    return render_template("admin/products.html", products=Product.query.order_by(Product.id).all())


@bp.route("/orders/<int:order_id>", methods=["POST"])
@admin_required
def order_status(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    status = request.form.get("status")
    if status in {"new", "paid", "shipping", "delivered", "cancelled"}:
        if status == "cancelled" and order.status != "cancelled":
            from empire.models import CardLedger, PoopCard
            from empire.services import card_move

            card = PoopCard.query.filter_by(number=order.card_number).first() if order.card_number else None
            marker = f"заказ {order.number}"
            if card and order.bonus_spent_kop and not CardLedger.query.filter_by(card_id=card.id, kind="refund").filter(CardLedger.note.contains(order.number)).first():
                card_move(card, "refund", order.bonus_spent_kop, f"Возврат бонусов, {marker}. Деньги банка не участвуют.")
            if card:
                cashback = CardLedger.query.filter_by(card_id=card.id, kind="cashback").filter(CardLedger.note.contains(order.number)).first()
                undone = CardLedger.query.filter_by(card_id=card.id, kind="adjust").filter(CardLedger.note.contains(f"отмена кэшбэка {order.number}")).first()
                if cashback and not undone:
                    card_move(card, "adjust", -cashback.amount_kop, f"Снят бонус после отмены, отмена кэшбэка {order.number}.")
        order.status = status
        db.session.commit()
        flash("Статус заказа обновлён.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/orders")
@admin_required
def orders():
    rows = Order.query.order_by(Order.created_at.desc()).limit(80).all()
    return render_template("admin/orders.html", orders=rows)


@bp.route("/reviews", methods=["POST"])
@admin_required
def moderate():
    review = db.session.get(Review, request.form.get("id", type=int))
    if review:
        review.approved = request.form.get("approved") == "1"
        product = review.product
        approved = [r for r in product.reviews if r.approved]
        product.review_count = len(approved)
        product.rating = round(sum(r.rating for r in approved) / len(approved), 2) if approved else 0
        db.session.commit()
        flash("Отзыв обновлён.")
    return redirect(url_for("admin.reviews"))


@bp.route("/reviews")
@admin_required
def reviews():
    return render_template("admin/reviews.html", reviews=Review.query.order_by(Review.created_at.desc()).all())


@bp.route("/promos", methods=["GET", "POST"])
@admin_required
def promos():
    if request.method == "POST":
        if request.form.get("action") == "delete":
            row = db.session.get(PromoCode, request.form.get("id", type=int))
            if row:
                db.session.delete(row)
        else:
            row = db.session.get(PromoCode, request.form.get("id", type=int)) if request.form.get("id") else None
            if row is None:
                row = PromoCode(code=(request.form.get("code") or "CODE").upper())
                db.session.add(row)
            row.code = (request.form.get("code") or row.code).upper()
            row.discount_percent = request.form.get("discount", type=int) or 0
            row.min_kop = parse_rub(request.form.get("minimum") or "0")
            row.is_active = request.form.get("active") == "1"
        db.session.commit()
        flash("Промокоды сохранены.")
        return redirect(url_for("admin.promos"))
    return render_template("admin/promos.html", codes=PromoCode.query.order_by(PromoCode.id).all())


def _when(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


@bp.route("/news", methods=["GET", "POST"])
@admin_required
def news():
    from empire.models import ListedCompany, MarketNews

    if request.method == "POST" and request.form.get("kind") == "market":
        try:
            percent = float((request.form.get("impact") or "0").replace(",", "."))
        except ValueError:
            percent = 0
        bps = int(round(percent * 100))
        if abs(bps) > 2000:
            flash("Влияние новости на котировку: не больше 20% в любую сторону.", "error")
            return redirect(url_for("admin.news"))
        ticker = (request.form.get("ticker") or "").strip().upper()
        company = ListedCompany.query.filter_by(ticker=ticker).first() if ticker else None
        if ticker and company is None:
            flash("Такого тикера на бирже нет.", "error")
            return redirect(url_for("admin.news"))
        db.session.add(
            MarketNews(
                company_id=company.id if company else None,
                title=request.form.get("title") or "DEMO · биржевая строка",
                body=request.form.get("body") or "Сервер применит влияние, когда наступит время публикации.",
                region=request.form.get("region") if request.form.get("region") in {"world", "russia"} else "world",
                impact_bps=bps,
                publish_at=_when(request.form.get("publish_at")),
                applied=False,
            )
        )
        db.session.commit()
        flash("Биржевая новость поставлена в очередь. Котировка сдвинется на сервере в её время.")
        return redirect(url_for("admin.news"))
    if request.method == "POST":
        row = NewsPost.query.filter_by(slug=request.form.get("slug")).first() if request.form.get("slug") else None
        if row is None:
            row = NewsPost(slug=request.form.get("slug") or f"note-{NewsPost.query.count() + 1}", body="")
            db.session.add(row)
        row.title = request.form.get("title") or "Новость"
        row.excerpt = request.form.get("excerpt") or ""
        row.body = request.form.get("body") or ""
        row.is_published = request.form.get("published") == "1"
        row.company_slug = request.form.get("company") or ""
        row.category = request.form.get("category") or "империя"
        row.publish_at = _when(request.form.get("publish_at"))
        if request.form.get("delete") == "1":
            db.session.delete(row)
            db.session.commit()
            flash("Новость удалена.")
            return redirect(url_for("admin.news"))
        db.session.commit()
        flash("Новость записана.")
        return redirect(url_for("admin.news"))
    return render_template(
        "admin/news.html",
        posts=NewsPost.query.order_by(NewsPost.id.desc()).all(),
        headlines=MarketNews.query.order_by(MarketNews.id.desc()).limit(20).all(),
    )


@bp.route("/delivery", methods=["GET", "POST"])
@admin_required
def delivery():
    if request.method == "POST":
        row = db.session.get(DeliveryMethod, request.form.get("id", type=int))
        if row:
            row.name = request.form.get("name") or row.name
            row.description = request.form.get("description") or ""
            row.fee_kop = parse_rub(request.form.get("fee") or "0")
            row.days = request.form.get("days") or ""
            row.is_active = request.form.get("active") == "1"
            db.session.commit()
            flash("Доставка обновлена.")
        return redirect(url_for("admin.delivery"))
    return render_template(
        "admin/delivery.html",
        methods=DeliveryMethod.query.order_by(DeliveryMethod.sort_order).all(),
    )


@bp.route("/donations")
@admin_required
def donations():
    return render_template("admin/donations.html", rows=Donation.query.order_by(Donation.created_at.desc()).all())


@bp.route("/contacts")
@admin_required
def contacts():
    return render_template("admin/contacts.html", rows=ContactMessage.query.order_by(ContactMessage.created_at.desc()).all())


@bp.route("/users", methods=["POST"])
@admin_required
def users_update():
    user = db.session.get(User, request.form.get("id", type=int))
    if user and user.id != current_user.id:
        user.is_blocked = request.form.get("blocked") == "1"
        db.session.commit()
        flash("Пользователь обновлён.")
    return redirect(url_for("admin.users"))


@bp.route("/users")
@admin_required
def users():
    return render_template("admin/users.html", users=User.query.order_by(User.id).all())


@bp.route("/settings", methods=["POST"])
@admin_required
def settings():
    for key in ("brand", "corp", "slogan"):
        if key in request.form:
            set_setting(key, request.form.get(key) or "")
    db.session.commit()
    flash("Название и слоган сохранены.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/wheel", methods=["GET", "POST"])
@admin_required
def wheel():
    if request.method == "POST":
        prize = db.session.get(WheelPrize, request.form.get("id", type=int))
        if prize:
            prize.title = request.form.get("title") or prize.title
            prize.weight = max(1, request.form.get("weight", type=int) or 1)
            prize.amount = request.form.get("amount", type=int) or 0
            prize.is_active = request.form.get("active") == "1"
            db.session.commit()
            flash("Награда колеса сохранена.")
        return redirect(url_for("admin.wheel"))
    prizes = WheelPrize.query.order_by(WheelPrize.sort_order).all()
    total = sum(item.weight for item in prizes if item.is_active) or 1
    return render_template("admin/wheel.html", prizes=prizes, total=total)


@bp.route("/factories", methods=["GET", "POST"])
@admin_required
def factories():
    if request.method == "POST":
        row = db.session.get(Factory, request.form.get("id", type=int))
        if row:
            row.name = request.form.get("name") or row.name
            row.city = request.form.get("city") or row.city
            row.status = request.form.get("status") or row.status
            row.staff = request.form.get("staff", type=int) or 0
            row.innovation = request.form.get("innovation") or row.innovation
            try:
                row.revenue_rub = int((request.form.get("revenue") or "0").replace(" ", ""))
            except ValueError:
                flash("Стоимость должна быть целым числом.", "error")
                return redirect(url_for("admin.factories"))
            row.is_active = request.form.get("active") == "1"
            db.session.commit()
            flash("Завод сохранён.")
        return redirect(url_for("admin.factories"))
    return render_template("admin/factories.html", plants=Factory.query.order_by(Factory.city).all())


@bp.route("/delivery-sim", methods=["GET", "POST"])
@admin_required
def delivery_sim():
    if request.method == "POST":
        set_setting("delivery_step_min", str(max(0, request.form.get("low", type=int) or 0)))
        set_setting("delivery_step_max", str(max(0, request.form.get("high", type=int) or 0)))
        set_setting("daily_coins", str(max(0, request.form.get("coins", type=int) or 0)))
        order = Order.query.filter_by(number=request.form.get("number", "")).first()
        if order and request.form.get("stage") != "":
            from empire.delivery import is_pickup, notify_ready, stages_for

            last = len(stages_for(order)) - 1
            stage = max(0, min(last, request.form.get("stage", type=int) or 0))
            order.delivery_stage = stage
            order.delivery_demo = True
            if stage >= last:
                order.status = "issued" if is_pickup(order) else "delivered"
                order.next_stage_at = None
            notify_ready(order)
            db.session.commit()
            flash("Статус демонстрационной доставки изменён.")
        else:
            db.session.commit()
            flash("Интервалы доставки сохранены.")
        return redirect(url_for("admin.delivery_sim"))
    return render_template(
        "admin/delivery_sim.html",
        low=setting("delivery_step_min", "8"),
        high=setting("delivery_step_max", "20"),
        coins=setting("daily_coins", "200"),
    )


@bp.route("/casino", methods=["GET", "POST"])
@admin_required
def casino_rules():
    from empire.casino_engine import rules, save_rules

    if request.method == "POST":
        try:
            save_rules(request.form)
            flash("Таблица выплат казино сохранена.")
        except (TypeError, ValueError) as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin.casino_rules"))
    return render_template("admin/casino.html", rules=rules())


@bp.route("/holding", methods=["GET", "POST"])
@admin_required
def holding():
    from empire.models import ListedCompany

    if request.method == "POST":
        row = db.session.get(ListedCompany, request.form.get("id", type=int))
        if row:
            row.name = request.form.get("name") or row.name
            row.boss = request.form.get("boss") or row.boss
            row.summary = request.form.get("summary") or row.summary
            row.staff = request.form.get("staff", type=int) or 0
            row.revenue_demo = request.form.get("revenue", type=int) or 0
            price = request.form.get("price", type=int)
            if price and price > 0:
                row.price_kop = price * 100
            row.is_active = request.form.get("active") == "1"
            db.session.commit()
            flash("Компания холдинга сохранена. Цифры остаются демонстрационными.")
        return redirect(url_for("admin.holding"))
    return render_template("admin/holding.html", companies=ListedCompany.query.order_by(ListedCompany.sort_order).all())


@bp.route("/world", methods=["GET", "POST"])
@admin_required
def world():
    from empire.models import Airframe, AirRoute, ConflictZone, InvestLedger, TimelineEvent

    if request.method == "POST":
        kind = request.form.get("kind")
        if kind == "zone":
            row = db.session.get(ConflictZone, request.form.get("id", type=int))
            if row:
                row.status = request.form.get("status") or row.status
                row.story = request.form.get("story") or row.story
                row.influence = request.form.get("influence", type=int) or row.influence
        elif kind == "plane":
            row = db.session.get(Airframe, request.form.get("id", type=int))
            if row:
                row.status = request.form.get("status") or row.status
                row.note = request.form.get("note") or row.note
        elif kind == "route":
            row = db.session.get(AirRoute, request.form.get("id", type=int))
            if row:
                row.status = request.form.get("status") or row.status
                row.per_week = request.form.get("per_week", type=int) or row.per_week
                row.note = request.form.get("note") or row.note
        elif kind == "year":
            row = db.session.get(TimelineEvent, request.form.get("id", type=int))
            if row:
                row.title = request.form.get("title") or row.title
                row.body = request.form.get("body") or row.body
                row.year = request.form.get("year", type=int) or row.year
        db.session.commit()
        flash("Запись вселенной сохранена. Цифры остаются демонстрационными.")
        return redirect(url_for("admin.world"))
    return render_template(
        "admin/world.html",
        zones=ConflictZone.query.order_by(ConflictZone.id).all(),
        planes=Airframe.query.order_by(Airframe.id).all(),
        routes=AirRoute.query.order_by(AirRoute.id).all(),
        events=TimelineEvent.query.order_by(TimelineEvent.sort_order).all(),
        ledger=InvestLedger.query.order_by(InvestLedger.id.desc()).limit(20).all(),
    )


@bp.route("/couriers", methods=["GET", "POST"])
@admin_required
def couriers():
    from empire.models import Courier

    if request.method == "POST":
        row = db.session.get(Courier, request.form.get("id", type=int)) if request.form.get("id") else None
        if row is None:
            row = Courier(slug=request.form.get("slug") or f"courier-{Courier.query.count() + 1}", name="Курьер")
            db.session.add(row)
        row.name = request.form.get("name") or row.name
        row.nickname = request.form.get("nickname") or ""
        row.specialty = request.form.get("specialty") or ""
        row.bio = request.form.get("bio") or ""
        row.status = request.form.get("status") or "свободен"
        row.eta = request.form.get("eta") or row.eta
        row.mark = request.form.get("mark") or row.mark
        row.is_active = request.form.get("active") == "1"
        order = Order.query.filter_by(number=request.form.get("number") or "").first()
        if order and request.form.get("assign") == "1":
            order.courier_id = row.id
            order.courier_name = f"{row.name} «{row.nickname}»" if row.nickname else row.name
        db.session.commit()
        flash("Курьер сохранён.")
        return redirect(url_for("admin.couriers"))
    return render_template("admin/couriers.html", couriers=Courier.query.order_by(Courier.id).all())


@bp.route("/panda", methods=["GET", "POST"])
@admin_required
def panda_facts():
    from empire.models import PandaFact

    if request.method == "POST":
        row = db.session.get(PandaFact, request.form.get("id", type=int)) if request.form.get("id") else None
        if request.form.get("delete") == "1" and row:
            db.session.delete(row)
        else:
            if row is None:
                row = PandaFact(keys="", answer="")
                db.session.add(row)
            row.company_slug = request.form.get("company") or ""
            row.keys = request.form.get("keys") or ""
            row.answer = request.form.get("answer") or ""
            row.link = request.form.get("link") or ""
            row.link_label = request.form.get("label") or ""
        db.session.commit()
        flash("База панды обновлена.")
        return redirect(url_for("admin.panda_facts"))
    return render_template("admin/panda.html", facts=PandaFact.query.order_by(PandaFact.id).all())
