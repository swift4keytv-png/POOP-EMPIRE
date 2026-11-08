"""Серверные партии POOP CASINO. Клиент только анимирует уже выбранный результат."""

import json
import random
from copy import deepcopy

from flask import session
from sqlalchemy import func, text

from empire.extensions import db
from empire.models import Achievement, CasinoRound, CoinLedger, User, UserAchievement
from empire.services import set_setting, setting

SYMBOLS = ["POOP", "CROWN", "COIN", "GEM", "PANDA", "BOLT", "CUP"]
TIERS = (
    (800, "TRILLIONAIRE"),
    (400, "BLACK"),
    (150, "GOLD"),
    (50, "SILVER"),
    (0, "BRONZE"),
)

DEFAULT_RULES = {
    "slots": {
        "weights": [30, 5, 20, 8, 14, 12, 3],
        "pay": [4, 18, 6, 12, 8, 10, 30],
        "min": 10,
    },
    "golden": {
        "multipliers": [0, 0, 2, 3, 5, 10, 25],
        "weights": [42, 22, 16, 10, 6, 3, 1],
        "min": 20,
    },
    "jackpot": {"chance": 2, "min": 100, "seed": 5000},
    "roulette": {"red": 2, "black": 2, "gold": 14, "min": 10},
    "dice": {"exact": 8, "min": 10},
    "panda": {"min": 10},
    "vip": {"min": 100, "need_xp": 150},
}


def rules():
    merged = deepcopy(DEFAULT_RULES)
    raw = setting("casino_rules", "") or ""
    if not raw:
        return merged
    try:
        saved = json.loads(raw)
    except json.JSONDecodeError:
        return merged
    for key, value in saved.items():
        if key in merged and isinstance(value, dict):
            merged[key].update(value)
    return merged


def save_rules(form):
    data = rules()

    def ints(name, count, low, high):
        parts = [piece.strip() for piece in (form.get(name) or "").split(",") if piece.strip()]
        if len(parts) != count:
            raise ValueError(f"Поле {name}: нужно {count} чисел через запятую")
        values = [int(piece) for piece in parts]
        if any(item < low or item > high for item in values):
            raise ValueError(f"Поле {name}: числа от {low} до {high}")
        return values

    data["slots"]["weights"] = ints("slot_weights", 7, 1, 100)
    data["slots"]["pay"] = ints("slot_pay", 7, 1, 100)
    data["slots"]["min"] = max(1, min(10000, int(form.get("slot_min") or 10)))
    data["golden"]["multipliers"] = ints("golden_mult", 7, 0, 100)
    data["golden"]["weights"] = ints("golden_weights", 7, 1, 100)
    data["golden"]["min"] = max(1, min(10000, int(form.get("golden_min") or 20)))
    data["jackpot"]["chance"] = max(0, min(20, int(form.get("jackpot_chance") or 2)))
    data["jackpot"]["min"] = max(1, min(10000, int(form.get("jackpot_min") or 100)))
    data["roulette"]["red"] = max(1, min(50, int(form.get("red_mult") or 2)))
    data["roulette"]["black"] = max(1, min(50, int(form.get("black_mult") or 2)))
    data["roulette"]["gold"] = max(1, min(50, int(form.get("gold_mult") or 14)))
    data["dice"]["exact"] = max(1, min(50, int(form.get("dice_mult") or 8)))
    set_setting("casino_rules", json.dumps(data, ensure_ascii=False))
    db.session.commit()
    return data


def level_of(user):
    return (user.xp or 0) // 100 + 1


def tier_of(user):
    xp = user.xp or 0
    for need, name in TIERS:
        if xp >= need:
            return name
    return "BRONZE"


def grant(user, code):
    if UserAchievement.query.filter_by(user_id=user.id, code=code).first():
        return None
    ach = Achievement.query.filter_by(code=code).first()
    if not ach:
        return None
    db.session.add(UserAchievement(user_id=user.id, code=code))
    user.xp = (user.xp or 0) + ach.xp
    if (user.poop_coins or 0) >= 1000:
        hoard = grant(user, "coin-hoard")
        return ach.title if hoard is None else ach.title
    return ach.title


def _fresh_bet(raw, minimum):
    try:
        bet = int(raw)
    except (TypeError, ValueError):
        return None, "Ставка должна быть числом"
    if bet < minimum:
        return None, f"Минимальная ставка {minimum} POOP COINS"
    if bet > 100000:
        return None, "Слишком крупная ставка для шуточного зала"
    return bet, ""


def _token_ok(token):
    if not token:
        return True
    token = str(token)[:80]
    used = session.get("casino_tokens") or []
    if token in used:
        return False
    used.append(token)
    session["casino_tokens"] = used[-40:]
    return True


def _debit(user, bet):
    result = db.session.execute(
        text("UPDATE users SET poop_coins = poop_coins - :bet WHERE id = :id AND poop_coins >= :bet"),
        {"bet": int(bet), "id": user.id},
    )
    if result.rowcount != 1:
        db.session.rollback()
        return False
    db.session.expire(user)
    return True


