"""Первичное наполнение SQLite. Повторный запуск ничего не затирает, если товары уже есть."""

import os
import random
import shutil
from datetime import datetime, timedelta

from empire.art import ensure_cereal_box, ensure_sample_cards, write_product_mark
from empire.config import ROOT
from empire.extensions import db
from empire.models import (
    Banner,
    CardTier,
    Category,
    DeliveryMethod,
    Donation,
    FinanceRecord,
    NewsPost,
    Order,
    OrderItem,
    Partner,
    Product,
    ProductImage,
    PromoCode,
    Review,
    SiteSetting,
    User,
)
from empire.services import set_setting

ADMIN_EMAIL = "admin@poop.empire"
ADMIN_PASSWORD = "PoopEmpire#2026"
BUYER_EMAIL = "buyer@poop.empire"
BUYER_PASSWORD = "Buyer#2026"

PHOTO_MAP = {
    "руслан.jpg": "images/ruslan.jpg",
    "серго.jpg": "images/sergey.jpg",
    "артур.jpg": "images/artur.jpg",
    "тишкины хлопья.jpg": "images/tishka.jpg",
}


def copy_photos():
    dest_dir = os.path.join(ROOT, "static", "images")
    os.makedirs(dest_dir, exist_ok=True)
    copied = {}
    for src_name, rel in PHOTO_MAP.items():
        src = os.path.join(ROOT, src_name)
        dest = os.path.join(ROOT, "static", rel.replace("/", os.sep))
        if os.path.exists(src) and not os.path.exists(dest):
            shutil.copy2(src, dest)
        copied[src_name] = rel if os.path.exists(dest) else ""
    return copied


