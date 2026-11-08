from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from empire.art import render_personal_card
from empire.extensions import db
from empire.models import CardTier, DeliveryMethod, Order, PoopCard
from empire.services import add_to_cart, apply_promo, place_order, quote, unique_card_number, update_qty

bp = Blueprint("shop", __name__)


@bp.route("/cart")
def cart():
    delivery = request.args.get("delivery") or "pickup"
    priced = quote(delivery, False)
    methods = DeliveryMethod.query.filter_by(is_active=True).order_by(DeliveryMethod.sort_order).all()
    return render_template("cart.html", priced=priced, methods=methods, delivery=delivery)


@bp.route("/cart/add", methods=["POST"])
def cart_add():
    ok, message = add_to_cart(request.form.get("product_id", type=int) or 0, request.form.get("qty", type=int) or 1)
    flash(message, "ok" if ok else "error")
    return redirect(request.referrer or url_for("shop.cart"))


@bp.route("/cart/update", methods=["POST"])
def cart_update():
    ok, message = update_qty(request.form.get("product_id", type=int) or 0, request.form.get("qty", type=int) or 0)
    flash(message, "ok" if ok else "error")
    return redirect(url_for("shop.cart"))


@bp.route("/cart/promo", methods=["POST"])
def cart_promo():
    ok, message = apply_promo(request.form.get("code"))
    flash(message, "ok" if ok else "error")
    return redirect(url_for("shop.cart"))


@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    methods = DeliveryMethod.query.filter_by(is_active=True).order_by(DeliveryMethod.sort_order).all()
    if request.method == "POST":
        order, error = place_order(request.form)
        if error:
            flash(error, "error")
        else:
            flash(f"Заказ {order.number} записан. Деньги не списывались.")
            return redirect(url_for("shop.success", number=order.number))
    delivery = request.form.get("delivery") or "pickup"
    priced = quote(delivery, request.form.get("spend_bonus") == "1")
    profile = {}
    if current_user.is_authenticated:
        profile = {"name": current_user.name, "email": current_user.email, "phone": current_user.phone or ""}
        addr = next((a for a in current_user.addresses if a.is_default), None)
        if addr is None and current_user.addresses:
            addr = current_user.addresses[0]
        if addr:
            profile["city"] = addr.city
            profile["address"] = addr.line
    return render_template("checkout.html", priced=priced, methods=methods, profile=profile)


@bp.route("/order/<number>")
def success(number):
    order = Order.query.filter_by(number=number).first_or_404()
    allowed = session.get("last_order") == number
    if current_user.is_authenticated and order.user_id == current_user.id:
        allowed = True
    if not allowed:
        flash("Этот заказ открывается из кабинета владельца.", "error")
        return redirect(url_for("main.home"))
    return render_template("order_success.html", order=order)


@bp.route("/card/issue", methods=["POST"])
@login_required
def issue_card():
    if current_user.card:
        flash("Карта уже выпущена. Она лежит в кабинете.")
        return redirect(url_for("account.card"))
    design = request.form.get("design") or "gold"
    tier = CardTier.query.filter_by(slug=design, is_active=True).first()
    holder = " ".join((request.form.get("holder") or "").split()).upper()[:26]
    if tier is None or len(holder) < 2:
        flash("Выберите дизайн и впишите имя для карты.", "error")
        return redirect(url_for("main.home") + "#gold-card")
    card = PoopCard(
        user_id=current_user.id,
        tier_id=tier.id,
        holder_name=holder,
        number=unique_card_number(),
        design=tier.slug,
        bonus_kop=0,
    )
    db.session.add(card)
    db.session.commit()
    relative = f"uploads/cards/{card.id}.png"
    card.image = render_personal_card(card.holder_name, card.number, card.design, relative)
    db.session.commit()
    flash(f"{tier.name} выпущена. Скидка {tier.discount_percent}% уже учитывается в заказе.")
    return redirect(url_for("account.card"))