def _played(user, game=None):
    query = CasinoRound.query.filter_by(user_id=user.id)
    if game:
        query = query.filter_by(game=game)
    return query.count()


def _stats(user):
    games, total_win, best = db.session.query(
        func.count(CasinoRound.id),
        func.coalesce(func.sum(CasinoRound.payout), 0),
        func.coalesce(func.max(CasinoRound.payout), 0),
    ).filter(CasinoRound.user_id == user.id).one()
    badges = UserAchievement.query.filter_by(user_id=user.id).count()
    xp = user.xp or 0
    return {
        "coins": user.poop_coins or 0,
        "level": level_of(user),
        "tier": tier_of(user),
        "vip": (user.xp or 0) >= 150,
        "xp": xp,
        "xp_bar": xp % 100,
        "games": int(games or 0),
        "total_win": int(total_win or 0),
        "best": int(best or 0),
        "badges": int(badges or 0),
    }


def finish(user, game, bet, payout, detail, extra=None):
    token = ""
    if extra and extra.get("token"):
        token = extra.pop("token")
    if not _token_ok(token):
        db.session.rollback()
        fresh = db.session.get(User, user.id)
        return {"ok": False, "error": "Этот запрос уже обработан", "coins": fresh.poop_coins}, 409
    if not _debit(user, bet):
        fresh = db.session.get(User, user.id)
        return {
            "ok": False,
            "error": "Не хватает POOP COINS. Пополнение в зале — DEMO, без рублей и без карты.",
            "coins": fresh.poop_coins if fresh else 0,
        }, 400
    user.poop_coins = (user.poop_coins or 0) + int(payout)
    user.xp = (user.xp or 0) + 1
    db.session.add(CasinoRound(user_id=user.id, game=game, bet=bet, payout=int(payout), detail=detail[:300]))
    db.session.add(CoinLedger(user_id=user.id, kind="bet", amount=-int(bet), note=game))
    if int(payout):
        db.session.add(CoinLedger(user_id=user.id, kind="win", amount=int(payout), note=game))
    unlocked = []
    for title in (
        grant(user, "first-bet"),
        grant(user, "first-win") if payout > bet else None,
        grant(user, "big-win") if payout >= bet * 8 and payout > 0 else None,
        grant(user, "gold-luck") if game == "golden" and extra and extra.get("multiplier", 0) >= 5 else None,
        grant(user, "jackpot-hunter") if game == "jackpot" and payout > bet else None,
        grant(user, "roulette-fan") if game == "roulette" and _played(user, "roulette") >= 5 else None,
        grant(user, "dice-lord") if game == "dice" and _played(user, "dice") >= 5 else None,
        grant(user, "casino-legend") if _played(user) >= 50 else None,
        grant(user, "coin-hoard") if (user.poop_coins or 0) >= 1000 else None,
    ):
        if title and title not in unlocked:
            unlocked.append(title)
    db.session.commit()
    payload = {
        "ok": True,
        "payout": int(payout),
        "detail": detail,
        "big": payout >= bet * 8 and payout > 0,
        "new_achievements": unlocked,
    }
    payload.update(_stats(user))
    if extra:
        payload.update(extra)
    return payload, 200


def slots(user, data, game="slots"):
    table = rules()
    vip = game == "vip"
    block = table["vip"] if vip else table["slots"]
    minimum = block["min"] if vip else table["slots"]["min"]
    if vip and (user.xp or 0) < table["vip"]["need_xp"]:
        return {"ok": False, "error": "VIP-автомат открывается с уровня GOLD. Его нельзя купить."}, 400
    bet, error = _fresh_bet(data.get("bet"), minimum)
    if error:
        return {"ok": False, "error": error}, 400
    weights = table["slots"]["weights"]
    pay = table["slots"]["pay"]
    roll = random.choices(SYMBOLS, weights=weights, k=5)
    best = 0
    hit = None
    for symbol in SYMBOLS:
        count = roll.count(symbol)
        if count >= 3 and count > best:
            best = count
            hit = symbol
    multiplier = 0
    if hit:
        base = pay[SYMBOLS.index(hit)]
        multiplier = base if best == 3 else base * 2 if best == 4 else base * 4
    payout = bet * multiplier
    detail = " ".join(roll)
    if multiplier:
        detail += f" · {hit} ×{multiplier}"
    return finish(
        user,
        game,
        bet,
        payout,
        detail,
        {"reels": roll, "hit": hit, "count": best, "multiplier": multiplier, "token": data.get("token")},
    )


def golden(user, data):
    table = rules()["golden"]
    bet, error = _fresh_bet(data.get("bet"), table["min"])
    if error:
        return {"ok": False, "error": error}, 400
    multiplier = random.choices(table["multipliers"], weights=table["weights"], k=1)[0]
    payout = bet * multiplier
    detail = f"множитель ×{multiplier}"
    return finish(
        user,
        "golden",
        bet,
        payout,
        detail,
        {"multiplier": multiplier, "rare": multiplier >= 10, "token": data.get("token")},
    )


