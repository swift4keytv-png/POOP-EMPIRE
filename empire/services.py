"""Корзина, цены, заказы, графики магазина и ответы панды."""

import random
from collections import defaultdict
from datetime import datetime, timedelta

from flask import session, url_for
from flask_login import current_user
from sqlalchemy import text

from empire.extensions import db
from empire.models import (
    Banner,
    CardTier,
    Category,
    DeliveryMethod,
    Favorite,
    FinanceRecord,
    Order,
    OrderItem,
    Partner,
    CardLedger,
    PoopCard,
    Product,
    PromoCode,
    SiteSetting,
)

CASHBACK_PERCENT = 2

CARD_KINDS = {
    "topup": "Пополнение",
    "spend": "Оплата заказа",
    "cashback": "Начисление с заказа",
    "refund": "Возврат средств",
    "adjust": "Корректировка штаба",
    "transfer": "Перевод между счетами",
}


def card_move(card, kind, amount_kop, note):
    amount_kop = int(amount_kop or 0)
    if card is None or amount_kop == 0:
        return
    card.bonus_kop = max(0, int(card.bonus_kop or 0) + amount_kop)
    db.session.add(
        CardLedger(
            user_id=card.user_id,
            card_id=card.id,
            kind=kind,
            amount_kop=amount_kop,
            note=note[:240],
        )
    )


def money_kop(value):
    return int(value or 0)


def transfer_pockets(user, source, dest, amount_rub):
    """Перевод между бонусами карты и инвестиционным счётом. POOP COINS не участвуют."""

    source = (source or "").strip()
    dest = (dest or "").strip()
    if source not in {"card", "invest"} or dest not in {"card", "invest"} or source == dest:
        return {"ok": False, "error": "Перевод только между бонусами карты и инвестиционным счётом."}, 400
    try:
        amount = int(amount_rub)
    except (TypeError, ValueError):
        amount = 0
    if amount < 100 or amount > 1_000_000:
        return {"ok": False, "error": "Сумма перевода: от 100 до 1 000 000 ₽. Это DEMO, банк ничего не списывает."}, 400
    card = PoopCard.query.filter_by(user_id=user.id).first()
    if card is None:
        return {"ok": False, "error": "Сначала выпустите какашечную карту. Без неё перевод некуда записать."}, 400
    kop = amount * 100
    if source == "card":
        moved = db.session.execute(
            text("UPDATE poop_cards SET bonus_kop = bonus_kop - :kop WHERE id = :id AND bonus_kop >= :kop"),
            {"kop": kop, "id": card.id},
        )
        if moved.rowcount != 1:
            db.session.rollback()
            return {"ok": False, "error": "На бонусах карты не хватает суммы."}, 400
        db.session.execute(
            text("UPDATE users SET invest_kop = invest_kop + :kop WHERE id = :id"),
            {"kop": kop, "id": user.id},
        )
        note = f"DEMO · {amount} ₽ с бонусов карты на инвестиционный счёт"
    else:
        moved = db.session.execute(
            text("UPDATE users SET invest_kop = invest_kop - :kop WHERE id = :id AND invest_kop >= :kop"),
            {"kop": kop, "id": user.id},
        )
        if moved.rowcount != 1:
            db.session.rollback()
            return {"ok": False, "error": "На инвестиционном счёте не хватает суммы."}, 400
        db.session.execute(
            text("UPDATE poop_cards SET bonus_kop = bonus_kop + :kop WHERE id = :id"),
            {"kop": kop, "id": card.id},
        )
        note = f"DEMO · {amount} ₽ с инвестиционного счёта на бонусы карты"
    db.session.expire_all()
    from empire.models import InvestLedger

    card_delta = -kop if source == "card" else kop
    db.session.add(CardLedger(user_id=user.id, card_id=card.id, kind="transfer", amount_kop=card_delta, note=note))
    db.session.add(InvestLedger(user_id=user.id, kind="transfer", amount_kop=-card_delta, note=note))
    db.session.commit()
    from empire.models import User

    fresh_card = db.session.get(PoopCard, card.id)
    fresh_user = db.session.get(User, user.id)
    return {
        "ok": True,
        "card": fresh_card.bonus_kop,
        "invest": fresh_user.invest_kop,
        "coins": fresh_user.poop_coins,
    }, 200


