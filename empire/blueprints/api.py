from flask import Blueprint, jsonify, request, session
from flask_login import current_user

from empire.extensions import db
from empire.models import Favorite, Product
from empire.services import add_to_cart, cart_count, update_qty

bp = Blueprint("api", __name__)


@bp.post("/api/cart/add")
def cart_add():
    data = request.get_json(silent=True) or request.form
    ok, message = add_to_cart(int(data.get("product_id") or 0), int(data.get("qty") or 1))
    return jsonify(ok=ok, message=message, count=cart_count()), (200 if ok else 400)


@bp.post("/api/cart/update")
def cart_update():
    data = request.get_json(silent=True) or request.form
    ok, message = update_qty(int(data.get("product_id") or 0), int(data.get("qty") or 0))
    return jsonify(ok=ok, message=message, count=cart_count()), (200 if ok else 400)


@bp.post("/api/compare")
def compare():
    data = request.get_json(silent=True) or request.form
    product_id = int(data.get("product_id") or 0)
    if db.session.get(Product, product_id) is None:
        return jsonify(ok=False, message="Товар не найден"), 404
    ids = [int(i) for i in (session.get("compare") or [])]
    if product_id in ids:
        ids.remove(product_id)
        state = False
    elif len(ids) >= 4:
        return jsonify(ok=False, message="В сравнении уже четыре товара"), 400
    else:
        ids.append(product_id)
        state = True
    session["compare"] = ids
    session.modified = True
    return jsonify(ok=True, in_compare=state, count=len(ids))


@bp.post("/api/favorite")
def favorite():
    if not current_user.is_authenticated:
        return jsonify(ok=False, message="Войдите, чтобы сохранить избранное"), 401
    data = request.get_json(silent=True) or request.form
    product_id = int(data.get("product_id") or 0)
    if db.session.get(Product, product_id) is None:
        return jsonify(ok=False, message="Товар не найден"), 404
    row = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if row:
        db.session.delete(row)
        state = False
    else:
        db.session.add(Favorite(user_id=current_user.id, product_id=product_id))
        state = True
    db.session.commit()
    count = Favorite.query.filter_by(user_id=current_user.id).count()
    return jsonify(ok=True, favorite=state, count=count)


@bp.post("/api/ad/close")
def close_ad():
    session["hide_tishka"] = True
    return jsonify(ok=True)


@bp.post("/api/panda")
def panda():
    from flask_login import current_user

    from empire.panda_mind import answer, history, remember

    data = request.get_json(silent=True) or request.form
    text = (data.get("message") or "").strip()
    user_id = current_user.id if current_user.is_authenticated else None
    if text:
        remember("user", text, user_id)
    payload = answer(text)
    if text:
        remember("panda", payload["reply"], user_id)
    payload["ok"] = True
    payload["history"] = history(user_id)
    return jsonify(payload)


@bp.post("/api/panda/clear")
def panda_clear():
    from flask_login import current_user

    from empire.models import ChatLine

    if current_user.is_authenticated:
        ChatLine.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    return jsonify(ok=True)


@bp.get("/api/panda/history")
def panda_history():
    from flask_login import current_user

    from empire.panda_mind import history

    user_id = current_user.id if current_user.is_authenticated else None
    return jsonify(ok=True, history=history(user_id))


@bp.get("/api/suggest")
def suggest():
    term = (request.args.get("q") or "").strip().lower()
    if len(term) < 2:
        return jsonify(items=[])
    like = f"%{term}%"
    rows = Product.query.filter(Product.is_active.is_(True), db.func.lower(Product.name).like(like)).limit(6).all()
    return jsonify(items=[{"name": p.name, "slug": p.slug, "price": p.price_kop} for p in rows])
