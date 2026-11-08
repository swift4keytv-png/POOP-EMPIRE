from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from empire.extensions import db
from empire.models import Address, CardLedger, Favorite, Order, Product
from empire.services import CARD_KINDS, card_move, transfer_pockets

bp = Blueprint("account", __name__)


@bp.route("/account")
@login_required
def index():
    if request.method == "POST":
        pass
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    from empire.models import Notice

    notices = Notice.query.filter_by(user_id=current_user.id).order_by(Notice.id.desc()).limit(8).all()
    ledger = CardLedger.query.filter_by(user_id=current_user.id).order_by(CardLedger.id.desc()).limit(6).all()
    return render_template("account/index.html", orders=orders, notices=notices, ledger=ledger, kinds=CARD_KINDS, invest=current_user.invest_kop or 0)


@bp.route("/account/profile", methods=["POST"])
@login_required
def profile():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    if len(name) < 2:
        flash("Имя слишком короткое.", "error")
    else:
        current_user.name = name
        current_user.phone = phone
        db.session.commit()
        flash("Профиль обновлён.")
    return redirect(url_for("account.index"))


@bp.route("/account/orders")
@login_required
def orders():
    rows = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("account/orders.html", orders=rows)


@bp.route("/account/orders/<number>")
@login_required
def order(number):
    row = Order.query.filter_by(number=number, user_id=current_user.id).first_or_404()
    return render_template("account/order.html", order=row)


@bp.route("/account/card", methods=["GET", "POST"])
@login_required
def card():
    owned = current_user.card
    if request.method == "POST":
        if owned is None:
            flash("Сначала выпустите какашечную карту.", "error")
            return redirect(url_for("main.home") + "#gold-card")
        try:
            amount = int(request.form.get("amount") or "0")
        except ValueError:
            amount = 0
        if amount < 100 or amount > 1_000_000:
            flash("Виртуальное пополнение бонусов: от 100 до 1 000 000 ₽. Банк ничего не списывает.", "error")
        else:
            card_move(owned, "topup", amount * 100, "Виртуальное пополнение бонусов какашечной карты. Это не банковская операция: деньги не списывались.")
            db.session.commit()
            flash("Бонусы карты пополнены виртуально. С банковской карты ничего не списано.")
        return redirect(url_for("account.index"))
    ledger = CardLedger.query.filter_by(user_id=current_user.id).order_by(CardLedger.id.desc()).limit(40).all() if owned else []
    return render_template("account/card.html", ledger=ledger, kinds=CARD_KINDS)


@bp.route("/account/favorites")
@login_required
def favorites():
    rows = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template("account/favorites.html", rows=rows)


@bp.route("/account/favorites/toggle/<int:product_id>", methods=["POST"])
@login_required
def favorite_toggle(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        flash("Товар не найден.", "error")
        return redirect(url_for("catalog.index"))
    row = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if row:
        db.session.delete(row)
        flash("Убрано из избранного.")
    else:
        db.session.add(Favorite(user_id=current_user.id, product_id=product_id))
        flash("В избранном.")
    db.session.commit()
    return redirect(request.referrer or url_for("account.favorites"))


@bp.route("/account/addresses", methods=["GET", "POST"])
@login_required
def addresses():
    if request.method == "POST":
        city = request.form.get("city", "").strip()
        line = request.form.get("line", "").strip()
        label = request.form.get("label", "").strip() or "Адрес"
        if len(city) < 2 or len(line) < 4:
            flash("Нужны город и адрес.", "error")
        else:
            if request.form.get("default") == "1":
                for addr in current_user.addresses:
                    addr.is_default = False
            db.session.add(Address(user_id=current_user.id, label=label, city=city, line=line, is_default=request.form.get("default") == "1"))
            db.session.commit()
            flash("Адрес сохранён.")
            return redirect(url_for("account.addresses"))
    return render_template("account/addresses.html")


@bp.route("/account/addresses/<int:addr_id>/delete", methods=["POST"])
@login_required
def delete_address(addr_id):
    row = Address.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    db.session.delete(row)
    db.session.commit()
    flash("Адрес удалён.")
    return redirect(url_for("account.addresses"))


@bp.route("/account/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    from empire.models import InvestLedger

    if request.method == "POST":
        payload, code = transfer_pockets(current_user, request.form.get("source"), request.form.get("dest"), request.form.get("amount"))
        flash(payload.get("error") or "DEMO-перевод записан. С настоящей карты ничего не списано.", "error" if code != 200 else "message")
        return redirect(url_for("account.transfer"))
    card = CardLedger.query.filter_by(user_id=current_user.id, kind="transfer").order_by(CardLedger.id.desc()).limit(12).all()
    invest = InvestLedger.query.filter_by(user_id=current_user.id, kind="transfer").order_by(InvestLedger.id.desc()).limit(12).all()
    return render_template(
        "account/transfer.html",
        card_rows=card,
        invest_rows=invest,
        invest=current_user.invest_kop or 0,
        kinds=CARD_KINDS,
    )


@bp.route("/account/investments", methods=["GET", "POST"])
@login_required
def investments():
    from empire.models import InvestLedger, StockHolding, User
    from empire.universe import advance_market, quote_payload

    user = db.session.get(User, current_user.id)
    if request.method == "POST":
        raw = request.form.get("amount") or request.form.get("custom") or "0"
        try:
            amount = int(raw)
        except ValueError:
            amount = 0
        if amount < 100 or amount > 1_000_000:
            flash("Виртуальное пополнение от 100 до 1 000 000 ₽. Номер карты не сохраняется.", "error")
        else:
            kop = amount * 100
            user.invest_kop = (user.invest_kop or 0) + kop
            db.session.add(InvestLedger(user_id=user.id, kind="topup", amount_kop=kop, note="DEMO-пополнение без списания с банка"))
            db.session.commit()
            flash("Виртуальный баланс пополнен. С банковской карты ничего не списано.")
        return redirect(url_for("account.investments"))
    advance_market()
    rows = StockHolding.query.filter_by(user_id=user.id).filter(StockHolding.qty > 0).all()
    portfolio_value = sum(row.qty * (row.company.price_kop or 0) for row in rows)
    spent = sum(row.qty * (row.avg_kop or 0) for row in rows)
    ledger = InvestLedger.query.filter_by(user_id=user.id).order_by(InvestLedger.id.desc()).limit(40).all()
    return render_template(
        "account/investments.html",
        balance=user.invest_kop or 0,
        rows=rows,
        portfolio_value=portfolio_value,
        pnl=portfolio_value - spent,
        ledger=ledger,
        quotes=quote_payload(),
        chart_labels=[row.company.ticker for row in rows],
        chart_values=[row.qty * (row.company.price_kop or 0) / 100 for row in rows],
        mask=f"PE •••• •••• •••• {user.id % 10000:04d}",
    )


@bp.post("/account/investments/trade")
@login_required
def invest_trade():
    from empire.universe import trade

    payload, code = trade(current_user, request.form.get("ticker"), request.form.get("side"), request.form.get("qty"))
    flash(payload.get("error") or f"Сделка {payload.get('ticker')} записана.", "error" if code != 200 else "message")
    return redirect(url_for("account.investments"))