def settings_map():
    return {row.key: row.value for row in SiteSetting.query.all()}


def setting(key, default=""):
    row = db.session.get(SiteSetting, key)
    return row.value if row else default


def set_setting(key, value):
    row = db.session.get(SiteSetting, key)
    if row is None:
        row = SiteSetting(key=key, value=value)
        db.session.add(row)
    else:
        row.value = value


def cart_raw():
    raw = session.get("cart") or {}
    return {int(k): int(v) for k, v in raw.items() if int(v) > 0}


def save_cart(raw):
    session["cart"] = {str(k): int(v) for k, v in raw.items() if int(v) > 0}
    session.modified = True


def cart_count():
    return sum(cart_raw().values())


def cart_lines():
    raw = cart_raw()
    if not raw:
        return []
    products = Product.query.filter(Product.id.in_(raw.keys())).all()
    by_id = {p.id: p for p in products}
    lines = []
    for pid, qty in raw.items():
        product = by_id.get(pid)
        if not product or not product.is_active:
            continue
        lines.append({"product": product, "qty": qty, "line_kop": product.price_kop * qty})
    return lines


def active_promo():
    code = (session.get("promo") or "").strip().upper()
    if not code:
        return None
    promo = PromoCode.query.filter_by(code=code, is_active=True).first()
    if promo is None:
        return None
    if promo.max_uses and promo.used_count >= promo.max_uses:
        return None
    return promo


def user_card():
    if not current_user.is_authenticated:
        return None
    return current_user.card


def quote(delivery_slug="pickup", spend_bonus=False):
    lines = cart_lines()
    subtotal = sum(line["line_kop"] for line in lines)
    card = user_card()
    percent = card.tier.discount_percent if card and card.tier and card.tier.is_active else 0
    card_off = subtotal * percent // 100
    after = subtotal - card_off
    promo = active_promo()
    promo_off = 0
    promo_code = ""
    if promo and after >= promo.min_kop:
        promo_off = after * promo.discount_percent // 100
        promo_code = promo.code
    after -= promo_off
    delivery = DeliveryMethod.query.filter_by(slug=delivery_slug, is_active=True).first()
    if delivery is None:
        delivery = DeliveryMethod.query.filter_by(is_active=True).order_by(DeliveryMethod.sort_order).first()
    fee = delivery.fee_kop if delivery else 0
    free_ship = False
    if fee and current_user.is_authenticated and (current_user.free_deliveries or 0) > 0:
        fee = 0
        free_ship = True
    bonus_balance = card.bonus_kop if card else 0
    bonus = 0
    if spend_bonus and card:
        bonus = min(bonus_balance, after)
    total = max(0, after - bonus) + fee
    return {
        "lines": lines,
        "subtotal": subtotal,
        "card": card,
        "card_percent": percent,
        "card_off": card_off,
        "promo": promo if promo_code else None,
        "promo_code": promo_code,
        "promo_off": promo_off,
        "delivery": delivery,
        "fee": fee,
        "free_ship": free_ship,
        "bonus": bonus,
        "bonus_balance": bonus_balance,
        "total": total,
        "cashback": (after - bonus) * CASHBACK_PERCENT // 100 if card else 0,
    }


