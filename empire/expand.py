"""Одноразовые дополнения к уже заполненной базе. Старые товары не удаляются."""

from sqlalchemy import inspect, text

from empire.art import write_product_mark
from empire.extensions import db
from empire.models import (
    Achievement,
    Category,
    Factory,
    FinanceRecord,
    Partner,
    Product,
    ProductImage,
    Review,
    SiteSetting,
    WheelPrize,
)
from empire.services import set_setting, setting

COLUMN_PATCHES = {
    "users": {
        "poop_coins": "INTEGER NOT NULL DEFAULT 0",
        "xp": "INTEGER NOT NULL DEFAULT 0",
        "extra_spins": "INTEGER NOT NULL DEFAULT 0",
        "free_deliveries": "INTEGER NOT NULL DEFAULT 0",
        "last_daily_spin": "DATE",
        "last_daily_coins": "DATE",
        "invest_kop": "INTEGER NOT NULL DEFAULT 100000000",
    },
    "factories": {
        "lat": "FLOAT",
        "lng": "FLOAT",
    },
    "orders": {
        "delivery_stage": "INTEGER NOT NULL DEFAULT 0",
        "next_stage_at": "DATETIME",
        "stage_updated_at": "DATETIME",
        "delivery_demo": "BOOLEAN NOT NULL DEFAULT 1",
        "courier_name": "VARCHAR(120) DEFAULT ''",
        "courier_id": "INTEGER",
        "pickup_notified": "BOOLEAN NOT NULL DEFAULT 0",
    },
    "news_posts": {
        "company_slug": "VARCHAR(80) DEFAULT ''",
        "category": "VARCHAR(80) DEFAULT 'империя'",
        "image": "VARCHAR(255) DEFAULT ''",
        "publish_at": "DATETIME",
    },
    "market_news": {
        "region": "VARCHAR(16) DEFAULT 'world'",
        "impact_bps": "INTEGER NOT NULL DEFAULT 0",
        "publish_at": "DATETIME",
        "applied": "BOOLEAN NOT NULL DEFAULT 0",
    },
}


