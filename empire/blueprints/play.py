import random
import secrets
from datetime import date, datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from empire.extensions import db
from empire.models import (
    Achievement,
    CasinoRound,
    Factory,
    PromoCode,
    User,
    UserAchievement,
    WheelPrize,
    WheelSpin,
)
from empire.services import set_setting, setting

bp = Blueprint("play", __name__)


def level_of(user):
    return (user.xp or 0) // 100 + 1


def grant(user, code):
    if UserAchievement.query.filter_by(user_id=user.id, code=code).first():
        return
    ach = Achievement.query.filter_by(code=code).first()
    if not ach:
        return
    db.session.add(UserAchievement(user_id=user.id, code=code))
    user.xp = (user.xp or 0) + ach.xp
    if (user.poop_coins or 0) >= 1000:
        grant(user, "coin-hoard")


def make_code(prefix):
    while True:
        code = prefix + secrets.token_hex(3).upper()
        if PromoCode.query.filter_by(code=code).first() is None:
            return code


def apply_prize(user, prize):
    if prize.kind == "percent":
        code = make_code("WHEEL")
        db.session.add(PromoCode(code=code, discount_percent=prize.amount, min_kop=0, max_uses=1, is_active=True))
        return f"Промокод {code} на {prize.amount}%. Один раз, на сумму товаров.", code
    if prize.kind == "shipping":
        user.free_deliveries = (user.free_deliveries or 0) + prize.amount
        return "Бесплатная доставка записана на кабинет. Она снимет стоимость доставки в следующем заказе.", ""
    if prize.kind == "product":
        code = make_code("GIFT")
        db.session.add(PromoCode(code=code, discount_percent=100, min_kop=0, max_uses=1, is_active=True))
        return f"Промокод {code} на 100% стоимости товаров. Один раз. Доставка считается отдельно.", code
    coins = prize.amount
    user.poop_coins = (user.poop_coins or 0) + coins
    if prize.kind == "jackpot":
        return f"Джекпот: {coins} POOP COINS. У монет нет денежной цены и их нельзя вывести.", ""
    if prize.kind == "gift":
        return f"Секретный подарок — {coins} POOP COINS. Это игровая фишка, не деньги.", ""
    return f"Начислено {coins} POOP COINS. Это виртуальная фишка без денежной стоимости.", ""


def spins_left(user):
    free = 1 if user.last_daily_spin != date.today() else 0
    return free + (user.extra_spins or 0)


@bp.route("/wheel")
def wheel():
    prizes = WheelPrize.query.filter_by(is_active=True).order_by(WheelPrize.sort_order).all()
    total = sum(item.weight for item in prizes) or 1
    history = []
    if current_user.is_authenticated:
        history = WheelSpin.query.filter_by(user_id=current_user.id).order_by(WheelSpin.id.desc()).limit(8).all()
    return render_template("wheel.html", prizes=prizes, total=total, history=history, left=spins_left(current_user) if current_user.is_authenticated else 0)


@bp.post("/api/wheel/spin")
@login_required
def wheel_spin():
    prizes = WheelPrize.query.filter_by(is_active=True).order_by(WheelPrize.sort_order).all()
    if not prizes:
        return jsonify(ok=False, error="Колесо ещё не настроено"), 400
    user = db.session.get(User, current_user.id)
    free = user.last_daily_spin != date.today()
    if not free and (user.extra_spins or 0) <= 0:
        return jsonify(ok=False, error="Бесплатная попытка уже использована. Ещё одна появится после покупки."), 400
    prize = random.choices(prizes, weights=[item.weight for item in prizes], k=1)[0]
    if free:
        user.last_daily_spin = date.today()
    else:
        user.extra_spins -= 1
    text, code = apply_prize(user, prize)
    db.session.add(WheelSpin(user_id=user.id, prize_id=prize.id, result_text=text, promo_code=code))
    grant(user, "first-spin")
    db.session.commit()
    return jsonify(
        ok=True,
        index=prizes.index(prize),
        title=prize.title,
        text=text,
        code=code,
        coins=user.poop_coins,
        left=spins_left(user),
    )


