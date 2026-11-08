"""Новости, курьеры, телефон мечты и стартовые факты панды. Повторный запуск ничего не дублирует."""

from datetime import timedelta

from empire.extensions import db
from empire.models import Banner, Category, Courier, ListedCompany, MarketNews, NewsPost, PandaFact, Product, utcnow


COURIERS = [
    ("sergey", "Сергей", "Серёга", "Главный курьер империи и лицо энергетического отдела.", "POOP DELIVERY", 4.9, 420, "свободен", "25–40 мин", "🛵", "images/sergey.jpg"),
    ("max", "Макс", "Турбо", "Берёт срочные заказы и не любит стоять на светофоре в легенде.", "Срочная доставка", 4.7, 310, "свободен", "15–25 мин", "⚡", ""),
    ("artur-pro", "Артур", "Профи", "Ведёт крупные коробки. Это курьер службы, не директор заводов.", "Крупные заказы", 4.8, 260, "свободен", "40–70 мин", "📦", ""),
    ("radik", "Радик", "Экспресс", "Городские небольшие посылки.", "Небольшие посылки", 4.6, 190, "отдыхает", "20–35 мин", "🏙️", ""),
    ("ponchik", "Панда Пончик", "Пончик", "Официальный курьер PANDA GROUP. Живых панд не возит.", "Товары с пандами", 5.0, 88, "свободен", "30–45 мин", "🐼", ""),
    ("timur-air", "Тимур", "Авиадоставка", "Специальные демонстрационные авиаперевозки POOP AIRLINES. Это не настоящий рейс.", "DEMO-авиадоставка", 4.9, 40, "свободен", "по расписанию DEMO", "✈️", "images/timur.jpg"),
]


NEWS = [
    ("two-toe-origin", "two-toe", "история", "TWO-TOE CHICKEN CORP остаётся первой разработкой", "Хроника начинается с двухпалых куриц, а не с биржи.", "DEMO. В художественной хронике именно птицеводство открыло путь остальным компаниям Руслана."),
    ("two-toe-farm", "two-toe", "производство", "Новый демонстрационный птичник", "Агрохолдинг расширяет схему ферм.", "DEMO. Цифры фермы условные и не относятся к реальному хозяйству."),
    ("sergo-can", "sergo-energy", "продукт", "Новая банка SERGO ENERGY", "Серёга ставит на полку яркую банку.", "DEMO. Напиток продаётся в каталоге как обычный товар сайта."),
    ("sergo-team", "sergo-energy", "событие", "Энергетический забег легенды", "Команда банок вышла на демонстрационный старт.", "DEMO. Это корпоративная шутка, не спортивное событие."),
    ("delivery-crew", "poop-delivery", "логистика", "В службе появились новые курьеры", "Кроме Серёги заказы могут везти Макс, Артур, Радик, Пончик и Тимур.", "Назначение сохраняется в заказе. Карта маршрута, если показана, остаётся демонстрационной."),
    ("delivery-hq", "poop-delivery", "самовывоз", "Штаб принимает самовывоз", "Пункт выдачи: Максима Горького, 70/1.", "Уведомление о готовности появляется только когда заказ доходит до статуса «готов к выдаче»."),
    ("panda-cafe", "panda-group", "кафе", "Кафе панд обновило витрину", "Сувениры и сладости лежат в каталоге.", "Живых животных магазин не продаёт. Журнал помощи остаётся журналом."),
    ("panda-grove", "panda-group", "ферма", "Бамбуковая ферма на схеме", "PANDA GROUP показывает ферму как часть легенды.", "DEMO. Это не отчёт заповедника."),
    ("shm-honey", "shmileon", "мёд", "Максуд открыл новую полку мёда", "Премиальные банки SHMILEON уже в каталоге.", "Пасека в легенде. Адрес дома на сайте не публикуется."),
    ("shm-mush", "shmileon", "грибы", "Шампиньоны вышли новой партией", "Грибной цех пополнил витрину.", "DEMO-статистика урожая не является отчётом фермы."),
    ("gorilla-yard", "gorilla", "легенда", "Гориллы Радмира обновили схему", "Художественный сюжет: таблички у вымышленных складов.", "DEMO. Это не военная сводка и не описание настоящих действий."),
    ("gorilla-gate", "gorilla", "легенда", "GORILLA SQUAD нарисована у ворот", "Конфликт на карте остаётся игровым.", "DEMO. Никаких реальных операций и целей."),
    ("air-fleet", "poop-airlines", "авиапарк", "POOP AIRLINES показала пять бортов", "POOP-001…005 стоят в демонстрационном авиапарке.", "Билеты не продаются. Рейсы помечены DEMO."),
    ("air-route", "poop-airlines", "маршруты", "На схеме появились плечи Уфа — Москва и Казань — Сочи", "Расписание можно открыть на странице авиакомпании.", "Это не данные реального перевозчика."),
    ("peg-floor", "poop-empire", "биржа", "POOP EMPIRE GROUP держит первую строку биржи", "Виртуальные котировки обновляются внутри сайта.", "Это не настоящая фондовая биржа."),
    ("phone-dream", "poop-tech", "продукт", "Xiaomi 17T Pro появился в каталоге мечты", "Карточка ведёт в обычную корзину сайта.", "Если файл фотографии не был изображением, карточка честно обходится без чужой картинки."),
    ("tishka-bank-open", "tishka-bank", "банк", "TishkaBank открыл утреннее окно", "Бонусы карты лежат в пушистом банке легенды.", "DEMO. Счетов в настоящем банке страница не открывает."),
    ("kakashka-bank-desk", "kakashka-bank", "банк", "КАКАШКА БАНК связал карту и биржу", "Перевод в кабинете двигает бонусы и инвестиционный счёт.", "DEMO. POOP COINS в этот перевод не входят."),
]


