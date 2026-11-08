from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from empire.extensions import db
from empire.models import (
    Airframe,
    AirRoute,
    ConflictZone,
    ContactMessage,
    Courier,
    NewsPost,
    Factory,
    ListedCompany,
    MarketNews,
    Product,
    StockHolding,
    StockTrade,
    TimelineEvent,
)
from empire.universe import advance_market, history, quote_payload, trade

bp = Blueprint("group", __name__)


def _companies():
    advance_market()
    return ListedCompany.query.filter_by(is_active=True).order_by(ListedCompany.sort_order).all()


@bp.route("/holding")
def holding():
    rows = _companies()
    holding_rows = [row for row in rows if row.in_holding]
    plants = Factory.query.filter_by(is_active=True).count()
    staff = db.session.query(db.func.coalesce(db.func.sum(Factory.staff), 0)).scalar()
    return render_template("holding.html", companies=holding_rows, listed=rows, plants=plants, staff=staff)


@bp.route("/company/<slug>")
def company(slug):
    row = ListedCompany.query.filter_by(slug=slug, is_active=True).first_or_404()
    goods = []
    cat = {"sergo-energy": "sergo-energy", "panda-group": "panda-shop", "two-toe": "two-toe", "shmileon": "shmileon"}.get(slug)
    if cat:
        goods = Product.query.filter(Product.slug.in_(_slugs(cat)), Product.is_active.is_(True)).all()
    return render_template(
        "company.html",
        company=row,
        goods=goods,
        branches=(row.branches or "").splitlines(),
        zones=ConflictZone.query.order_by(ConflictZone.id).all() if slug == "gorilla" else [],
        zone_data=[
            {"region": item.region, "title": item.title, "foe": item.foe, "status": item.status, "troops": item.troops, "influence": item.influence, "story": item.story, "updated": item.updated_label, "lat": item.lat, "lng": item.lng}
            for item in (ConflictZone.query.order_by(ConflictZone.id).all() if slug == "gorilla" else [])
        ],
        planes=Airframe.query.order_by(Airframe.id).all() if slug == "poop-airlines" else [],
        routes=AirRoute.query.order_by(AirRoute.id).all() if slug == "poop-airlines" else [],
        posts=NewsPost.live().filter_by(company_slug=slug).order_by(NewsPost.id.desc()).limit(4).all(),
        couriers=Courier.query.filter_by(is_active=True).order_by(Courier.id).all() if slug == "poop-delivery" else [],
        sisters=ListedCompany.query.filter(ListedCompany.slug != slug, ListedCompany.in_holding.is_(True), ListedCompany.is_active.is_(True)).order_by(ListedCompany.sort_order).all(),
    )


@bp.post("/company/<slug>/contact")
def company_contact(slug):
    row = ListedCompany.query.filter_by(slug=slug, is_active=True).first_or_404()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    if len(name) < 2 or "@" not in email or len(message) < 5:
        flash("Нужны имя, почта и текст обращения.", "error")
    else:
        db.session.add(ContactMessage(name=name, email=email, message=f"[{row.name}] {message}"))
        db.session.commit()
        flash(f"Обращение для {row.name} сохранено в штабе.")
    return redirect(url_for("group.company", slug=slug) + "#desk")


def _slugs(cat):
    from empire.universe import GOODS

    return [item[0] for item in GOODS if item[2] == cat]