@bp.route("/casino")
def casino():
    from empire.casino_engine import jackpot_board, player_panel, recent_wins, rules

    leaders = User.query.order_by(User.poop_coins.desc()).limit(8).all()
    mine = []
    ach = Achievement.query.order_by(Achievement.id).all()
    have = set()
    user = current_user if current_user.is_authenticated else None
    if user is not None:
        mine = CasinoRound.query.filter_by(user_id=user.id).order_by(CasinoRound.id.desc()).limit(8).all()
        have = {row.code for row in UserAchievement.query.filter_by(user_id=user.id).all()}
    from empire.models import CoinLedger

    ledger = CoinLedger.query.filter_by(user_id=user.id).order_by(CoinLedger.id.desc()).limit(8).all() if user else []
    jackpot_wins, jackpot_people = jackpot_board()
    table = rules()
    return render_template(
        "casino.html",
        leaders=leaders,
        mine=mine,
        achievements=ach,
        have=have,
        jackpot=int(setting("jackpot_pool", "5000") or 5000),
        jackpot_wins=jackpot_wins,
        jackpot_people=jackpot_people,
        wins=recent_wins(),
        panel=player_panel(user),
        symbols=["💩", "👑", "🪙", "💎", "🐼", "⚡", "🏆"],
        pay=list(zip(["💩", "👑", "🪙", "💎", "🐼", "⚡", "🏆"], table["slots"]["pay"])),
        rules=table,
        ledger=ledger,
    )


@bp.post("/api/casino/daily")
@login_required
def daily_coins():
    user = db.session.get(User, current_user.id)
    if user.last_daily_coins == date.today():
        return jsonify(ok=False, error="Бесплатные монеты на сегодня уже выданы", coins=user.poop_coins), 400
    amount = int(setting("daily_coins", "200") or 200)
    user.poop_coins = (user.poop_coins or 0) + amount
    user.last_daily_coins = date.today()
    db.session.commit()
    return jsonify(ok=True, coins=user.poop_coins, amount=amount)


def _play(handler):
    from empire.casino_engine import dice as play_dice
    from empire.casino_engine import panda as play_panda
    from empire.casino_engine import roulette as play_roulette

    user = db.session.get(User, current_user.id)
    data = request.get_json(silent=True) or request.form
    games = {"roulette": play_roulette, "dice": play_dice, "panda": play_panda}
    payload, code = games[handler](user, data)
    return jsonify(payload), code


@bp.post("/api/casino/slots")
@login_required
def slots():
    from empire.casino_engine import golden as play_golden
    from empire.casino_engine import jackpot as play_jackpot
    from empire.casino_engine import slots as play_slots

    user = db.session.get(User, current_user.id)
    data = request.get_json(silent=True) or request.form
    game = data.get("game") or "slots"
    if game == "golden":
        payload, code = play_golden(user, data)
    elif game == "jackpot":
        payload, code = play_jackpot(user, data)
    elif game == "vip":
        payload, code = play_slots(user, data, game="vip")
    else:
        payload, code = play_slots(user, data, game="slots")
    return jsonify(payload), code


@bp.post("/api/casino/roulette")
@login_required
def roulette():
    return _play("roulette")


@bp.post("/api/casino/dice")
@login_required
def dice():
    return _play("dice")


PACKS = {
    "starter": 1000,
    "bronze": 5000,
    "gold": 15000,
    "trillionaire": 50000,
    "legend": 100000,
}


@bp.post("/api/casino/topup")
@login_required
def coin_topup():
    from empire.casino_engine import _token_ok
    from empire.models import CoinLedger

    data = request.get_json(silent=True) or request.form
    if not _token_ok(data.get("token")):
        return jsonify(ok=False, error="Это пополнение уже проведено"), 409
    amount = PACKS.get(data.get("pack") or "")
    if amount is None:
        try:
            amount = int(data.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0
    if amount < 100 or amount > 100000:
        return jsonify(ok=False, error="DEMO-пакет от 100 до 100 000 POOP COINS"), 400
    user = db.session.get(User, current_user.id)
    user.poop_coins = (user.poop_coins or 0) + amount
    db.session.add(CoinLedger(user_id=user.id, kind="topup", amount=amount, note="DEMO-пополнение, без оплаты"))
    db.session.commit()
    return jsonify(ok=True, coins=user.poop_coins, amount=amount, demo=True)


@bp.post("/api/casino/panda")
@login_required
def panda():
    return _play("panda")


@bp.route("/industry")
def industry():
    plants = Factory.query.filter_by(is_active=True).order_by(Factory.city).all()
    return render_template(
        "industry.html",
        plants=plants,
        regions=len({item.region for item in plants}),
        staff=sum(item.staff for item in plants),
        worth=sum(item.revenue_rub for item in plants),
    )


@bp.get("/api/delivery/<number>")
def delivery_status(number):
    from flask import session

    from empire.delivery import advance_delivery, payload
    from empire.models import Order

    order = Order.query.filter_by(number=number).first_or_404()
    allowed = session.get("last_order") == number or (current_user.is_authenticated and order.user_id == current_user.id)
    if current_user.is_authenticated and current_user.is_admin:
        allowed = True
    if not allowed:
        return jsonify(ok=False, error="Этот трек открыт владельцу заказа"), 403
    advance_delivery(order)
    if current_user.is_authenticated and order.user_id == current_user.id:
        grant(current_user, "delivery-watch")
        db.session.commit()
    return jsonify(payload(order))
