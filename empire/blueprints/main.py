from flask import Blueprint, flash, redirect, render_template, request, url_for

from empire.extensions import db
from empire.models import ContactMessage, Donation, NewsPost, Partner, Subscriber
from empire.services import finance_dashboard, home_bundle

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    return render_template("home.html", **home_bundle())


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/contacts", methods=["GET", "POST"])
def contacts():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if len(name) < 2 or "@" not in email or len(message) < 5:
            flash("Напишите имя, почту и сообщение.", "error")
        else:
            db.session.add(ContactMessage(name=name, email=email, message=message))
            db.session.commit()
            flash("Сообщение записано. Это форма штаба, не обещание ответа за час.")
            return redirect(url_for("main.contacts"))
    return render_template("contacts.html")


@bp.route("/delivery")
def delivery():
    from empire.models import DeliveryMethod

    from empire.models import Courier

    methods = DeliveryMethod.query.filter_by(is_active=True).order_by(DeliveryMethod.sort_order).all()
    couriers = Courier.query.filter_by(is_active=True).order_by(Courier.id).all()
    return render_template("delivery.html", methods=methods, couriers=couriers)


@bp.route("/promos")
def promos():
    from empire.models import PromoCode

    codes = PromoCode.query.filter_by(is_active=True).order_by(PromoCode.id).all()
    return render_template("promos.html", codes=codes)


@bp.route("/charity", methods=["GET", "POST"])
def charity():
    if request.method == "POST":
        name = request.form.get("name", "").strip() or "Аноним штаба"
        message = request.form.get("message", "").strip()
        try:
            amount = int(round(float(request.form.get("amount", "0").replace(",", ".")) * 100))
        except ValueError:
            amount = 0
        if amount < 1000:
            flash("Минимальная запись — 10 ₽. Это журнал, не сбор денег.", "error")
        else:
            from flask_login import current_user

            db.session.add(
                Donation(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    donor_name=name,
                    amount_kop=amount,
                    message=message,
                )
            )
            db.session.commit()
            flash("Запись добавлена в журнал. Перевода фонду нет.")
            return redirect(url_for("main.charity"))
    rows = Donation.query.order_by(Donation.created_at.desc()).limit(30).all()
    total = db.session.query(db.func.coalesce(db.func.sum(Donation.amount_kop), 0)).scalar()
    return render_template("charity.html", donations=rows, total=total)


@bp.route("/news")
def news():
    query = NewsPost.live()
    company = request.args.get("company") or ""
    category = request.args.get("category") or ""
    if company:
        query = query.filter_by(company_slug=company)
    if category:
        query = query.filter_by(category=category)
    posts = query.order_by(NewsPost.created_at.desc()).all()
    visible = NewsPost.live().all()
    companies = sorted({row.company_slug for row in visible if row.company_slug})
    categories = sorted({row.category for row in visible if row.category})
    return render_template("news/index.html", posts=posts, companies=companies, categories=categories, company=company, category=category)


@bp.route("/news/<slug>")
def news_item(slug):
    post = NewsPost.query.filter_by(slug=slug).first_or_404()
    if not post.is_live():
        from flask import abort

        abort(404)
    return render_template("news/show.html", post=post)


COMPANY_LINKS = {
    "ruslan": [("/company/poop-empire", "POOP EMPIRE GROUP"), ("/company/kakashka-bank", "КАКАШКА БАНК")],
    "artur": [("/company/golden-poop", "GOLDEN POOP INDUSTRIES"), ("/industry", "Заводы и промышленность")],
    "sergey": [("/company/sergo-energy", "SERGO ENERGY"), ("/company/poop-delivery", "POOP DELIVERY")],
    "maksud": [("/company/shmileon", "SHMILEON HONEY & MUSHROOMS")],
    "radmir": [("/company/gorilla", "GORILLA DEFENSE GROUP")],
    "timur": [("/company/poop-airlines", "POOP AIRLINES")],
    "tishka": [("/product/tishkiny-hlopya", "Тишкины хлопья"), ("/company/tishka-bank", "TishkaBank")],
}


@bp.route("/banks")
def banks():
    from empire.models import ListedCompany

    rows = (
        ListedCompany.query.filter(ListedCompany.slug.in_(["tishka-bank", "kakashka-bank"]), ListedCompany.is_active.is_(True))
        .order_by(ListedCompany.sort_order)
        .all()
    )
    return render_template("banks.html", banks=rows)


@bp.route("/team")
def team():
    people = Partner.query.filter_by(is_active=True).order_by(Partner.sort_order).all()
    return render_template("team/index.html", people=people, links=COMPANY_LINKS)


@bp.route("/team/<slug>")
def partner(slug):
    person = Partner.query.filter_by(slug=slug, is_active=True).first_or_404()
    return render_template("team/show.html", person=person, links=COMPANY_LINKS.get(slug, []))


@bp.route("/finance")
def finance():
    return render_template("finance.html", fin=finance_dashboard())


@bp.route("/newsletter", methods=["POST"])
def newsletter():
    email = request.form.get("email", "").strip().lower()
    if "@" not in email:
        flash("Нужна почта для рассылки.", "error")
    elif Subscriber.query.filter_by(email=email).first():
        flash("Эта почта уже в списке.")
    else:
        db.session.add(Subscriber(email=email))
        db.session.commit()
        flash("Почта записана в рассылку штаба.")
    return redirect(request.referrer or url_for("main.home"))