def ensure_columns():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    for table, columns in COLUMN_PATCHES.items():
        if table not in tables:
            continue
        have = {column["name"] for column in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in have:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
    db.session.commit()
    db.create_all()


def rename_texts():
    pairs = (
        ("site_settings", "value"),
        ("partners", "name"),
        ("partners", "title"),
        ("partners", "role"),
        ("partners", "bio"),
        ("partners", "joke"),
        ("news_posts", "title"),
        ("news_posts", "excerpt"),
        ("news_posts", "body"),
        ("finance_records", "title"),
        ("finance_records", "note"),
        ("products", "name"),
        ("products", "short"),
        ("products", "description"),
    )
    for table, column in pairs:
        db.session.execute(
            text(f"UPDATE {table} SET {column} = REPLACE({column}, 'Миллиардеркин', 'Триллионеркин')")
        )
    db.session.commit()


def refresh_roles():
    if setting("roles_v2") == "1":
        return
    people = {
        "ruslan": {
            "name": "Руслан Триллионеркин",
            "title": "Основатель, владелец и генеральный директор",
            "role": "Управляет всей группой POOP EMPIRE GROUP: финансами, инвестициями, развитием и всеми подразделениями империи.",
            "bio": "Руслан собрал корпорацию как шутку, которая ведёт настоящий штаб: витрину, карты, заводы, доставку и финансовый зал. Биография на сайте — фирменный текст, а не справка из реестра.",
            "joke": "Руслан Триллионеркин настолько занят развитием своей корпорации, что практически не выходит гулять. Его стихия — кабинет, бизнес, финансы и управление крупнейшей какашечной империей.",
        },
        "artur": {
            "name": "Артур Ахметвалеев",
            "title": "Глава какашечных заводов России и директор по инновациям",
            "role": "Управление какашечными заводами по всей России. Контроль производства. Открытие новых предприятий. Разработка какашечных технологий. Управление лабораториями. Развитие промышленности. Создание новых видов какашечной продукции.",
            "bio": "Артур держит промышленный контур империи. В легенде корпорации он открывает заводы быстрее, чем протокол успевает их назвать, и считает инновацией всё, что хрустит иначе, чем вчера.",
            "joke": "Говорит, что лаборатория — это тоже завод, только с более тихим станком.",
        },
        "sergey": {
            "name": "Сергей Любин",
            "title": "Глава службы доставки POOP DELIVERY",
            "role": "Доставка заказов на самокатах. Курьеры. Логистика. Распределение заказов. Контроль доставки.",
            "bio": "Сергей — легендарный руководитель самокатной доставки. Управленческий подход у него особый: дисциплина измеряется не опозданием, а тем, успел ли самокат доехать раньше, чем остыл слоган. Это корпоративная шутка, не характеристика живого человека.",
            "joke": "Если заказ слишком долго лежит на складе, Сергей забирает его сам и называет это личным аудитом маршрута.",
        },
    }
    for slug, fields in people.items():
        row = Partner.query.filter_by(slug=slug).first()
        if row:
            for key, value in fields.items():
                setattr(row, key, value)
    set_setting("roles_v2", "1")
    db.session.commit()


def refresh_finance():
    if setting("finance_trillion") == "1":
        return
    targets = {
        "capital": (3847291650000, "Демонстрационный личный капитал триллионера. Не выписка и не оценка имущества."),
        "valuation": (9640000000000, "Демонстрационная стоимость корпорации. Не отчёт оценщика."),
        "revenue_fiction": (1820000000000, "Демонстрационная легенда холдинга. Выручка магазина считается отдельно из заказов."),
        "profit_fiction": (640000000000, "Демонстрационная легенда. Прибыль витрины считается из заказов."),
    }
    for section, (amount, note) in targets.items():
        row = FinanceRecord.query.filter_by(section=section).order_by(FinanceRecord.id).first()
        if row:
            row.amount_rub = amount
            row.note = note
            row.is_fiction = True
    for row in FinanceRecord.query.filter(FinanceRecord.section.in_(["investment", "asset", "deal", "income", "forecast"])).all():
        if row.amount_rub < 100_000_000_000:
            row.amount_rub *= 40
            if "Демонстрац" not in (row.note or ""):
                row.note = ((row.note or "") + " Демонстрационная сумма.").strip()
    set_setting("finance_trillion", "1")
    db.session.commit()


GOODS = [
    ("classic-poop", "Классические какашки", "sami-kakashki", 390, "Базовая форма имперской коллекции.", "Размер M, материал: сувенирный полимер", False),
    ("small-poop", "Маленькие какашки", "sami-kakashki", 190, "Карманный формат для протокола.", "Размер S", False),
    ("medium-poop", "Средние какашки", "sami-kakashki", 490, "Середина линейки, любимая складом.", "Размер M+", False),
    ("huge-poop", "Огромные какашки", "sami-kakashki", 1490, "Не влезают в обычную полку.", "Размер XL", False),
    ("gold-poop", "Золотые какашки", "sami-kakashki", 4990, "Золотистое покрытие для кабинета.", "Покрытие: золотистая эмаль", False),
    ("silver-poop", "Серебряные какашки", "sami-kakashki", 3990, "Серебро для совета, который любит скромнее.", "Покрытие: серебристая эмаль", False),
    ("rainbow-poop", "Радужные какашки", "sami-kakashki", 890, "Все цвета квартального отчёта сразу.", "Градиентная окраска", False),
    ("glow-poop", "Светящиеся какашки", "sami-kakashki", 990, "Светятся, когда в кабинете гасят люстру.", "Люминесцентный слой", False),
    ("collect-poop", "Коллекционные какашки", "sami-kakashki", 2590, "Номерная серия для витрины.", "Сертификат шутки в комплекте", False),
    ("premium-poop", "Премиальные какашки", "sami-kakashki", 3290, "Футляр и лента, как у печати.", "Футляр, лента", False),
    ("limited-poop", "Лимитированная серия «Кабинет»", "sami-kakashki", 4590, "Тираж, который якобы не повторят.", "Лимитированный тираж", False),
    ("surprise-poop", "Какашки-сюрпризы", "sami-kakashki", 690, "Внутри записка от штаба.", "Скрытый вкладыш", False),
    ("trillion-set", "Набор какашек триллионера", "sami-kakashki", 9990, "Семь форм и одна инструкция не выходить гулять.", "7 предметов", False),
    ("poop-juice", "Какашечный сок", "kakashki-napitki", 220, "Сок цвета отчёта, без какашек внутри.", "Вода, яблоко, карамель", False),
    ("poop-cola", "Какашечная кола", "kakashki-napitki", 180, "Газировка с фирменным шильдом.", "Вода, сахар, карамель", False),
    ("poop-lime", "Какашечный лимонад", "kakashki-napitki", 170, "Кислый, как замечание аудитора.", "Лимон, газ, сахар", False),
    ("poop-soda", "Какашечная газировка", "kakashki-napitki", 150, "Пузыри и никаких обещаний витаминов.", "Газированная вода, ароматизатор", False),
    ("poop-signature", "Фирменный напиток POOP", "kakashki-napitki", 320, "То, что наливают на планёрке.", "Секрет штаба, опубликованный на этикетке", False),
    ("liquid-gold", "Напиток «Жидкое золото»", "kakashki-napitki", 540, "Сладкий и слишком торжественный.", "Мёд, вода, золотистый краситель", False),
    ("drink-gift", "Подарочный набор напитков", "kakashki-napitki", 1290, "Шесть бутылок и открытка Тишки.", "Набор 6×0.33", False),
    ("energy-original", "POOP ENERGY Original", "poop-energy", 210, "Базовый энергетик линейки.", "Кофеин, таурин, вода", False),
    ("energy-gold", "POOP ENERGY Gold", "poop-energy", 290, "Золотая банка для золотой планёрки.", "Кофеин, вкус манго", False),
    ("energy-black", "POOP ENERGY Black", "poop-energy", 310, "Чёрная банка, белая надпись.", "Кофеин, вкус колы", False),
    ("energy-max", "POOP ENERGY Maximum", "poop-energy", 340, "Максимум бодрости, которую штаб готов признать.", "Повышенный кофеин", False),
    ("energy-trillion", "POOP ENERGY Trillionaire Edition", "poop-energy", 490, "Издание для тех, кто считает нули.", "Лимитированная банка", False),
    ("energy-night", "POOP ENERGY «Ночь в кабинете»", "poop-energy", 360, "Лимитированный выпуск для поздних сводок.", "Кофеин, ваниль", False),
    ("poop-vodka", "POOP VODKA", "kakashki-alcohol", 1890, "Только витрина. Продажа не подключена.", "Демонстрационный образец 18+", True),
    ("poop-whisky", "Какашечный виски", "kakashki-alcohol", 4590, "Бутылка для полки, не для корзины.", "Демонстрационный образец 18+", True),
    ("poop-liqueur", "Какашечный ликёр", "kakashki-alcohol", 2290, "Сладкая витринная позиция.", "Демонстрационный образец 18+", True),
    ("poop-bottle", "Премиальная бутылка POOP", "kakashki-alcohol", 6990, "Футляр и никакой кнопки «купить».", "Демонстрационный образец 18+", True),
    ("alcohol-gift", "Коллекционный алкогольный набор", "kakashki-alcohol", 9990, "Набор смотрят, не заказывают.", "Демонстрационный набор 18+", True),
    ("plush-poop", "Плюшевая какашка", "igrushki", 790, "Мягкая, для дивана в приёмной.", "Текстиль, наполнитель", False),
    ("stress-poop", "Какашка-антистресс", "igrushki", 450, "Мнётся лучше, чем черновик приказа.", "Эластомер", False),
    ("figure-poop", "Фигурка какашки", "igrushki", 650, "Стоит на мониторе и смотрит в таблицу.", "Полимер", False),
    ("interactive-poop", "Интерактивная какашка", "igrushki", 1890, "Издаёт хруст, если её не игнорировать.", "Батарейка в комплекте", False),
    ("rc-poop", "Какашка на пульте", "igrushki", 3490, "Едет по ковру медленнее Сергея.", "Пульт, колёса", False),
    ("key-poop", "Брелок POOP", "igrushki", 290, "Маленький ключ от шутки.", "Металл", False),
    ("toy-collect", "Коллекционная игрушка POOP", "igrushki", 1590, "Серия для тех, кто собирает всё.", "Номер на подставке", False),
    ("figure-ruslan", "Фигурка Руслана Триллионеркина", "igrushki", 2590, "Мини-основатель, который тоже не гуляет.", "Полимер, подставка", False),
    ("figure-artur", "Фигурка Артура", "igrushki", 2190, "С крошечным чертежом завода.", "Полимер", False),
    ("figure-sergey", "Фигурка Сергея на самокате", "igrushki", 2390, "Самокат съёмный, дисциплина нет.", "Полимер, самокат", False),
    ("figure-tishka", "Фигурка Тишки", "igrushki", 1990, "Пушистый партнёр в миниатюре.", "Полимер", False),
    ("tee-empire", "Футболка POOP EMPIRE", "odezhda-empire", 2490, "Чёрная футболка с золотым шильдом.", "Хлопок", False),
    ("cap-trillion", "Кепка триллионера", "odezhda-empire", 1890, "Козырёк шире, чем прогулка основателя.", "Хлопок, вышивка", False),
    ("mug-trillion", "Кружка триллионера", "aksessuary", 990, "Влезает эспрессо и один нуль.", "Керамика", False),
    ("pin-empire", "Значок POOP EMPIRE", "aksessuary", 390, "На лацкан пиджака, который не выходит на улицу.", "Металл", False),
    ("choco-poop", "Шоколадные какашки", "sladosti", 450, "Шоколад. Форма шуточная, вкус обычный.", "Какао, сахар", False),
    ("marmalade-poop", "Мармеладные какашки", "sladosti", 320, "Жевательные, яркие, без философии.", "Мармелад, сахар", False),
    ("candy-poop", "Конфеты POOP", "sladosti", 280, "Коробка к чаю после планёрки.", "Сахар, патока", False),
    ("gift-safe", "Подарочный набор «Сейф»", "podarki-empire", 4590, "Коробка с лентой и тремя маленькими формами.", "Сборный набор", False),
    ("collect-cert", "Коллекционный сертификат империи", "kollekciya-tovarov", 1500, "Бумага, которая ничего не обещает банку.", "Бумага, печать", False),
    ("ruslan-seal", "Эксклюзив Руслана: печать кабинета", "eksklyuziv-ruslana", 8900, "Только для тех, кого пустили в шутку совета.", "Металл, подушка", False),
    ("secret-crate", "Ящик секретного склада", "secret-sklad", 12900, "Что внутри, склад рассказывает шёпотом в описании.", "Сборный набор, пломба", False),
]


CATEGORIES = [
    ("sami-kakashki", "Сами какашки", "Формы, серии и наборы", 10),
    ("kakashki-napitki", "Какашечные напитки", "Соки, кола и лимонад без лишней серьёзности", 11),
    ("poop-energy", "Какашечные энергетики", "Линейка POOP ENERGY", 12),
    ("kakashki-alcohol", "Какашечный алкоголь", "Только демонстрационная витрина 18+", 13),
    ("igrushki", "Игрушки", "Плюш, фигурки и пульты", 14),
    ("odezhda-empire", "Одежда POOP EMPIRE", "То, что носят в штабе", 15),
    ("aksessuary", "Кружки и аксессуары", "Мелочи с шильдом", 16),
    ("sladosti", "Сладости", "Шоколад, мармелад и конфеты", 17),
    ("podarki-empire", "Подарочные наборы империи", "Коробки для партнёров", 18),
    ("kollekciya-tovarov", "Коллекционные товары", "То, что ставят на полку", 19),
    ("eksklyuziv-ruslana", "Эксклюзив Руслана", "Вещи из кабинета", 20),
    ("secret-sklad", "Секретный склад триллионера", "Закрытая витрина, которая всё равно открыта", 21),
]


FACTORIES = [
    ("spb-poop", "Северная какашечная мануфактура", "Санкт-Петербург", "Северо-Запад", 2016, "Артур Ахметвалеев", 420, "12 тонн сувениров в месяц", "Классические и серебряные формы", "Тихая полировка", 24000000000, "Завод", 28, 22),
    ("moscow-lab", "Лаборатория «Кабинет-1»", "Москва", "Центр", 2018, "Артур Ахметвалеев", 180, "40 опытных партий в месяц", "Светящиеся формы", "Люминесцентный слой", 18000000000, "Лаборатория", 34, 30),
    ("kazan-drink", "Казанский завод напитков", "Казань", "Поволжье", 2019, "Лилия Штабная", 260, "1.2 млн бутылок", "Кола и лимонад", "Пузырь с золотой кромкой", 15000000000, "Напитки", 42, 34),
    ("sochi-toy", "Сочинский цех игрушек", "Сочи", "Юг", 2020, "Пётр Плюшев", 140, "80 тыс. игрушек", "Плюш и антистресс", "Мягкий каркас", 9000000000, "Игрушки", 30, 48),
    ("ekb-energy", "Уральский завод POOP ENERGY", "Екатеринбург", "Урал", 2017, "Артур Ахметвалеев", 310, "2 млн банок", "Original и Gold", "Банка, которая не мнётся в отчёте", 21000000000, "Энергетики", 48, 32),
    ("novosib-hub", "Новосибирский логистический комплекс", "Новосибирск", "Сибирь", 2021, "Сергей Любин", 190, "400 самокатов на схеме", "Склад и отгрузка", "Ночная сортировка", 11000000000, "Логистика", 58, 36),
    ("krasnoyarsk", "Красноярский исследовательский центр", "Красноярск", "Сибирь", 2022, "Артур Ахметвалеев", 90, "12 патентов-шуток", "Радужные пигменты", "Пигмент «квартал»", 7000000000, "Исследования", 64, 34),
    ("irkutsk-wh", "Иркутский склад", "Иркутск", "Сибирь", 2015, "Кладовщик Байкал", 70, "Хранение 3 месяцев спроса", "Серии и футляры", "Холодный архив", 4000000000, "Склад", 70, 38),
    ("vladivostok", "Тихоокеанский завод форм", "Владивосток", "Дальний Восток", 2023, "Артур Ахметвалеев", 150, "6 тонн в месяц", "Огромные формы", "Морская сушка", 8000000000, "Завод", 92, 42),
    ("yakutsk-lab", "Якутская лаборатория холода", "Якутск", "Дальний Восток", 2024, "Артур Ахметвалеев", 40, "Зимние опыты", "Светящиеся серии", "Мороз как технология", 3000000000, "Лаборатория", 78, 18),
    ("murmansk", "Мурманский цех энергетика", "Мурманск", "Север", 2018, "Нора Полярная", 110, "Полярная смена", "Black и Maximum", "Этикетка, которую видно в полярную ночь", 6000000000, "Энергетики", 36, 8),
    ("kaliningrad", "Калининградский анклав-цех", "Калининград", "Запад", 2020, "Артур Ахметвалеев", 60, "Малый тираж", "Лимитированные серии", "Короткий цикл", 2500000000, "Завод", 12, 28),
]


def add_catalog():
    cats = {row.slug: row for row in Category.query.all()}
    for slug, name, desc, sort in CATEGORIES:
        if slug not in cats:
            row = Category(slug=slug, name=name, description=desc, sort_order=sort)
            db.session.add(row)
            cats[slug] = row
    db.session.flush()
    for slug, name, cat, price, short, specs, alcohol in GOODS:
        if Product.query.filter_by(slug=slug).first():
            continue
        rub = price * 100
        product = Product(
            category_id=cats[cat].id,
            slug=slug,
            sku="PE-" + slug[:18].upper(),
            name=name,
            short=short,
            description=short + "\n\nДемонстрационный товар POOP EMPIRE GROUP. Оплата на сайте не списывает деньги.",
            composition=specs,
            price_kop=rub,
            cost_kop=int(rub * 0.45),
            stock=0 if alcohol else 36,
            rating=4.7,
            review_count=1,
            is_active=True,
            purchasable=not alcohol,
            age_restricted=alcohol,
            is_featured=slug in {"gold-poop", "energy-trillion", "trillion-set"},
        )
        db.session.add(product)
        db.session.flush()
        portraits = {
            "figure-ruslan": "images/ruslan.jpg",
            "figure-artur": "images/artur.jpg",
            "figure-sergey": "images/sergey.jpg",
            "figure-tishka": "images/tishka.jpg",
        }
        path = portraits.get(slug) or write_product_mark(slug, name)
        db.session.add(ProductImage(product_id=product.id, path=path, sort_order=0))
        db.session.add(Review(product_id=product.id, author="Штаб", rating=5, text="Демонстрационный отзыв витрины.", approved=True))
    db.session.commit()


def add_wheel():
    if WheelPrize.query.count():
        return
    prizes = [
        ("Скидка 5%", "percent", 5, 18),
        ("Скидка 10%", "percent", 10, 14),
        ("Скидка 20%", "percent", 20, 8),
        ("Скидка 50%", "percent", 50, 4),
        ("Бесплатная доставка", "shipping", 1, 12),
        ("100 POOP COINS", "coins", 100, 16),
        ("500 POOP COINS", "coins", 500, 8),
        ("Секретный подарок", "gift", 250, 8),
        ("Бесплатный товар", "product", 100, 3),
        ("Джекпот Руслана Триллионеркина", "jackpot", 5000, 2),
    ]
    for index, (title, kind, amount, weight) in enumerate(prizes, start=1):
        db.session.add(WheelPrize(title=title, kind=kind, amount=amount, weight=weight, sort_order=index))
    db.session.commit()


def add_factories():
    if Factory.query.count():
        return
    for slug, name, city, region, year, boss, staff, capacity, products, innovation, revenue, kind, x, y in FACTORIES:
        db.session.add(
            Factory(
                slug=slug,
                name=name,
                city=city,
                region=region,
                founded=year,
                boss=boss,
                staff=staff,
                capacity=capacity,
                products=products,
                innovation=innovation,
                revenue_rub=revenue,
                status="Демонстрационный объект",
                kind=kind,
                pos_x=x,
                pos_y=y,
            )
        )
    db.session.commit()


def add_achievements():
    rows = [
        ("first-spin", "Первый оборот", "Крутануть POOP WHEEL.", 20),
        ("first-bet", "Первый спин", "Сыграть в POOP CASINO на виртуальные монеты.", 20),
        ("first-win", "Первый выигрыш", "Получить выплату в казино.", 30),
        ("coin-hoard", "Карман с монетами", "Накопить 1000 POOP COINS.", 40),
        ("delivery-watch", "Ждать самокат", "Открыть трек демонстрационной доставки.", 10),
        ("big-win", "Первая крупная победа", "Выигрыш не меньше чем в восемь раз выше ставки.", 40),
        ("gold-luck", "Золотая удача", "Поймать множитель GOLDEN POOP от ×5.", 30),
        ("roulette-fan", "Любитель рулетки", "Сыграть пять партий в рулетку.", 25),
        ("dice-lord", "Повелитель кубиков", "Сыграть пять партий в кости.", 25),
        ("jackpot-hunter", "Охотник за джекпотом", "Открыть сейф TRILLIONAIRE.", 80),
        ("casino-legend", "Легенда POOP CASINO", "Сыграть 50 партий.", 50),
    ]
    have = {row.code: row for row in Achievement.query.all()}
    for code, title, desc, xp in rows:
        if code not in have:
            db.session.add(Achievement(code=code, title=title, description=desc, xp=xp))
        elif code in {"first-bet", "first-win"}:
            have[code].title = title
            have[code].description = desc
    db.session.commit()


def expand():
    ensure_columns()
    rename_texts()
    refresh_roles()
    refresh_finance()
    if not SiteSetting.query.filter_by(key="delivery_step_min").first():
        set_setting("delivery_step_min", "8")
        set_setting("delivery_step_max", "20")
        set_setting("daily_coins", "200")
        db.session.commit()
    add_catalog()
    add_wheel()
    add_factories()
    add_achievements()
    from empire.universe import install
    from empire.desk import seed_desk

    install()
    seed_desk()