def seed():
    photos = copy_photos()
    cards = ensure_sample_cards()
    tishka = os.path.join(ROOT, "static", "images", "tishka.jpg")
    box, back = ensure_cereal_box(tishka)
    if SiteSetting.query.count() == 0:
        defaults = {
            "brand": "Какашечная Империя Руслана Триллионеркина",
            "corp": "POOP EMPIRE GROUP",
            "slogan": "Мы не просто продаём какашки. Мы управляем какашечной экономикой мира.",
            "ad_enabled": "1",
            "ad_text": "Тишка лично рекомендует свои хлопья!",
            "ad_link": "/product/tishkiny-hlopya",
            "tishka_photo": photos.get("тишкины хлопья.jpg") or "images/tishka.jpg",
        }
        for key, value in defaults.items():
            set_setting(key, value)
        db.session.commit()
    if Product.query.count():
        return

    categories = [
        ("kollekciya", "Коллекция империи", "Статусные вещи казначейства", 1),
        ("napitki", "Напитки штаба", "То, что пьют, не выходя из кабинета", 2),
        ("merch", "Мерч корпорации", "Одежда и канцелярия POOP EMPIRE GROUP", 3),
        ("zavtraki", "Завтраки Тишки", "Хлопья и то, что кот согласен рекламировать", 4),
        ("podarki", "Подарочные наборы", "Коробки для партнёров и панд", 5),
    ]
    cat = {}
    for slug, name, desc, sort in categories:
        row = Category(slug=slug, name=name, description=desc, sort_order=sort)
        db.session.add(row)
        cat[slug] = row
    db.session.flush()

    goods = [
        ("slitok", "PE-SLITOK", "Имперский слиток", "kollekciya", 249000, 299000, "Тяжёлый сувенир для стола, за которым заключают сделки.", "Литьё, золотистое покрытие, подставка.", False),
        ("pechat", "PE-PECHAT", "Золотая печать казначея", "kollekciya", 189000, None, "Печать, которой в шутку утверждают бюджет хлопьев.", "Металл, подушка, футляр.", False),
        ("tron", "PE-TRON", "Настольный трон", "kollekciya", 459000, None, "Маленький трон для большого отчёта.", "Дерево, латунь.", True),
        ("espresso", "PE-ESPRESSO", "Эспрессо из кабинета", "napitki", 39000, None, "Крепкий, как квартальный план.", "Зёрна, вода, амбиция.", True),
        ("nektar", "PE-NEKTAR", "Чёрный нектар POOP", "napitki", 52000, 69000, "Безалкогольный напиток цвета отчёта о прибыли.", "Вода, карамель, экстракт цикория.", False),
        ("konjak", "PE-KONYAK", "Имперский коньяк 18+", "napitki", 129000, None, "Только витрина. В корзину не кладётся.", "Витринный образец, продажа отключена.", False),
        ("hoodie", "PE-HOODIE", "Толстовка POOP GOLD", "merch", 790000, 890000, "Чёрная толстовка с золотым шильдом корпорации.", "Хлопок.", True),
        ("cap", "PE-CAP", "Кепка «Не выхожу гулять»", "merch", 249000, None, "Для тех, кто тоже выбрал кабинет.", "Хлопок, вышивка.", False),
        ("diary", "PE-DIARY", "Ежедневник миллиардера", "merch", 159000, None, "Клетка для выручки и поля для шуток совета директоров.", "Бумага, кожзам.", False),
        ("tishkiny-hlopya", "PE-CEREAL", "Тишкины хлопья", "zavtraki", 54900, 69000, "Завтрак настоящего миллиардера. Тишка одобряет!", "Овсяные хлопья, мёд, пищевое золото.", True),
        ("mega-box", "PE-MEGA", "Мегакороб Тишки", "zavtraki", 129000, None, "Семейный формат для штаба и гостей.", "Те же хлопья, втрое больше хруста.", False),
        ("medal", "PE-MEDAL", "Медаль «Тишка одобряет»", "zavtraki", 99000, None, "Вручается тем, кто доел миску.", "Металл, лента.", False),
        ("breakfast-set", "PE-BREAK", "Завтрак настоящего миллиардера", "podarki", 219000, 259000, "Хлопья, чашка и открытка от Тишки.", "Набор.", True),
        ("panda-set", "PE-PANDA", "Набор «Панде тоже вкусно»", "podarki", 179000, None, "Часть шутки про помощь пандам. Сам набор — обычный товар.", "Хлопья, открытка.", False),
        ("crate", "PE-CRATE", "Корпоративный ящик", "podarki", 349000, None, "Слиток, ежедневник и хлопья для совета.", "Сборный набор.", False),
        ("cup", "PE-CUP", "Чашка кабинета", "merch", 129000, None, "Из неё пьют эспрессо, не выходя на улицу.", "Керамика.", False),
    ]
    products = {}
    for slug, sku, name, cslug, price, old, short, comp, featured in goods:
        product = Product(
            category_id=cat[cslug].id,
            slug=slug,
            sku=sku,
            name=name,
            short=short,
            description=short + "\n\nПозиция корпоративного магазина POOP EMPIRE GROUP. Оплата на сайте демонстрационная.",
            composition=comp,
            price_kop=price,
            old_price_kop=old,
            cost_kop=int(price * 0.45),
            stock=40 if slug != "konjak" else 0,
            is_featured=featured,
            is_cereal=slug in {"tishkiny-hlopya", "mega-box"},
            purchasable=slug != "konjak",
            age_restricted=slug == "konjak",
            rating=4.8 if slug == "tishkiny-hlopya" else 4.6,
            review_count=0,
        )
        db.session.add(product)
        products[slug] = product
    db.session.flush()

    for slug, product in products.items():
        if slug == "tishkiny-hlopya":
            paths = [photos.get("тишкины хлопья.jpg") or "images/tishka.jpg", box, back]
        elif slug == "mega-box":
            paths = [box, photos.get("тишкины хлопья.jpg") or "images/tishka.jpg"]
        else:
            paths = [write_product_mark(slug, product.name)]
        for index, path in enumerate(paths):
            db.session.add(ProductImage(product_id=product.id, path=path, sort_order=index))

    reviews = [
        ("tishkiny-hlopya", "Мила", 5, "Хруст честный. Кот на упаковке смотрит так, будто лично пробовал."),
        ("tishkiny-hlopya", "Глеб", 4, "Завтрак для совещания. Молоко обычное, амбиции корпоративные."),
        ("hoodie", "Кира", 5, "Толстовка тяжёлая, шильд золотой, прогулки по-прежнему не обязательны."),
        ("espresso", "Павел", 5, "Бодрит лучше планёрки."),
        ("slitok", "Нина", 4, "Слиток стоит на столе и делает вид, что это актив."),
        ("panda-set", "Олег", 5, "Открытка панде понравилась хотя бы нам."),
        ("cap", "Яна", 4, "Кепка точно передаёт политику основателя."),
        ("breakfast-set", "Тимур", 5, "Набор дарят партнёрам. Тишка одобряет даже ленту."),
    ]
    for slug, author, rating, text in reviews:
        db.session.add(Review(product_id=products[slug].id, author=author, rating=rating, text=text, approved=True))
        products[slug].review_count += 1

    for code, percent, minimum in (("TISHKA10", 10, 0), ("EMPIRE15", 15, 200000), ("PANDA5", 5, 0)):
        db.session.add(PromoCode(code=code, discount_percent=percent, min_kop=minimum, max_uses=0, is_active=True))

    for slug, name, desc, fee, days, sort in (
        ("pickup", "Самовывоз из штаба", "Заберёте сами, если всё-таки выйдете из дома.", 0, "1–2 дня", 1),
        ("courier", "Курьер по городу", "До двери. Какашечная логистика без опозданий в легендах.", 39000, "2–4 дня", 2),
        ("express", "Экспресс до кабинета", "Если завтрак нужен раньше планёрки.", 89000, "1 день", 3),
    ):
        db.session.add(DeliveryMethod(slug=slug, name=name, description=desc, fee_kop=fee, days=days, sort_order=sort))

    ruslan_joke = (
        "Руслан Триллионеркин настолько занят развитием своей корпорации, что практически не выходит гулять. "
        "Его стихия — кабинет, бизнес, финансы и управление крупнейшей какашечной империей."
    )
    people = [
        (
            "ruslan",
            "Руслан Триллионеркин",
            "Основатель и генеральный директор",
            "Стратегия, капитал, какашечная экономика и последнее слово на планёрке.",
            "Руслан собрал POOP EMPIRE GROUP как корпоративную шутку, которая ведёт себя как настоящий штаб: витрина, заказы, карты лояльности и финансовый зал. Биография на сайте — фирменный текст корпорации, а не справка из реестра.",
            ruslan_joke,
            photos.get("руслан.jpg") or "images/ruslan.jpg",
            1,
        ),
        (
            "artur",
            "Артур Ахметвалеев",
            "Деловой партнёр",
            "Партнёрские сделки, тон переговоров и проверка, чтобы золото на картах не выглядело дешёвым.",
            "Артур входит в совет как деловой партнёр. В легенде корпорации он следит, чтобы имперские презентации не разваливались на середине слогана, и кивает только тем поставкам, которые можно положить в каталог.",
            "Говорит мало, зато каждый кивок считается строкой в протоколе.",
            photos.get("артур.jpg") or "images/artur.jpg",
            2,
        ),
        (
            "sergey",
            "Сергей Любин",
            "Деловой партнёр",
            "Операционный контур: витрина, поставки мерча и чтобы заказы не застревали между шуткой и складом.",
            "Сергей держит операционную сторону партнёрства. Если хлопья кончились или толстовка зависла в статусе, это сначала его зона, а уже потом повод звать Руслана из кабинета.",
            "Умеет смотреть на жёлтый фон так, будто это цвет квартального отчёта.",
            photos.get("серго.jpg") or "images/sergey.jpg",
            3,
        ),
        (
            "tishka",
            "Тишка",
            "Почётный пушистый партнёр POOP EMPIRE GROUP",
            "Контроль качества завтраков. Реклама Тишкиных хлопьев. Проверка привлекательности упаковки. Представительство пушистых интересов.",
            "Тишка не подписывает договоры лапой, но без его взгляда коробка не считается готовой. Он утверждает рецепт молчанием, отвергает скучную упаковку и считается единственным партнёром, которому разрешено сидеть на протоколах.",
            "Однажды Тишка сел на макет коробки и тем самым утвердил дизайн. Юристы до сих пор называют это мягкой экспертизой.",
            photos.get("тишкины хлопья.jpg") or "images/tishka.jpg",
            4,
        ),
    ]
    for slug, name, title, role, bio, joke, photo, sort in people:
        db.session.add(
            Partner(slug=slug, name=name, title=title, role=role, bio=bio, joke=joke, photo=photo, sort_order=sort)
        )

    for slug, name, percent, tag, sort in (
        ("silver", "POOP SILVER", 5, "Первый шаг к разумной цене на какашки.", 1),
        ("gold", "POOP GOLD", 10, "Золотая середина миллиардера.", 2),
        ("black", "POOP BLACK", 20, "Чёрная карта для тех, кто считает полную цену неразумной.", 3),
    ):
        db.session.add(CardTier(slug=slug, name=name, discount_percent=percent, tagline=tag, sort_order=sort))

    db.session.add(Banner(title="Тишкины хлопья", subtitle="Тишка одобряет!", image=photos.get("тишкины хлопья.jpg") or "images/tishka.jpg", link="/product/tishkiny-hlopya", sort_order=1))
    db.session.add(Banner(title="Какашечная карта", subtitle="Платить полную стоимость неразумно.", image=cards["gold"], link="/#gold-card", sort_order=2))

    news = [
        ("otkrytie-shtaba", "Штаб открыл витрину", "Магазин, карта и финансовый зал заработали в одном кабинете.",
         "POOP EMPIRE GROUP собрала каталог, доставку, промокоды и какашечную карту. Оплата по-прежнему демонстрационная: банк не участвует, статус «успешно оплачено» сам не появляется."),
        ("tishka-partner", "Тишка вошёл в партнёры", "Пушистый контроль качества назначен официально.",
         "Совет директоров в лице тех, кто был в кабинете, присвоил Тишке должность почётного пушистого партнёра. Зона ответственности: завтраки, упаковка и рекламный взгляд."),
        ("ne-gulyaet", "Основатель снова не пошёл гулять", "Фирменная шутка стала строкой в биографии.",
         "Руслан Триллионеркин подтвердил режим: кабинет, финансы, империя. Прогулка в календарь не ставилась. Это шутка образа, и на странице руководства она так и подписана."),
        ("pandam", "Журнал помощи пандам открыт", "Записи хранятся. Перевода фонду нет.",
         "Пожертвования в разделе панд — демонстрационный журнал. Он нужен, чтобы жест был виден на сайте, а не чтобы деньги куда-то ушли."),
    ]
    for slug, title, excerpt, body in news:
        db.session.add(NewsPost(slug=slug, title=title, excerpt=excerpt, body=body))

    fiction = [
        ("capital", "Личный капитал Руслана", 3847291650000, "Демонстрационная цифра триллионера. Не выписка и не оценка имущества.", "", 1),
        ("valuation", "Оценка всей корпорации", 9640000000000, "Демонстрационная стоимость империи, не отчёт оценщика.", "", 1),
        ("revenue_fiction", "Легендарная выручка холдинга", 9800000000, "Вымысел для зала славы. Рядом на странице есть выручка магазина из заказов.", "год", 1),
        ("profit_fiction", "Легендарная прибыль холдинга", 4100000000, "Тоже вымысел. Прибыль витрины считается отдельно из заказов.", "год", 1),
        ("operation", "Покупка золотых чернил для печатей", 12000000, "Протокол вымышленный.", "март", 1),
        ("operation", "Аренда соседнего кабинета «на всякий случай»", 8400000, "Руслан туда не ходит.", "апрель", 2),
        ("investment", "Доля в утреннем хрусте", 250000000, "Инвестиция в линейку Тишки. Шутка баланса.", "", 1),
        ("investment", "Фонд «Панда не в курсе»", 40000000, "Название фондовое, перевода нет.", "", 2),
        ("asset", "Кабинет основателя", 700000000, "Главный актив, потому что из него не выходят.", "", 1),
        ("asset", "Партия упаковки с взглядом Тишки", 18000000, "Оценена советом на глаз.", "", 2),
        ("expense", "Золотая фольга", 22000000, "Статья для пирога расходов.", "", 1),
        ("expense", "Охрана режима без прогулок", 15000000, "Никто не выводит Руслана на улицу.", "", 2),
        ("expense", "Реклама хлопьев", 31000000, "Тишка берёт гонорар молоком.", "", 3),
        ("income", "Лицензии на слоган", 640000000, "Вымышленный лицензионный поток.", "", 1),
        ("income", "Партнёрские завтраки", 210000000, "Завтраки, которых не было в заказах магазина.", "", 2),
        ("forecast", "Прогноз: ещё один кабинет", 1500000000, "Если империя разрастётся, гулять всё равно не планируется.", "2027", 1),
        ("forecast", "Прогноз: чёрная карта у каждого второго", 900000000, "Желаемое, не план продаж.", "2027", 2),
        ("deal", "Сделка «Утренний хруст континента»", 3200000000, "Крупнейшая вымышленная поставка хлопьев.", "", 1),
        ("deal", "Сделка «Печать на весь квартал»", 870000000, "Печатей хватило бы на все протоколы.", "", 2),
        ("deal", "Сделка «Панда в золотой рамке»", 120000000, "Благотворительный жест внутри шутки, без перевода.", "", 3),
    ]
    for section, title, amount, note, period, sort in fiction:
        db.session.add(
            FinanceRecord(
                section=section,
                title=title,
                amount_rub=amount,
                note=note,
                period=period,
                is_fiction=True,
                sort_order=sort,
            )
        )

    admin = User(email=ADMIN_EMAIL, name="Администратор штаба", is_admin=True)
    admin.set_password(ADMIN_PASSWORD)
    buyer = User(email=BUYER_EMAIL, name="Покупатель Демо", phone="+7 900 000-00-01")
    buyer.set_password(BUYER_PASSWORD)
    db.session.add(admin)
    db.session.add(buyer)
    db.session.flush()
    db.session.add(Donation(user_id=buyer.id, donor_name="Покупатель Демо", amount_kop=50000, message="Панде на бамбук. Это запись в журнале, не платёж."))

    rng = random.Random(7)
    catalog = list(products.values())
    start = datetime.now().replace(hour=11, minute=0, second=0, microsecond=0)
    seq = 1
    for offset in range(170):
        if rng.random() > 0.62:
            continue
        when = start - timedelta(days=offset, hours=rng.randint(0, 6))
        chosen = rng.sample(catalog, k=rng.randint(1, 3))
        items = []
        subtotal = 0
        for product in chosen:
            if not product.purchasable:
                continue
            qty = rng.randint(1, 2)
            subtotal += product.price_kop * qty
            items.append((product, qty))
        if not items:
            continue
        fee = rng.choice([0, 39000, 89000])
        order = Order(
            number=f"PE-{when.year}-{seq:04d}",
            user_id=buyer.id,
            email=buyer.email,
            customer_name=buyer.name,
            phone=buyer.phone,
            city="Уфа",
            address="Демонстрационный адрес штаба",
            delivery_name="Курьер" if fee else "Самовывоз",
            delivery_fee_kop=fee,
            payment_type="demo",
            subtotal_kop=subtotal,
            card_discount_kop=0,
            promo_discount_kop=0,
            bonus_spent_kop=0,
            total_kop=subtotal + fee,
            status=rng.choice(["paid", "delivered", "shipping", "new"]),
            is_demo=True,
            note="Демонстрационная продажа магазина",
            created_at=when,
        )
        db.session.add(order)
        db.session.flush()
        for product, qty in items:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    name=product.name,
                    qty=qty,
                    price_kop=product.price_kop,
                    cost_kop=product.cost_kop,
                )
            )
        seq += 1
    db.session.commit()
