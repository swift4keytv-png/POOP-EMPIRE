from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from empire.extensions import db
from empire.models import Category, Product, Review

bp = Blueprint("catalog", __name__)


def query_products():
    q = Product.query.filter_by(is_active=True)
    category = request.args.get("category") or ""
    if category:
        cat = Category.query.filter_by(slug=category).first()
        if cat:
            q = q.filter_by(category_id=cat.id)
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term.lower()}%"
        q = q.filter(db.or_(db.func.lower(Product.name).like(like), db.func.lower(Product.sku).like(like), db.func.lower(Product.short).like(like)))
    try:
        price_min = int(float(request.args.get("price_min") or 0) * 100)
    except ValueError:
        price_min = 0
    try:
        price_max = int(float(request.args.get("price_max") or 0) * 100)
    except ValueError:
        price_max = 0
    if price_min:
        q = q.filter(Product.price_kop >= price_min)
    if price_max:
        q = q.filter(Product.price_kop <= price_max)
    sort = request.args.get("sort") or "popular"
    if sort == "price_asc":
        q = q.order_by(Product.price_kop.asc())
    elif sort == "price_desc":
        q = q.order_by(Product.price_kop.desc())
    elif sort == "new":
        q = q.order_by(Product.created_at.desc())
    else:
        q = q.order_by(Product.rating.desc(), Product.id.desc())
    return q, term, sort


@bp.route("/catalog")
@bp.route("/search")
def index():
    q, term, sort = query_products()
    page = max(1, request.args.get("page", 1, type=int))
    pagination = q.paginate(page=page, per_page=8, error_out=False)
    return render_template(
        "catalog.html",
        pagination=pagination,
        products=pagination.items,
        term=term,
        sort=sort,
        categories=Category.query.order_by(Category.sort_order).all(),
    )


@bp.route("/product/<slug>", methods=["GET", "POST"])
def product(slug):
    item = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Отзыв пишут из кабинета.", "error")
            return redirect(url_for("auth.login", next=request.path))
        text = request.form.get("text", "").strip()
        rating = request.form.get("rating", type=int) or 5
        if len(text) < 4:
            flash("Отзыв слишком короткий.", "error")
        else:
            db.session.add(
                Review(
                    product_id=item.id,
                    user_id=current_user.id,
                    author=current_user.name,
                    rating=max(1, min(5, rating)),
                    text=text,
                    approved=False,
                )
            )
            db.session.commit()
            flash("Отзыв отправлен на модерацию.")
            return redirect(url_for("catalog.product", slug=slug))
    reviews = Review.query.filter_by(product_id=item.id, approved=True).order_by(Review.created_at.desc()).all()
    related = (
        Product.query.filter(Product.category_id == item.category_id, Product.id != item.id, Product.is_active.is_(True))
        .limit(4)
        .all()
    )
    return render_template("product.html", item=item, reviews=reviews, related=related)


@bp.route("/compare")
def compare():
    ids = [int(i) for i in (session.get("compare") or [])]
    items = Product.query.filter(Product.id.in_(ids)).all() if ids else []
    order = {pid: n for n, pid in enumerate(ids)}
    items.sort(key=lambda p: order.get(p.id, 0))
    return render_template("compare.html", items=items)


@bp.route("/compare/add/<int:product_id>", methods=["POST"])
def compare_add(product_id):
    ids = [int(i) for i in (session.get("compare") or [])]
    if product_id not in ids:
        if len(ids) >= 4:
            flash("В сравнении уже четыре позиции.", "error")
        else:
            ids.append(product_id)
            flash("Добавлено к сравнению.")
    session["compare"] = ids
    session.modified = True
    return redirect(request.referrer or url_for("catalog.compare"))


@bp.route("/compare/remove/<int:product_id>", methods=["POST"])
def compare_remove(product_id):
    session["compare"] = [int(i) for i in (session.get("compare") or []) if int(i) != product_id]
    session.modified = True
    return redirect(url_for("catalog.compare"))
