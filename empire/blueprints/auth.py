from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from empire.extensions import db
from empire.models import User

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash("Почта или пароль не подходят.", "error")
        elif user.is_blocked:
            flash("Кабинет заблокирован администратором.", "error")
        else:
            login_user(user)
            nxt = request.args.get("next") or request.form.get("next") or ""
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("account.index"))
    return render_template("auth/login.html", next=request.args.get("next", ""))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("account.index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(name) < 2 or "@" not in email or len(password) < 6:
            flash("Имя, почта и пароль от 6 символов.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Такая почта уже зарегистрирована.", "error")
        else:
            user = User(name=name, email=email, phone=request.form.get("phone", "").strip())
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Кабинет открыт. Карту можно выпустить на главной.")
            return redirect(url_for("main.home") + "#gold-card")
    return render_template("auth/register.html")


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Вы вышли из кабинета.")
    return redirect(url_for("main.home"))