def add_to_cart(product_id, qty=1):
    product = db.session.get(Product, product_id)
    if product is None or not product.is_active:
        return False, "Товар не найден"
    if not product.purchasable:
        return False, "Этот товар только на витрине: в корзину его нельзя"
    raw = cart_raw()
    next_qty = raw.get(product.id, 0) + max(1, qty)
    if next_qty > product.stock:
        return False, "На складе меньше, чем вы просите"
    raw[product.id] = next_qty
    save_cart(raw)
    return True, "Товар в корзине"


def update_qty(product_id, qty):
    product = db.session.get(Product, product_id)
    raw = cart_raw()
    if qty <= 0:
        raw.pop(product_id, None)
        save_cart(raw)
        return True, "Позиция убрана"
    if product is None or qty > product.stock:
        return False, "Такого количества нет"
    raw[product_id] = qty
    save_cart(raw)
    return True, "Корзина обновлена"


def apply_promo(code):
    code = (code or "").strip().upper()
    if not code:
        session.pop("promo", None)
        return True, "Промокод снят"
    promo = PromoCode.query.filter_by(code=code, is_active=True).first()
    if promo is None:
        return False, "Такого промокода нет"
    session["promo"] = promo.code
    return True, f"Промокод {promo.code} применён"


def next_order_number():
    year = datetime.now().year
    last = Order.query.filter(Order.number.like(f"PE-{year}-%")).order_by(Order.id.desc()).first()
    seq = 1
    if last:
        try:
            seq = int(last.number.split("-")[-1]) + 1
        except ValueError:
            seq = last.id + 1
    return f"PE-{year}-{seq:04d}"


def unique_card_number():
    while True:
        digits = "".join(str(random.randint(0, 9)) for _ in range(16))
        pretty = " ".join(digits[i : i + 4] for i in range(0, 16, 4))
        if PoopCard.query.filter_by(number=pretty).first() is None:
            return pretty


def place_order(form):
    delivery_slug = form.get("delivery") or "pickup"
    spend = form.get("spend_bonus") == "1"
    priced = quote(delivery_slug, spend)
    if not priced["lines"]:
        return None, "Корзина пуста"
    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip().lower()
    phone = (form.get("phone") or "").strip()
    city = (form.get("city") or "").strip()
    address = (form.get("address") or "").strip()
    pickup = delivery_slug == "pickup"
    if pickup and len(address) < 4:
        address = "Максима Горького, 70/1"
        if len(city) < 2:
            city = "Штаб"
    if len(name) < 2 or "@" not in email or len(phone) < 5 or len(city) < 2 or len(address) < 4:
        return None, "Заполните имя, почту, телефон, город и адрес"
    for line in priced["lines"]:
        product = db.session.get(Product, line["product"].id)
        if product.stock < line["qty"] or not product.purchasable:
            return None, f"«{product.name}» нельзя заказать в таком количестве"
    order = Order(
        number=next_order_number(),
        user_id=current_user.id if current_user.is_authenticated else None,
        email=email,
        customer_name=name,
        phone=phone,
        city=city,
        address=address,
        delivery_name=priced["delivery"].name if priced["delivery"] else "",
        delivery_fee_kop=priced["fee"],
        payment_type=form.get("payment") or "demo",
        subtotal_kop=priced["subtotal"],
        card_discount_kop=priced["card_off"],
        promo_code=priced["promo_code"],
        promo_discount_kop=priced["promo_off"],
        bonus_spent_kop=priced["bonus"],
        total_kop=priced["total"],
        card_number=priced["card"].number if priced["card"] else "",
        status="new",
        note=(form.get("note") or "").strip(),
        delivery_demo=True,
        delivery_stage=0,
        courier_name="",
    )
    db.session.add(order)
    db.session.flush()
    for line in priced["lines"]:
        product = db.session.get(Product, line["product"].id)
        product.stock -= line["qty"]
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                name=product.name,
                qty=line["qty"],
                price_kop=product.price_kop,
                cost_kop=product.cost_kop,
            )
        )
    if priced["promo"]:
        priced["promo"].used_count += 1
    if priced["card"]:
        if priced["bonus"]:
            card_move(priced["card"], "spend", -priced["bonus"], f"Списание бонусов, заказ {order.number}. Это скидка магазина, не банк.")
        if priced["cashback"]:
            card_move(priced["card"], "cashback", priced["cashback"], f"Бонус с заказа {order.number}. Начисление витрины, не банк.")
    if current_user.is_authenticated:
        if priced["free_ship"]:
            current_user.free_deliveries = max(0, (current_user.free_deliveries or 0) - 1)
        current_user.extra_spins = (current_user.extra_spins or 0) + 1
    from empire.delivery import open_delivery

    open_delivery(order)
    db.session.commit()
    session["cart"] = {}
    session.pop("promo", None)
    session["last_order"] = order.number
    session.modified = True
    return order, ""


