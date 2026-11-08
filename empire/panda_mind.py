"""Локальный помощник «Панда штаба». Без внешней языковой модели."""

import re

from flask import session
from flask_login import current_user

from empire.extensions import db
from empire.models import ChatLine, ListedCompany, NewsPost, Order, PandaFact, Product

STOP = {"и", "в", "на", "по", "о", "об", "что", "как", "где", "кто", "это", "ли", "за", "к", "от", "для", "мне", "мой", "моя", "мои"}


def _norm(text):
    text = (text or "").lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9\s-]", " ", text)


def _words(text):
    return [word for word in _norm(text).split() if word not in STOP and len(word) > 2]


def _hit(keys, question):
    score = 0
    for key in keys:
        key = key.strip()
        if len(key) < 3:
            continue
        if key in question:
            score += 2 if len(key) > 5 else 1
    return score


def _links(pairs):
    seen = set()
    out = []
    for href, label in pairs:
        if href and href not in seen:
            seen.add(href)
            out.append({"href": href, "label": label})
    return out


def _facts(question):
    best = None
    best_score = 0
    for row in PandaFact.query.all():
        score = _hit([part.strip() for part in (row.keys or "").split(",")], question)
        if score > best_score:
            best, best_score = row, score
    return best, best_score


def _catalog(question):
    words = _words(question)
    if not words:
        return []
    rows = []
    for product in Product.query.filter_by(is_active=True).limit(80).all():
        hay = _norm(product.name + " " + (product.short or ""))
        if any(word in hay for word in words):
            rows.append(product)
    return rows[:4]


def _orders():
    if not current_user.is_authenticated:
        return []
    return Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).limit(3).all()


def _news(question):
    rows = NewsPost.live().order_by(NewsPost.id.desc()).limit(12).all()
    words = _words(question)
    picked = [row for row in rows if any(word in _norm(row.title + " " + (row.company_slug or "")) for word in words)]
    return (picked or rows)[:3]