CHAPTERS = {
    "two-toe": (2009, "цех-легенда, затем Артур Ахметвалеев", "Двухпалые курицы как первая разработка хроники.", "Птицефабрика, сувенир, отдельная отрасль, вход в холдинг.", "Старейшая компания империи в этой легенде.", "POOP EMPIRE GROUP"),
    "golden-poop": (2012, "Артур Ахметвалеев", "Цех форм рядом с птицефабрикой.", "Заводы, лаборатории, карта России, POOP TECH.", "Промышленный контур какашечной продукции.", "POOP EMPIRE GROUP"),
    "poop-tech": (2014, "Артур Ахметвалеев", "Лабораторные шутки и упаковка.", "Пигменты, штампы, инновации заводов.", "Технологии остаются внутри промышленности Артура.", "GOLDEN POOP INDUSTRIES"),
    "sergo-energy": (2016, "Серёга", "Первая банка POOP ENERGY BY SERGO.", "SERGO GOLD, BLACK и TRILLIONAIRE.", "Энергетики как полка помощника Артура.", "POOP EMPIRE GROUP"),
    "poop-delivery": (2018, "Серёга", "Самокаты и таймер статусов.", "Курьеры, хабы, самовывоз из штаба.", "Доставка без GPS: это демонстрационный таймер.", "POOP EMPIRE GROUP"),
    "panda-group": (2020, "направление Руслана Триллионеркина", "Панды, кафе и сувениры.", "Журнал помощи, сладости, плюш.", "Живых панд сайт не продаёт.", "POOP EMPIRE GROUP"),
    "shmileon": (2022, "Максуд ШмильЁн", "Пасеки и шампиньоны.", "Мёд, воск, грибные залы, вход в холдинг.", "Публичное место компании вымышлено.", "POOP EMPIRE GROUP"),
    "gorilla": (2024, "Радмир Галлямов", "Игровая охрана заводов.", "GORILLA SQUAD и схема конфликтов.", "Это не военная служба и не сводка.", "POOP EMPIRE GROUP"),
    "poop-airlines": (2025, "Тимур Сафин", "Демонстрационный авиапарк.", "Борта POOP-001—005 и маршруты без билетов.", "Бронь не создаётся.", "POOP EMPIRE GROUP"),
    "poop-empire": (2026, "Руслан Триллионеркин", "Холдинг собирает дочерние компании.", "Биржа, кабинет, витрина, карта лояльности.", "POOP EMPIRE GROUP в легенде всегда первая по капитализации.", "материнский холдинг"),
}


@bp.route("/timeline")
@bp.route("/chronicle")
def timeline():
    events = TimelineEvent.query.order_by(TimelineEvent.sort_order, TimelineEvent.year).all()
    chapters = []
    for row in ListedCompany.query.filter_by(in_holding=True, is_active=True).all():
        year, founder, start, stages, win, parent = CHAPTERS.get(
            row.slug,
            (2099, row.boss, row.tagline, row.summary, "DEMO", "POOP EMPIRE GROUP"),
        )
        chapters.append({
            "year": year,
            "slug": row.slug,
            "name": row.name,
            "boss": row.boss,
            "photo": row.boss_photo,
            "founder": founder,
            "start": start,
            "stages": stages,
            "win": win,
            "parent": parent,
            "sort": row.sort_order,
        })
    chapters.sort(key=lambda item: (item["year"], item["sort"]))
    return render_template("chronicle.html", events=events, chapters=chapters)


@bp.route("/dream")
def dream():
    return render_template("dream.html")


@bp.route("/exchange")
def exchange():
    rows = _companies()
    quotes = quote_payload(rows)
    peg = next((row for row in rows if row.ticker == "PEG"), rows[0])
    news = [row for row in MarketNews.query.order_by(MarketNews.id.desc()).limit(24).all() if row.is_due][:8]
    portfolio = []
    balance = 0
    trades = []
    if current_user.is_authenticated:
        balance = current_user.invest_kop or 0
        portfolio = StockHolding.query.filter_by(user_id=current_user.id).filter(StockHolding.qty > 0).all()
        trades = StockTrade.query.filter_by(user_id=current_user.id).order_by(StockTrade.id.desc()).limit(8).all()
    return render_template(
        "exchange.html",
        quotes=quotes,
        chart=history(peg, 30),
        chart_ticker=peg.ticker,
        news=news,
        portfolio=portfolio,
        trades=trades,
        balance=balance,
        cap=sum(item["cap"] for item in quotes),
        volume=sum(item["volume"] for item in quotes),
    )


@bp.route("/exchange/<ticker>")
def stock(ticker):
    rows = _companies()
    row = ListedCompany.query.filter_by(ticker=ticker.upper(), is_active=True).first_or_404()
    return render_template("stock.html", company=row, chart=history(row, 40), quotes=quote_payload(rows))


@bp.get("/api/exchange/quotes")
def quotes():
    rows = _companies()
    ticker = (request.args.get("ticker") or "PEG").upper()
    picked = next((row for row in rows if row.ticker == ticker), rows[0])
    return jsonify(ok=True, quotes=quote_payload(rows), history=history(picked, 30), ticker=picked.ticker)


@bp.post("/api/exchange/trade")
@login_required
def deal():
    data = request.get_json(silent=True) or request.form
    payload, code = trade(current_user, data.get("ticker"), (data.get("side") or "").lower(), data.get("qty"))
    return jsonify(payload), code