FACTS = [
    ("poop-empire", "руслан, триллионеркин, владелец, главный, основатель", "Империей владеет и руководит Руслан Триллионеркин. Он основатель, владелец и генеральный директор POOP EMPIRE GROUP.", "/holding", "Схема холдинга"),
    ("two-toe", "двухпал, куриц, two-toe, старейш", "TWO-TOE CHICKEN CORP в этой хронике самая старая компания и первая разработка империи. С неё началась легенда, потом уже появились какашечные цеха.", "/company/two-toe", "TWO-TOE"),
    ("sergo-energy", "энергетик, sergo, серёга, банка", "SERGO ENERGY — какашечные энергетики Серёги. Банки есть в каталоге, это обычные товары сайта.", "/company/sergo-energy", "SERGO ENERGY"),
    ("poop-delivery", "доставк, курьер, самовывоз, штаб", "Доставка: курьер POOP DELIVERY или самовывоз из штаба на Максима Горького, 70/1. Курьер назначается при заказе, самовывоз курьера не просит.", "/delivery", "Доставка"),
    ("panda-group", "панда групп, кафе, сувенир", "PANDA GROUP — направление панд, сувениров и кафе внутри холдинга. Живых животных витрина не продаёт.", "/company/panda-group", "PANDA GROUP"),
    ("shmileon", "мёд, пасек, гриб, шампиньон, максуд, шмил", "SHMILEON HONEY & MUSHROOMS ведёт Максуд ШмильЁн: мёд, пасеки и шампиньоны. Компания в холдинге, но управляется отдельно.", "/company/shmileon", "SHMILEON"),
    ("gorilla", "радмир, горилл, gorilla", "GORILLA DEFENSE GROUP — вымышленная охрана предприятий под руководством Радмира Галлямова. Карта конфликтов игровая и помечена как DEMO.", "/company/gorilla", "GORILLA"),
    ("poop-airlines", "авиа, тимур, самолёт, рейс, airlines", "POOP AIRLINES возглавляет Тимур Сафин. Борта и рейсы демонстрационные, билет сайт не оформляет.", "/company/poop-airlines", "POOP AIRLINES"),
    ("", "казино, слот, рулетк, кость, монет", "POOP CASINO играет только на виртуальные POOP COINS. Их можно пополнить в зале пометкой DEMO: рубли и инвестиционный счёт при этом не тратятся.", "/casino", "Казино"),
    ("", "бирж, акци, котиров, инвестиц", "POOP STOCK EXCHANGE — виртуальная биржа. Акции покупаются с инвестиционного баланса, это не POOP COINS и не банковский счёт.", "/exchange", "Биржа"),
    ("", "тишк, хлоп", "Тишкины хлопья — фирменный завтрак с котом Тишкой. Карточка лежит в каталоге.", "/product/tishkiny-hlopya", "Хлопья"),
    ("tishka-bank", "тишка банк, tishkabank, бонус карты", "TishkaBank хранит бонусы какашечной карты. Это витрина, не банк: перевод в кабинете двигает только DEMO-суммы.", "/company/tishka-bank", "TishkaBank"),
    ("kakashka-bank", "какашка банк, казнач, перевод", "КАКАШКА БАНК связывает бонусы карты и инвестиционный счёт. POOP COINS на рубли не меняются.", "/company/kakashka-bank", "КАКАШКА БАНК"),
    ("", "xiaomi, 17t, телефон, смартфон", "Xiaomi 17T Pro стоит в каталоге мечты и заказывается как обычный товар сайта. Отдельной фотографии-файла в папке не нашлось: сохранённая страница — это HTML, не снимок.", "/product/xiaomi-17t-pro", "Карточка"),
]