def jackpot(user, data):
    table = rules()["jackpot"]
    bet, error = _fresh_bet(data.get("bet"), table["min"])
    if error:
        return {"ok": False, "error": error}, 400
    pool = int(setting("jackpot_pool", str(table["seed"])) or table["seed"])
    pool += max(1, bet // 10)
    won = random.random() * 100 < float(table["chance"])
    if won:
        payout = pool
        detail = f"джекпот {pool}"
        pool = int(table["seed"])
    else:
        payout = 0
        detail = "сейф закрыт"
    set_setting("jackpot_pool", str(pool))
    payload, code = finish(user, "jackpot", bet, payout, detail, {"won": won, "pool": pool, "token": data.get("token")})
    if code == 200:
        people = db.session.query(func.count(func.distinct(CasinoRound.user_id))).filter(CasinoRound.game == "jackpot").scalar() or 0
        payload["participants"] = int(people)
        payload["pool"] = int(setting("jackpot_pool", str(pool)) or pool)
    return payload, code


def roulette(user, data):
    table = rules()["roulette"]
    choice = (data.get("choice") or "").lower()
    if choice == "green":
        choice = "gold"
    if choice not in {"red", "black", "gold"}:
        return {"ok": False, "error": "Выберите красное, чёрное или золотой сектор"}, 400
    bet, error = _fresh_bet(data.get("bet"), table["min"])
    if error:
        return {"ok": False, "error": error}, 400
    number = random.randint(0, 36)
    reds = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    color = "gold" if number == 0 else "red" if number in reds else "black"
    payout = bet * table[color] if choice == color else 0
    return finish(
        user,
        "roulette",
        bet,
        payout,
        f"{number} {color}",
        {"number": number, "color": color, "choice": choice, "token": data.get("token")},
    )


def dice(user, data):
    table = rules()["dice"]
    try:
        guess = int(data.get("guess"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "Нужна сумма от 2 до 12"}, 400
    if guess < 2 or guess > 12:
        return {"ok": False, "error": "Сумма от 2 до 12"}, 400
    bet, error = _fresh_bet(data.get("bet"), table["min"])
    if error:
        return {"ok": False, "error": error}, 400
    first, second = random.randint(1, 6), random.randint(1, 6)
    total = first + second
    multiplier = table["exact"] if total == guess else 0
    payout = bet * multiplier
    return finish(
        user,
        "dice",
        bet,
        payout,
        f"{first}+{second}={total}",
        {"dice": [first, second], "total": total, "guess": guess, "multiplier": multiplier, "token": data.get("token")},
    )


PANDA_KINDS = (
    ("coins", 2, "POOP COINS"),
    ("multi", 3, "Бонусный множитель"),
    ("gift", 4, "Секретный подарок"),
    ("spin", 1, "Дополнительная попытка"),
    ("vip", 8, "Редкий VIP-приз"),
)


def panda(user, data):
    table = rules()["panda"]
    try:
        door = int(data.get("door"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "Выберите дверь"}, 400
    if door not in {0, 1, 2}:
        return {"ok": False, "error": "Двери три"}, 400
    bet, error = _fresh_bet(data.get("bet"), table["min"])
    if error:
        return {"ok": False, "error": error}, 400
    bag = list(PANDA_KINDS)
    random.shuffle(bag)
    doors = []
    for kind, mult, title in bag[:3]:
        doors.append({"kind": kind, "multiplier": mult, "title": title})
    prize = doors[door]
    if prize["kind"] == "spin":
        user.extra_spins = (user.extra_spins or 0) + 1
    mood = "wow" if prize["multiplier"] >= 4 else "happy" if prize["multiplier"] > 1 else "sad"
    return finish(
        user,
        "panda",
        bet,
        bet * prize["multiplier"],
        f"{prize['title']} ×{prize['multiplier']}",
        {"door": door, "doors": doors, "mood": mood, "multiplier": prize["multiplier"], "token": data.get("token")},
    )


def recent_wins(limit=8):
    rows = (
        CasinoRound.query.filter(CasinoRound.payout > CasinoRound.bet)
        .order_by(CasinoRound.id.desc())
        .limit(limit)
        .all()
    )
    return rows


def jackpot_board():
    wins = (
        CasinoRound.query.filter(CasinoRound.game == "jackpot", CasinoRound.payout > 0)
        .order_by(CasinoRound.id.desc())
        .limit(6)
        .all()
    )
    people = db.session.query(func.count(func.distinct(CasinoRound.user_id))).filter(CasinoRound.game == "jackpot").scalar() or 0
    return wins, int(people)


def player_panel(user):
    if user is None:
        return {"coins": 0, "level": 1, "tier": "BRONZE", "vip": False, "xp": 0, "xp_bar": 0, "games": 0, "total_win": 0, "best": 0, "badges": 0}
    return _stats(user)