def finance_dashboard():
    now = datetime.now()
    start = datetime(now.year, now.month, now.day) - timedelta(days=29)
    orders = (
        Order.query.filter(Order.status != "cancelled", Order.created_at >= start)
        .order_by(Order.created_at)
        .all()
    )
    by_day_rev = {}
    by_day_cnt = {}
    for i in range(30):
        key = (start + timedelta(days=i)).strftime("%d.%m")
        by_day_rev[key] = 0
        by_day_cnt[key] = 0
    for order in orders:
        key = order.created_at.strftime("%d.%m")
        if key in by_day_rev:
            goods = sum(item.price_kop * item.qty for item in order.items)
            by_day_rev[key] += goods / 100
            by_day_cnt[key] += 1

    month_profit = defaultdict(float)
    cat_sales = defaultdict(float)
    for order in Order.query.filter(Order.status != "cancelled").all():
        label = order.created_at.strftime("%m.%Y")
        for item in order.items:
            profit = (item.price_kop - item.cost_kop) * item.qty
            month_profit[label] += profit / 100
            cat = item.product.category.name if item.product and item.product.category else "Без категории"
            cat_sales[cat] += item.price_kop * item.qty / 100

    months = []
    cursor = datetime(now.year, now.month, 1)
    for _ in range(6):
        months.append(cursor.strftime("%m.%Y"))
        cursor = (cursor.replace(day=1) - timedelta(days=1)).replace(day=1)
    months.reverse()

    all_orders = Order.query.filter(Order.status != "cancelled").all()
    revenue = sum(sum(i.price_kop * i.qty for i in o.items) for o in all_orders)
    cogs = sum(sum(i.cost_kop * i.qty for i in o.items) for o in all_orders)
    delivery_sum = sum(o.delivery_fee_kop for o in all_orders)
    gross = revenue - cogs
    demo_count = sum(1 for o in all_orders if o.is_demo)
    live_count = len(all_orders) - demo_count

    top = defaultdict(lambda: {"name": "", "profit": 0, "qty": 0, "revenue": 0})
    for order in all_orders:
        for item in order.items:
            row = top[item.name]
            row["name"] = item.name
            row["profit"] += (item.price_kop - item.cost_kop) * item.qty
            row["qty"] += item.qty
            row["revenue"] += item.price_kop * item.qty
    top_rows = sorted(top.values(), key=lambda r: r["profit"], reverse=True)[:8]

    records = FinanceRecord.query.order_by(FinanceRecord.sort_order, FinanceRecord.id).all()
    grouped = defaultdict(list)
    for rec in records:
        grouped[rec.section].append(rec)

    expense_labels = [r.title for r in grouped["expense"]]
    expense_values = [r.amount_rub for r in grouped["expense"]]

    def one(section):
        return grouped[section][0].amount_rub if grouped[section] else 0

    return {
        "labels_30": list(by_day_rev.keys()),
        "revenue_30": [round(v, 2) for v in by_day_rev.values()],
        "orders_30": list(by_day_cnt.values()),
        "month_labels": months,
        "month_profit": [round(month_profit[m], 2) for m in months],
        "cat_labels": list(cat_sales.keys()),
        "cat_values": [round(v, 2) for v in cat_sales.values()],
        "expense_labels": expense_labels,
        "expense_values": expense_values,
        "revenue_kop": revenue,
        "cogs_kop": cogs,
        "delivery_kop": delivery_sum,
        "gross_kop": gross,
        "orders_count": len(all_orders),
        "demo_count": demo_count,
        "live_count": live_count,
        "avg_kop": (revenue // len(all_orders)) if all_orders else 0,
        "top": top_rows,
        "groups": grouped,
        "capital": one("capital"),
        "valuation": one("valuation"),
        "fiction_revenue": one("revenue_fiction"),
        "fiction_profit": one("profit_fiction"),
    }


def panda_reply(text):
    q = (text or "").lower()
    pairs = [
        (("достав", "курьер", "самовывоз"), "Курьер, самовывоз из штаба и экспресс описаны на странице доставки. Срок и стоимость видны при оформлении заказа."),
        (("карт", "скид", "silver", "gold", "black", "бонус"), "Какашечная карта выпускается на главной: POOP SILVER 5%, POOP GOLD 10%, POOP BLACK 20%. Скидка сама садится в заказ, бонусы копятся на карте."),
        (("тишк", "хлоп", "завтрак"), "Тишка одобряет свои хлопья. Карточка товара — в каталоге завтраков, слоган простой: хруст, который заслужил даже кот."),
        (("панд", "пожерт", "благот"), "Помощь пандам пишется в журнал как демонстрация. Деньги фонду отсюда не уходят."),
        (("промо", "купон"), "Промокод вводится в корзине. Он считается после скидки карты."),
        (("оплат",), "Оплата на сайте демонстрационная: деньги не списываются и платёж не помечается как успешный банковский."),
        (("руслан", "офис", "гуля"), "Руслан Триллионеркин почти не выходит гулять. Его стихия — кабинет, финансы и какашечная империя. Это фирменная шутка корпорации."),
        (("заказ", "корзин"), "Корзина считает скидку карты, промокод, бонусы и доставку. После оформления номер заказа остаётся в кабинете."),
    ]
    for keys, answer in pairs:
        if any(k in q for k in keys):
            return answer
    return "Я панда-консультант штаба. Спросите про карту, доставку, хлопья Тишки, промокод или панд. Живой оператор сидит в разделе контактов."


def shell_context():
    data = settings_map()
    compare_ids = session.get("compare") or []
    fav_count = 0
    if current_user.is_authenticated:
        fav_count = Favorite.query.filter_by(user_id=current_user.id).count()
    ad_on = data.get("ad_enabled", "1") == "1" and not session.get("hide_tishka")
    return {
        "site": data,
        "nav_categories": Category.query.order_by(Category.sort_order).all(),
        "cart_count": cart_count(),
        "fav_count": fav_count,
        "compare_count": len(compare_ids),
        "show_tishka_ad": ad_on,
        "tishka_photo": url_for("static", filename=data.get("tishka_photo", "images/tishka.jpg")),
        "tiers": CardTier.query.filter_by(is_active=True).order_by(CardTier.sort_order).all(),
        "footer_partners": Partner.query.filter_by(is_active=True).order_by(Partner.sort_order).limit(4).all(),
    }


def home_bundle():
    cereal = Product.query.filter_by(slug="tishkiny-hlopya").first()
    return {
        "featured": Product.query.filter_by(is_active=True, is_featured=True).limit(4).all(),
        "newest": Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).limit(4).all(),
        "cereal": cereal,
        "banners": Banner.query.filter_by(is_active=True).order_by(Banner.sort_order).all(),
        "partners": Partner.query.filter_by(is_active=True).order_by(Partner.sort_order).all(),
        "tiers": CardTier.query.filter_by(is_active=True).order_by(CardTier.sort_order).all(),
    }