def seed_desk():
    if Courier.query.count() == 0:
        for slug, name, nick, bio, spec, rating, done, status, eta, mark, photo in COURIERS:
            db.session.add(
                Courier(
                    slug=slug, name=name, nickname=nick, bio=bio, specialty=spec,
                    rating=rating, done_count=done, status=status, eta=eta, mark=mark, photo=photo,
                )
            )
    have = {row.slug for row in NewsPost.query.all()}
    for slug, company, category, title, excerpt, body in NEWS:
        if slug not in have:
            db.session.add(
                NewsPost(
                    slug=slug, title=title, excerpt=excerpt, body=body,
                    company_slug=company, category=category, is_published=True,
                )
            )
    if PandaFact.query.count() == 0:
        for company, keys, answer, link, label in FACTS:
            db.session.add(PandaFact(company_slug=company, keys=keys, answer=answer, link=link, link_label=label))
    else:
        have_keys = {row.keys for row in PandaFact.query.all()}
        for company, keys, answer, link, label in FACTS:
            if keys not in have_keys:
                db.session.add(PandaFact(company_slug=company, keys=keys, answer=answer, link=link, link_label=label))
    _phone()
    _banks()
    _headlines()
    db.session.commit()


def _banks():
    marks = {
        "TishkaBank": ("Пушистый банк бонусов карты. DEMO, не лицензия.", "images/tishka-bank.jpg", "/company/tishka-bank", 2),
        "КАКАШКА БАНК": ("Казначейство карты и биржи. DEMO.", "images/kakashka-bank.jpg", "/company/kakashka-bank", 3),
    }
    have = {row.title for row in Banner.query.all()}
    for title, (subtitle, image, link, sort) in marks.items():
        if title not in have:
            db.session.add(Banner(title=title, subtitle=subtitle, image=image, link=link, sort_order=sort, is_active=True))
    night = NewsPost.query.filter_by(slug="tishka-bank-night").first()
    if night is None:
        db.session.add(
            NewsPost(
                slug="tishka-bank-night",
                title="Ночной отчёт TishkaBank",
                excerpt="Запись появится позже: сервер смотрит на время публикации.",
                body="DEMO. Эта новость была поставлена в очередь и не видна, пока не наступит её время.",
                company_slug="tishka-bank",
                category="банк",
                is_published=True,
                publish_at=utcnow() + timedelta(hours=6),
            )
        )


def _headlines():
    planned = (
        ("world-cereal", "world", None, 150, timedelta(hours=-2), "DEMO · мировые хлопья задали тон утренней ленте", "Событие мира двигает все виртуальные бумаги. Это не новость настоящего рынка."),
        ("russia-scooters", "russia", None, 80, timedelta(minutes=-20), "DEMO · российский самокатный час поддержал холдинг", "Российская лента двигает только компании POOP EMPIRE GROUP."),
        ("kbk-evening", "russia", "KBK", 60, timedelta(minutes=40), "DEMO · вечерний отчёт КАКАШКА БАНК ещё не вышел", "Пока время не наступило, котировка от этой строки не меняется."),
    )
    have = {row.title for row in MarketNews.query.all()}
    for _key, region, ticker, bps, shift, title, body in planned:
        if title in have:
            continue
        company = ListedCompany.query.filter_by(ticker=ticker).first() if ticker else None
        db.session.add(
            MarketNews(
                company_id=company.id if company else None,
                title=title,
                body=body,
                region=region,
                impact_bps=bps,
                publish_at=utcnow() + shift,
                applied=False,
            )
        )


def _phone():
    if Product.query.filter_by(slug="xiaomi-17t-pro").first():
        return
    cat = Category.query.filter_by(slug="tech").first() or Category.query.first()
    if cat is None:
        return
    product = Product(
        category_id=cat.id,
        slug="xiaomi-17t-pro",
        sku="XIAOMI-17T-PRO",
        name="Xiaomi 17T Pro",
        short="Мечта Руслана в обычном каталоге. Заказ идёт через корзину сайта.",
        description=(
            "Xiaomi 17T Pro, 12/256 ГБ, чёрный. По открытым характеристикам: экран около 6,83 дюйма, "
            "камера с оптикой Leica, Dimensity 9500, батарея около 7000 мА·ч. "
            "В папке проекта лежит файл «xiaomi 17t pro.htm» — это сохранённая страница магазина, не фотография. "
            "Чужое изображение вместо неё не подставлено."
        ),
        composition="12/256 ГБ · чёрный · карточка мечты POOP TECH",
        price_kop=8999000,
        cost_kop=7000000,
        stock=3,
        is_featured=True,
        purchasable=True,
    )
    db.session.add(product)
