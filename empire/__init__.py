import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from markupsafe import Markup, escape
from sqlalchemy.exc import IntegrityError, OperationalError

from empire.config import ROOT, Config
from empire.extensions import csrf, db, login_manager, migrate


def create_app(config_class=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(ROOT, "templates"),
        static_folder=os.path.join(ROOT, "static"),
    )
    app.config.from_object(config_class or Config)
    Path(ROOT, "instance").mkdir(exist_ok=True)
    Path(ROOT, "static", "uploads").mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from empire.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from empire.blueprints.account import bp as account_bp
    from empire.blueprints.admin import bp as admin_bp
    from empire.blueprints.api import bp as api_bp
    from empire.blueprints.auth import bp as auth_bp
    from empire.blueprints.catalog import bp as catalog_bp
    from empire.blueprints.group import bp as group_bp
    from empire.blueprints.main import bp as main_bp
    from empire.blueprints.play import bp as play_bp
    from empire.blueprints.shop import bp as shop_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(play_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    @app.template_filter("money")
    def money_filter(kop):
        kop = int(kop or 0)
        sign = "−" if kop < 0 else ""
        rub, kk = divmod(abs(kop), 100)
        return f"{sign}{rub:,}".replace(",", " ") + f",{kk:02d} ₽"

    @app.template_filter("rubbig")
    def rubbig(value):
        return f"{int(value or 0):,}".replace(",", " ") + " ₽"

    @app.template_filter("nl2br")
    def nl2br(value):
        return Markup("<br>\n".join(escape(value or "").split("\n")))

    @app.context_processor
    def inject():
        from empire.services import shell_context

        return shell_context()

    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return jsonify(ok=False, error="Не найдено"), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def crashed(_e):
        return render_template("errors/500.html"), 500

    with app.app_context():
        import empire.models  # noqa: F401

        if os.environ.get("POOP_SKIP_INIT") != "1":
            if app.config.get("TESTING"):
                db.create_all()
            else:
                from flask_migrate import upgrade

                try:
                    upgrade()
                except Exception:
                    db.session.rollback()
                    db.create_all()
                db.create_all()
            try:
                from empire.seed import seed

                seed()
                from empire.expand import expand

                expand()
            except (OperationalError, IntegrityError):
                db.session.rollback()

    return app