def answer(text):
    raw = (text or "").strip()
    question = _norm(raw)
    topic = session.get("panda_topic") or ""
    chunks = [part.strip() for part in re.split(r"[?.!]| и еще | а еще ", raw) if part.strip()]
    if len(chunks) == 1:
        halves = [part.strip() for part in re.split(r"\s+и\s+", raw, maxsplit=2) if part.strip()]
        if len(halves) > 1 and all(len(part) > 8 for part in halves):
            chunks = halves
    parts = chunks
    if len(parts) > 1:
        bits = []
        links = []
        for part in parts[:3]:
            piece = answer(part)
            bits.append(piece["reply"])
            links.extend((item["href"], item["label"]) for item in piece["links"])
        reply = " ".join(bits)
        return {"reply": reply, "links": _links(links)[:4], "topic": session.get("panda_topic") or topic}

    if len(question) < 2:
        return {"reply": "Напишите вопрос своими словами. Я местная панда штаба и смотрю каталог, новости и ваши заказы, если вы вошли.", "links": [], "topic": topic}

    if "самовывоз" in question or "пункт выдач" in question:
        session["panda_topic"] = "pickup"
        return {
            "reply": "Самовывоз идёт из штаба: Максима Горького, 70/1, ежедневно с 10:00 до 21:00. Курьер и домашний адрес не нужны. Уведомление в кабинете появляется, когда заказ доходит до статуса «готов к выдаче», а не в момент оформления.",
            "links": _links([("/delivery", "Доставка"), ("/account", "Кабинет")]),
            "topic": "pickup",
        }

    if "карт" in question and any(word in question for word in ("пополн", "бонус", "баланс", "какашеч")):
        session["panda_topic"] = "card"
        return {
            "reply": "Какашечная карта хранит рублёвые бонусы витрины. Пополнение в кабинете виртуальное: банк деньги не списывает. Это не POOP COINS и не инвестиционный счёт.",
            "links": _links([("/account/card", "Карта"), ("/account", "Кабинет")]),
            "topic": "card",
        }

    if any(word in question for word in ("poop coins", "coins", "пооп коин", "фишк")):
        session["panda_topic"] = "coins"
        return {
            "reply": "POOP COINS — фишки колеса и казино. Их можно получить DEMO-пакетом в зале казино. Рубли карты и инвестиционный счёт при этом не меняются, и вывести фишки деньгами нельзя.",
            "links": _links([("/casino", "Казино"), ("/wheel", "Колесо")]),
            "topic": "coins",
        }

    if any(word in question for word in ("airlines", "авиакомпан", "тимур сафин")):
        session["panda_topic"] = "poop-airlines"
        return {
            "reply": "POOP AIRLINES — демонстрационная авиакомпания Тимура Сафина. На странице есть борта и маршруты. Билет не оформляется, это не настоящий перевозчик.",
            "links": _links([("/company/poop-airlines", "POOP AIRLINES")]),
            "topic": "poop-airlines",
        }

    if any(word in question for word in ("panda group", "панда групп", "что такое панда")):
        session["panda_topic"] = "panda-group"
        return {
            "reply": "PANDA GROUP — направление холдинга: сувениры, кафе и журнал помощи. Живых панд сайт не продаёт и деньги фонду не переводит.",
            "links": _links([("/company/panda-group", "PANDA GROUP"), ("/charity", "Журнал пандам")]),
            "topic": "panda-group",
        }

    if any(word in question for word in ("руковод", "кто глав", "кто владел", "триллионер")):
        session["panda_topic"] = "holding"
        return {
            "reply": "Империей владеет и руководит Руслан Триллионеркин. Артур ведёт производство, Серёга — SERGO ENERGY и POOP DELIVERY, Максуд — мёд и грибы, Радмир — игровую охрану, Тимур — POOP AIRLINES.",
            "links": _links([("/team", "Руководство"), ("/holding", "Схема")]),
            "topic": "holding",
        }

    if any(word in question for word in ("истори компан", "хроник", "two-toe", "двухпал")):
        session["panda_topic"] = "history"
        return {
            "reply": "В хронике TWO-TOE CHICKEN CORP самая старая компания и первая разработка. Остальные даты — вымышленная корпоративная история и помечены DEMO.",
            "links": _links([("/timeline", "История компаний")]),
            "topic": "history",
        }

    if any(word in question for word in ("привет", "здравств", "хай")):
        return {
            "reply": "Я на месте. Спросите про компании, товар, заказ, авиакомпанию или новости. Шутки будут, но цифры я не выдумываю.",
            "links": [{"href": "/holding", "label": "Холдинг"}],
            "topic": topic,
        }

    if any(word in question for word in ("заказ", "где мой", "посылк", "достав")):
        orders = _orders()
        if not current_user.is_authenticated:
            reply = "Заказ привязан к кабинету. Войдите, и я посмотрю последние номера."
        elif not orders:
            reply = "В кабинете пока нет заказов. Корзина собирает товары до оформления."
        else:
            lines = []
            for order in orders:
                who = order.courier_name or ("самовывоз" if "самовывоз" in (order.delivery_name or "").lower() else "курьер ещё не назначен")
                lines.append(f"{order.number}: {order.delivery_name or 'доставка'}, статус {order.status}, этап {order.delivery_stage}. {who}.")
            reply = " ".join(lines)
        session["panda_topic"] = "order"
        return {"reply": reply, "links": _links([("/account", "Кабинет"), ("/delivery", "Доставка")]), "topic": "order"}

    if any(word in question for word in ("купить", "товар", "каталог", "цена", "наличи", "магазин", "сколько стоит")):
        goods = _catalog(question)
        if goods:
            reply = "Нашла в каталоге: " + "; ".join(
                f"{item.name} — {item.price_kop / 100:.0f} ₽, на складе {item.stock}" for item in goods
            ) + "."
            links = [(f"/product/{item.slug}", item.name) for item in goods]
        else:
            reply = "В каталоге есть какашечные товары, энергетики, хлопья Тишки, мёд, грибы и Xiaomi 17T Pro. Уточните название, и я сверюсь со складом."
            links = [("/search", "Каталог")]
        session["panda_topic"] = "shop"
        return {"reply": reply, "links": _links(links), "topic": "shop"}

    if any(word in question for word in ("новост", "что нового", "событ")):
        posts = _news(question)
        reply = "Последние записи: " + " ".join(f"«{post.title}» ({post.category}, DEMO, если сюжет легенды)." for post in posts)
        session["panda_topic"] = "news"
        return {"reply": reply, "links": _links([("/news", "Все новости")] + [(f"/news/{post.slug}", post.title) for post in posts[:2]]), "topic": "news"}

    if any(word in question for word in ("компани", "холдинг", "структур", "все фирмы", "дочерн")):
        rows = ListedCompany.query.filter_by(is_active=True, in_holding=True).order_by(ListedCompany.sort_order).all()
        names = ", ".join(f"{row.name} ({row.boss})" for row in rows if row.slug != "poop-empire")
        reply = f"Наверху Руслан Триллионеркин и POOP EMPIRE GROUP. Дальше: {names}. Цифры на страницах — демонстрационная легенда."
        session["panda_topic"] = "holding"
        return {"reply": reply, "links": _links([("/holding", "Схема"), ("/timeline", "История")]), "topic": "holding"}

    if any(word in question for word in ("бирж", "акци", "котиров")):
        rows = ListedCompany.query.filter_by(listed=True, is_active=True).order_by(ListedCompany.price_kop.desc()).limit(5).all()
        reply = "Виртуальная биржа, не банк. Сейчас в верхней части списка: " + ", ".join(f"{row.ticker} {row.price_kop / 100:.0f} ₽" for row in rows) + ". POOP COINS сюда не подмешиваются."
        session["panda_topic"] = "exchange"
        return {"reply": reply, "links": _links([("/exchange", "Биржа"), ("/account/investments", "Инвестиции")]), "topic": "exchange"}

    fact, score = _facts(question if len(question) > 8 else question + " " + topic)
    if fact and score >= 2:
        session["panda_topic"] = fact.company_slug or topic or "fact"
        links = [(fact.link, fact.link_label)] if fact.link else []
        return {"reply": fact.answer, "links": _links(links), "topic": session["panda_topic"]}

    if any(word in question for word in ("кто", "какой", "расскаж")) and topic:
        fact, score = _facts(topic + " " + question)
        if fact and score >= 2:
            return {"reply": fact.answer, "links": _links([(fact.link, fact.link_label)]), "topic": topic}

    return {
        "reply": "Этого в моих записях нет, и я не буду дорисовывать. Можно оставить обращение нужной компании: форма есть на её странице и в контактах.",
        "links": _links([("/contacts", "Контакты"), ("/holding", "Компании")]),
        "topic": topic,
    }


def remember(role, text, user_id=None):
    if not user_id:
        return
    db.session.add(ChatLine(user_id=user_id, role=role, text=text[:2000]))
    db.session.commit()
    extra = ChatLine.query.filter_by(user_id=user_id).order_by(ChatLine.id.desc()).offset(40).all()
    for row in extra:
        db.session.delete(row)
    if extra:
        db.session.commit()


def history(user_id):
    if not user_id:
        return []
    rows = ChatLine.query.filter_by(user_id=user_id).order_by(ChatLine.id.desc()).limit(30).all()
    return [{"role": row.role, "text": row.text} for row in reversed(rows)]
