"""Холдинг, дочерние компании и демонстрационная биржа. Цифры — DEMO."""

import random
import shutil
import time
from datetime import date

from sqlalchemy import or_, text

from empire.art import write_product_mark
from empire.config import ROOT
from empire.extensions import db
from empire.models import (
    Category,
    Factory,
    ListedCompany,
    MarketNews,
    Partner,
    Product,
    ProductImage,
    Review,
    StockHolding,
    StockTick,
    StockTrade,
    InvestLedger,
    User,
    utcnow,
)
from empire.services import set_setting, setting

# slug, ticker, name, tagline, boss, theme, holding, shares, price_rub, staff, sites, revenue_rub, sort
COMPANIES = [
    ("poop-empire", "PEG", "POOP EMPIRE GROUP", "Крупнейшая какашечная империя", "Руслан Триллионеркин", "poop", True, 800_000_000, 12500, 186000, 120, 9_640_000_000_000, 1),
    ("golden-poop", "GPI", "GOLDEN POOP INDUSTRIES", "Промышленное производство какашечной продукции", "Артур Ахметвалеев", "industry", True, 120_000_000, 640, 84000, 89, 1_820_000_000_000, 2),
    ("sergo-energy", "SEG", "SERGO ENERGY", "Какашечные энергетики от Серёги", "Серёга", "energy", True, 40_000_000, 210, 6200, 14, 240_000_000_000, 3),
    ("poop-delivery", "POD", "POOP DELIVERY", "Самокатная доставка по России", "Серёга", "delivery", True, 35_000_000, 180, 9100, 48, 96_000_000_000, 4),
    ("panda-group", "PNG", "PANDA GROUP", "Панды, кафе, сувениры и охрана природы", "направление под контролем Руслана", "panda", True, 55_000_000, 430, 7400, 18, 310_000_000_000, 5),
    ("two-toe", "TTC", "TWO-TOE CHICKEN CORP", "Двухпалые курицы как отдельная отрасль", "Артур Ахметвалеев", "chicken", True, 28_000_000, 155, 4100, 9, 74_000_000_000, 6),
    ("poop-tech", "PTC", "POOP TECH", "Технологии и инновации империи", "Артур Ахметвалеев", "tech", True, 22_000_000, 520, 1800, 6, 128_000_000_000, 7),
    ("shmileon", "SHM", "SHMILEON HONEY & MUSHROOMS", "Пчёлы, шампиньоны и большие корпоративные амбиции", "Максуд ШмильЁн", "honey", True, 18_000_000, 260, 960, 7, 41_000_000_000, 8),
    ("gorilla", "GDG", "GORILLA DEFENSE GROUP", "Вымышленная охрана предприятий империи", "Радмир Галлямов", "military", True, 12_000_000, 190, 2400, 11, 36_000_000_000, 9),
    ("poop-airlines", "PAL", "POOP AIRLINES", "Пассажиры и груз внутри легенды холдинга", "Тимур Сафин", "air", True, 20_000_000, 340, 3800, 16, 88_000_000_000, 10),
    ("royal-toilet", "RTH", "ROYAL TOILET HOLDING", "Конкурирующий холдинг сантехнических амбиций", "совет конкурентов", "rival", False, 60_000_000, 390, 12000, 20, 210_000_000_000, 11),
    ("mega-dung", "MDC", "MEGA DUNG COMPANY", "Промышленный конкурент по сырью", "правление конкурента", "rival", False, 48_000_000, 275, 15000, 16, 160_000_000_000, 12),
    ("fecal-food", "FFG", "FECAL FOOD GROUP", "Продукты и напитки вне контура Руслана", "правление конкурента", "rival", False, 30_000_000, 140, 4300, 11, 55_000_000_000, 13),
    ("tishka-bank", "TBK", "TishkaBank", "Пушистый банк завтраков и бонусов", "Тишка", "bank", True, 8_000_000, 90, 420, 6, 12_000_000_000, 14),
    ("kakashka-bank", "KBK", "КАКАШКА БАНК", "Казначейский банк империи", "Руслан Триллионеркин", "bank", True, 15_000_000, 120, 1800, 12, 48_000_000_000, 15),
]

STORIES = {
    "poop-empire": "POOP EMPIRE GROUP — холдинг Руслана Триллионеркина. Он владеет группой, принимает стратегические решения и держит дочерние компании в одном контуре. Все суммы на этой странице помечены DEMO и не являются отчётностью.",
    "golden-poop": "Промышленный контур Артура: заводы, лаборатории и новые формы. Каждая точка на карте России — вымышленный объект легенды, а не адрес действующего производства.",
    "sergo-energy": "SERGO ENERGY делает POOP ENERGY BY SERGO, SERGO GOLD, SERGO BLACK и SERGO TRILLIONAIRE. Бренд использует фотографию «Серго-энергетик» как фирменный образ, отдельно от портрета в руководстве.",
    "poop-delivery": "POOP DELIVERY возит заказы на самокатах. Это таймер статусов в магазине, а не GPS. Серёга отвечает за курьеров, хабы и скорость в корпоративной шутке.",
    "panda-group": "PANDA GROUP финансируется холдингом Руслана: фермы, исследовательские центры, сувениры, кафе, сладости и природоохранный журнал. Живых панд сайт не продаёт и деньги фонду не переводит.",
    "two-toe": "TWO-TOE CHICKEN CORP — старейшая компания хроники и первая разработка будущей империи. С неё в художественной легенде начались двухпалые курицы, и только потом вырос какашечный холдинг. Это не история реального предприятия.",
    "gorilla": "GORILLA DEFENSE GROUP — вымышленная служба Радмира Галлямова. Гориллы в легенде охраняют заводы и склады империи и спорят с другими какашечными корпорациями за влияние на карте. Это игровая схема, не военная сводка и не описание настоящих действий.",
    "poop-airlines": "POOP AIRLINES — авиакомпания Тимура Сафина внутри холдинга. Рейсы, борта и пассажиропоток демонстрационные. Билеты не продаются и брони у перевозчиков нет.",
    "poop-tech": "POOP TECH собирает лабораторные шутки Артура: пигменты, упаковку и всё, что можно назвать технологией на планёрке.",
    "shmileon": "SHMILEON HONEY & MUSHROOMS — дочерняя компания Максуда ШмильЁна. Он сам ведёт пасеки и грибные залы, а стратегически компания входит в империю Руслана. Публичный адрес предприятия вымышленный: демонстрационный двор холдинга, без домашнего адреса.",
    "royal-toilet": "Конкурент на бирже. В холдинг Руслана не входит.",
    "mega-dung": "Промышленный конкурент. Котировка демонстрационная.",
    "fecal-food": "Пищевой конкурент за пределами витрины POOP EMPIRE.",
    "tishka-bank": "TishkaBank — вымышленный банк Тишки внутри холдинга. Он показывает бонусы какашечной карты и не открывает настоящих счетов. Переводы в кабинете остаются DEMO: рубли с банковской карты никуда не уходят.",
    "kakashka-bank": "КАКАШКА БАНК — казначейская легенда Руслана. Через него в кабинете связаны бонусы карты и инвестиционный счёт биржи. POOP COINS сюда не входят и на рубли не меняются. Это не лицензированный банк.",
}

BRANCHES = {
    "poop-empire": "DEMO · Кабинет основателя\nDEMO · Инвестиционный контур\nDEMO · Совет дочерних компаний",
    "golden-poop": "DEMO · Заводы во всех регионах схемы\nDEMO · Лаборатории Артура\nDEMO · Служба качества",
    "sergo-energy": "DEMO · Линия SERGO GOLD\nDEMO · Линия SERGO BLACK\nDEMO · Цех лимитированных банок",
    "poop-delivery": "DEMO · Хаб самокатов «Запад»\nDEMO · Хаб «Волга»\nDEMO · Хаб «Сибирь»",
    "panda-group": "DEMO · Панда-ферма «Бамбук»\nDEMO · Панда-кафе\nDEMO · Сувенирный дом\nDEMO · Журнал охраны природы",
    "two-toe": "DEMO · Инкубатор «Два пальца»\nDEMO · Селекционный центр\nDEMO · Птицефабрика-витрина",
    "poop-tech": "DEMO · Лаборатория пигмента\nDEMO · Цех упаковки",
    "shmileon": "DEMO · Пасека «Золотой улей»\nDEMO · Грибной зал «Шампиньон»\nDEMO · Фасовка мёда\nDEMO · Двор холдинга, местонахождение вымышленное",
    "gorilla": "GORILLA SQUAD\nGORILLA SECURITY\nPOOP EMPIRE PROTECTION\nGORILLA RAPID RESPONSE",
    "poop-airlines": "DEMO · Уфа\nDEMO · Казань\nDEMO · Москва\nDEMO · Сочи\nГрузовой контур SHMILEON CARGO",
    "tishka-bank": "DEMO · Отделение «Утренний хруст»\nDEMO · Касса бонусов карты\nDEMO · Окно хлопьев",
    "kakashka-bank": "DEMO · Казначейство холдинга\nDEMO · Окно инвестиционного счёта\nDEMO · Зал переводов кабинета",
}

# город, регион, широта, долгота
REGIONS = [
    ("Москва", "Москва", 55.75, 37.62),
    ("Подольск", "Московская область", 55.43, 37.54),
    ("Санкт-Петербург", "Санкт-Петербург", 59.94, 30.31),
    ("Гатчина", "Ленинградская область", 59.57, 30.12),
    ("Севастополь", "Севастополь", 44.62, 33.53),
    ("Симферополь", "Республика Крым", 44.95, 34.10),
    ("Майкоп", "Адыгея", 44.61, 40.11),
    ("Горно-Алтайск", "Республика Алтай", 51.96, 85.96),
    ("Барнаул", "Алтайский край", 53.35, 83.78),
    ("Благовещенск", "Амурская область", 50.29, 127.54),
    ("Архангельск", "Архангельская область", 64.54, 40.54),
    ("Астрахань", "Астраханская область", 46.35, 48.04),
    ("Уфа", "Башкортостан", 54.74, 55.97),
    ("Белгород", "Белгородская область", 50.60, 36.59),
    ("Брянск", "Брянская область", 53.24, 34.37),
    ("Улан-Удэ", "Бурятия", 51.83, 107.61),
    ("Владимир", "Владимирская область", 56.14, 40.40),
    ("Волгоград", "Волгоградская область", 48.71, 44.51),
    ("Вологда", "Вологодская область", 59.22, 39.89),
    ("Воронеж", "Воронежская область", 51.67, 39.18),
    ("Махачкала", "Дагестан", 42.98, 47.50),
    ("Биробиджан", "Еврейская автономная область", 48.79, 132.92),
    ("Чита", "Забайкальский край", 52.03, 113.50),
    ("Иваново", "Ивановская область", 57.00, 40.97),
    ("Магас", "Ингушетия", 43.17, 44.81),
    ("Иркутск", "Иркутская область", 52.29, 104.28),
    ("Нальчик", "Кабардино-Балкария", 43.50, 43.62),
    ("Калининград", "Калининградская область", 54.71, 20.51),
    ("Элиста", "Калмыкия", 46.31, 44.27),
    ("Калуга", "Калужская область", 54.51, 36.26),
    ("Петропавловск-Камчатский", "Камчатский край", 53.02, 158.65),
    ("Черкесск", "Карачаево-Черкесия", 44.23, 42.06),
    ("Петрозаводск", "Карелия", 61.78, 34.35),
    ("Кемерово", "Кемеровская область", 55.35, 86.09),
    ("Киров", "Кировская область", 58.60, 49.66),
    ("Сыктывкар", "Коми", 61.67, 50.84),
    ("Кострома", "Костромская область", 57.77, 40.93),
    ("Краснодар", "Краснодарский край", 45.04, 38.98),
    ("Красноярск", "Красноярский край", 56.02, 92.87),
    ("Курган", "Курганская область", 55.44, 65.34),
    ("Курск", "Курская область", 51.73, 36.19),
    ("Липецк", "Липецкая область", 52.61, 39.59),
    ("Магадан", "Магаданская область", 59.56, 150.80),
    ("Йошкар-Ола", "Марий Эл", 56.63, 47.89),
    ("Саранск", "Мордовия", 54.18, 45.17),
    ("Мурманск", "Мурманская область", 68.97, 33.09),
    ("Нарьян-Мар", "Ненецкий автономный округ", 67.64, 53.00),
    ("Нижний Новгород", "Нижегородская область", 56.33, 44.00),
    ("Великий Новгород", "Новгородская область", 58.52, 31.27),
    ("Новосибирск", "Новосибирская область", 55.03, 82.92),
    ("Омск", "Омская область", 54.99, 73.37),
    ("Оренбург", "Оренбургская область", 51.77, 55.10),
    ("Орёл", "Орловская область", 52.97, 36.07),
    ("Пенза", "Пензенская область", 53.20, 45.00),
    ("Пермь", "Пермский край", 58.01, 56.25),
    ("Владивосток", "Приморский край", 43.12, 131.89),
    ("Псков", "Псковская область", 57.82, 28.33),
    ("Ростов-на-Дону", "Ростовская область", 47.23, 39.72),
    ("Рязань", "Рязанская область", 54.63, 39.74),
    ("Самара", "Самарская область", 53.20, 50.15),
    ("Саратов", "Саратовская область", 51.53, 46.03),
    ("Якутск", "Саха (Якутия)", 62.03, 129.73),
    ("Южно-Сахалинск", "Сахалинская область", 46.96, 142.73),
    ("Екатеринбург", "Свердловская область", 56.84, 60.60),
    ("Владикавказ", "Северная Осетия", 43.02, 44.68),
    ("Смоленск", "Смоленская область", 54.78, 32.05),
    ("Ставрополь", "Ставропольский край", 45.04, 41.97),
    ("Тамбов", "Тамбовская область", 52.72, 41.45),
    ("Казань", "Татарстан", 55.79, 49.12),
    ("Тверь", "Тверская область", 56.86, 35.92),
    ("Томск", "Томская область", 56.50, 84.97),
    ("Тула", "Тульская область", 54.20, 37.62),
    ("Кызыл", "Тыва", 51.72, 94.45),
    ("Тюмень", "Тюменская область", 57.15, 65.53),
    ("Ижевск", "Удмуртия", 56.85, 53.20),
    ("Ульяновск", "Ульяновская область", 54.31, 48.40),
    ("Хабаровск", "Хабаровский край", 48.48, 135.07),
    ("Абакан", "Хакасия", 53.72, 91.43),
    ("Ханты-Мансийск", "Ханты-Мансийский автономный округ", 61.00, 69.02),
    ("Челябинск", "Челябинская область", 55.16, 61.40),
    ("Грозный", "Чечня", 43.32, 45.69),
    ("Чебоксары", "Чувашия", 56.13, 47.25),
    ("Анадырь", "Чукотский автономный округ", 64.73, 177.51),
    ("Салехард", "Ямало-Ненецкий автономный округ", 66.53, 66.61),
    ("Ярославль", "Ярославская область", 57.63, 39.87),
    ("Сочи", "Краснодарский край", 43.60, 39.73),
]


def copy_photos():
    folder = ROOT
    static = ROOT + "/static/images"
    pairs = (
        ("максуд шмильен.jpg", "maksud.jpg"),
        ("серго энергетик.jpg", "sergo-energy.jpg"),
        ("радмир галлямов.jpg", "radmir.jpg"),
        ("тимур сафин.jpg", "timur.jpg"),
        ("чорт быля.jpg", "secret-empire.jpg"),
    )
    for src_name, dest_name in pairs:
        src = folder + "/" + src_name
        dest = static + "/" + dest_name
        try:
            shutil.copyfile(src, dest)
        except OSError:
            pass


def seed_companies():
    for row in COMPANIES:
        slug, ticker, name, tagline, boss, theme, holding, shares, price, staff, sites, revenue, sort = row
        company = ListedCompany.query.filter_by(slug=slug).first()
        price_kop = price * 100
        photo = ""
        if slug == "shmileon":
            photo = "images/maksud.jpg"
        elif slug == "sergo-energy":
            photo = "images/sergo-energy.jpg"
        elif slug == "poop-empire":
            photo = "images/ruslan.jpg"
        elif slug in {"golden-poop", "two-toe", "poop-tech"}:
            photo = "images/artur.jpg"
        elif slug == "poop-delivery":
            photo = "images/sergey.jpg"
        elif slug == "gorilla":
            photo = "images/radmir.jpg"
        elif slug == "poop-airlines":
            photo = "images/timur.jpg"
        elif slug == "tishka-bank":
            photo = "images/tishka-bank.jpg"
        elif slug == "kakashka-bank":
            photo = "images/kakashka-bank.jpg"
        if company is None:
            company = ListedCompany(
                slug=slug,
                ticker=ticker,
                name=name,
                tagline=tagline,
                summary=STORIES[slug],
                story=STORIES[slug],
                boss=boss,
                boss_photo=photo,
                theme=theme,
                in_holding=holding,
                listed=True,
                shares=shares,
                price_kop=price_kop,
                day_open_kop=price_kop,
                volume=10_000 + sort * 1000,
                staff=staff,
                sites=sites,
                revenue_demo=revenue,
                branches=BRANCHES.get(slug, "DEMO · представительство"),
                sort_order=sort,
            )
            db.session.add(company)
            db.session.flush()
            walk = price_kop
            rng = random.Random(slug)
            for _ in range(24):
                walk = max(100, int(walk * (1 + rng.uniform(-0.02, 0.02))))
                db.session.add(StockTick(company_id=company.id, price_kop=walk))
            company.price_kop = walk
            company.day_open_kop = price_kop
        elif not company.boss_photo and photo:
            company.boss_photo = photo
    db.session.commit()


def seed_leaders():
    if setting("leaders_v3") == "1":
        return
    updates = {
        "ruslan": {
            "title": "Основатель, владелец и генеральный директор POOP EMPIRE GROUP",
            "role": "Контролирует холдинг и дочерние компании, инвестиции, финансы и стратегию. PANDA GROUP, промышленность, доставка и SHMILEON входят в его империю.",
            "bio": "Руслан Триллионеркин стоит на вершине схемы. Биография на сайте — фирменный текст, не справка из реестра. Капитал и капитализация помечены DEMO.",
        },
        "artur": {
            "title": "Руководитель какашечного бизнеса и промышленности России",
            "role": "Управляет какашечными предприятиями, качеством, новыми товарами, филиалами и POOP TECH. Помощник по энергетикам и доставке — Серёга.",
            "bio": "Артур Ахметвалеев ведёт промышленный контур: заводы, лаборатории и карту POOP INDUSTRY RUSSIA. Объекты на карте вымышленные.",
            "joke": "Говорит, что регион без точки на схеме — это ещё не регион, а черновик.",
        },
        "sergey": {
            "name": "Серёга",
            "title": "Помощник Артура: SERGO ENERGY и POOP DELIVERY",
            "role": "Производство энергетиков POOP ENERGY BY SERGO и самокатная доставка POOP DELIVERY по России: курьеры, хабы, логистика и скорость.",
            "bio": "Серёга — правая рука Артура. Портрет в руководстве и фотография «Серго-энергетик» — разные кадры: второй используется как образ бренда банок, а не как замена человека.",
            "joke": "Если банка и самокат спорят, кто главнее, Серёга ставит банку в корзину самоката и закрывает спор.",
        },
    }
    for slug, fields in updates.items():
        row = Partner.query.filter_by(slug=slug).first()
        if row:
            for key, value in fields.items():
                setattr(row, key, value)
    if not Partner.query.filter_by(slug="maksud").first():
        db.session.add(
            Partner(
                slug="maksud",
                name="Максуд ШмильЁн",
                title="Руководитель SHMILEON HONEY & MUSHROOMS",
                role="Самостоятельно ведёт дочернюю компанию по пчёлам и шампиньонам. Стратегически предприятие входит в POOP EMPIRE GROUP Руслана.",
                bio="Максуд руководит пасеками, мёдом, воском и грибными залами. Публичная страница не указывает домашний адрес: у компании только вымышленное место в легенде холдинга.",
                joke="Говорит, что улей и шампиньонница спорят только до первой планёрки.",
                photo="images/maksud.jpg",
                sort_order=4,
            )
        )
    set_setting("leaders_v3", "1")
    db.session.commit()


GOODS = [
    ("sergo-original", "SERGO ENERGY", "sergo-energy", 180, "Классическая банка POOP ENERGY BY SERGO.", "Вода, сахар, кофеин"),
    ("sergo-gold", "SERGO GOLD", "sergo-energy", 220, "Золотая серия с мёдом в легенде вкуса.", "Вода, сахар, ароматизатор мёда"),
    ("sergo-black", "SERGO BLACK", "sergo-energy", 220, "Тёмная банка для ночной смены самоката.", "Вода, сахар, кофеин"),
    ("sergo-trillion", "SERGO TRILLIONAIRE", "sergo-energy", 350, "Лимитированная серия кабинета.", "Вода, сахар, кофеин, золотой краситель"),
    ("panda-plush", "Плюшевая панда PANDA GROUP", "panda-shop", 2490, "Сувенир, не животное.", "Плюш"),
    ("panda-mug", "Кружка панда-кафе", "panda-shop", 890, "Для тематического зала.", "Керамика"),
    ("panda-sweet", "Панда-мармелад", "panda-shop", 420, "Сладость с бамбуковым цветом, не с бамбуком в составе как кормом.", "Сахар, мармелад"),
    ("two-toe-figure", "Фигурка двухпалой курицы", "two-toe", 990, "Тематическая игрушка птицефабрики.", "Полимер"),
    ("two-toe-box", "Набор TWO-TOE", "two-toe", 1890, "Коробка с шуткой селекции.", "Сборный набор"),
    ("shmileon-gold", "SHMILEON GOLD HONEY", "shmileon", 890, "Демонстрационный мёд дочерней компании.", "Мёд"),
    ("trillionaire-honey", "TRILLIONAIRE HONEY", "shmileon", 1490, "Банка с шильдом холдинга.", "Мёд"),
    ("poop-mushrooms", "POOP EMPIRE MUSHROOMS", "shmileon", 640, "Фасованные шампиньоны легенды.", "Шампиньоны"),
    ("royal-champignons", "ROYAL CHAMPIGNONS", "shmileon", 720, "Отборная линия Максуда.", "Шампиньоны"),
    ("honey-vip", "HONEY & MUSHROOM VIP BOX", "shmileon", 4590, "Мёд и грибы в одной коробке.", "Мёд, шампиньоны"),
]


def seed_goods():
    cats = {row.slug: row for row in Category.query.all()}
    extra = [
        ("sergo-energy", "SERGO ENERGY", "Банки Серёги", 22),
        ("panda-shop", "PANDA GROUP", "Сувениры и сладости панд", 23),
        ("two-toe", "Двухпалые курицы", "Тематические товары птицефабрики", 24),
        ("shmileon", "SHMILEON", "Мёд и шампиньоны", 25),
    ]
    for slug, name, desc, sort in extra:
        if slug not in cats:
            row = Category(slug=slug, name=name, description=desc, sort_order=sort)
            db.session.add(row)
            cats[slug] = row
    db.session.flush()
    for slug, name, cat, price, short, specs in GOODS:
        if Product.query.filter_by(slug=slug).first():
            continue
        rub = price * 100
        product = Product(
            category_id=cats[cat].id,
            slug=slug,
            sku="PE-" + slug[:18].upper(),
            name=name,
            short=short,
            description=short + "\n\nDEMO. Товар витрины холдинга. Оплата на сайте деньги не списывает.",
            composition=specs,
            price_kop=rub,
            cost_kop=int(rub * 0.4),
            stock=40,
            rating=4.8,
            review_count=1,
            is_active=True,
            purchasable=True,
            is_featured=slug in {"sergo-gold", "shmileon-gold", "panda-plush"},
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(ProductImage(product_id=product.id, path=write_product_mark(slug, name), sort_order=0))
        db.session.add(Review(product_id=product.id, author="Штаб холдинга", rating=5, text="Демонстрационный отзыв.", approved=True))
    db.session.commit()


def seed_regions():
    coords = {city: (lat, lng, region) for city, region, lat, lng in REGIONS}
    for plant in Factory.query.all():
        if plant.city in coords and plant.lat is None:
            lat, lng, _region = coords[plant.city]
            plant.lat, plant.lng = lat, lng
        if setting("staff_boost") != "1" and (plant.staff or 0) < 900:
            plant.staff = (plant.staff or 0) * 3 + 800
    have = {row.city for row in Factory.query.all()}
    for index, (city, region, lat, lng) in enumerate(REGIONS):
        if city in have:
            continue
        staff = 900 + (index * 37) % 2800
        db.session.add(
            Factory(
                slug="reg-" + str(index),
                name=f"Какашечный завод «{city}»",
                city=city,
                region=region,
                founded=2014 + (index % 12),
                boss="Артур Ахметвалеев",
                staff=staff,
                capacity=f"DEMO · смена {staff // 10} человек",
                products="Формы, сувениры и цеховая линейка региона",
                innovation="Региональный штамп Артура",
                revenue_rub=2_000_000_000 + staff * 1_000_000,
                status="DEMO · вымышленный объект",
                kind="Завод",
                pos_x=10 + (index * 7) % 80,
                pos_y=15 + (index * 5) % 70,
                lat=lat,
                lng=lng,
            )
        )
    set_setting("staff_boost", "1")
    db.session.commit()


def seed_chronicle():
    from empire.models import Airframe, AirRoute, ConflictZone, TimelineEvent

    toe = ListedCompany.query.filter_by(slug="two-toe").first()
    if toe:
        toe.tagline = "Старейшая компания и первая разработка империи"
        toe.summary = STORIES["two-toe"]
        toe.story = STORIES["two-toe"]
    for slug, photo in (("gorilla", "images/radmir.jpg"), ("poop-airlines", "images/timur.jpg")):
        row = ListedCompany.query.filter_by(slug=slug).first()
        if row:
            row.boss_photo = photo
    extras = (
        ("radmir", "Радмир Галлямов", "Руководитель GORILLA DEFENSE GROUP", "Ведёт вымышленную охрану заводов и складов империи. Гориллы на карте — игровые фигуры, не описание настоящей службы.", "images/radmir.jpg", 5),
        ("timur", "Тимур Сафин", "Руководитель POOP AIRLINES", "Собирает демонстрационный авиапарк и маршруты холдинга. Билеты авиакомпания не продаёт.", "images/timur.jpg", 6),
    )
    for slug, name, title, bio, photo, sort in extras:
        if not Partner.query.filter_by(slug=slug).first():
            db.session.add(Partner(slug=slug, name=name, title=title, role=bio, bio=bio, joke="", photo=photo, sort_order=sort))
    if Airframe.query.count() == 0:
        planes = [
            ("POOP-001", "POOP-001 TRILLIONAIRE", "Условный дальнемагистральный", "PO-001", 312, "DEMO · в ангаре", "Борт кабинета"),
            ("POOP-002", "POOP-002 GOLDEN EMPIRE", "Условный среднемагистральный", "PO-002", 186, "DEMO · на схеме", "Золотая ливрея"),
            ("POOP-003", "POOP-003 SERGO EXPRESS", "Условный региональный", "PO-003", 98, "DEMO · у телетрапа", "Банки в грузовом отсеке легенды"),
            ("POOP-004", "POOP-004 PANDA AIR", "Условный пассажирский", "PO-004", 210, "DEMO · подготовка", "Бамбуковый салон на рисунке"),
            ("POOP-005", "POOP-005 SHMILEON CARGO", "Условный грузовой", "PO-005", 0, "DEMO · загрузка мёда", "Грибы и банки, не живые пчёлы"),
        ]
        for code, name, model, tail, seats, status, note in planes:
            db.session.add(Airframe(code=code, name=name, model=model, tail=tail, seats=seats, status=status, note=note))
    if AirRoute.query.count() == 0:
        routes = [
            ("Уфа", "Москва", 14, "DEMO · по расписанию", "Утренний и вечерний слот легенды"),
            ("Казань", "Сочи", 7, "DEMO · сезонный", "К морю без настоящего бронирования"),
            ("Москва", "Владивосток", 4, "DEMO · дальний", "Через всю схему"),
            ("Уфа", "Казань", 21, "DEMO · частый", "Короткое плечо"),
            ("Новосибирск", "Санкт-Петербург", 5, "DEMO · грузовой", "Ящики SHMILEON на бумаге"),
        ]
        for origin, dest, week, status, note in routes:
            db.session.add(AirRoute(origin=origin, destination=dest, per_week=week, status=status, note=note))
    if ConflictZone.query.count() == 0:
        zones = [
            ("Татарстан", "Спор за золотую банку", "ROYAL TOILET HOLDING", "Под контролем POOP EMPIRE", 24, 82, "Гориллы схемы стоят у вымышленного склада. Это не сводка и не адрес.", "DEMO", 55.79, 49.12),
            ("Краснодарский край", "Ночная очередь самокатов", "MEGA DUNG COMPANY", "Спорная территория", 18, 54, "Конкурент хочет забрать сувенирный цех в легенде.", "DEMO", 45.04, 38.98),
            ("Свердловская область", "Цех, который спорит с отчётом", "FECAL FOOD GROUP", "Идёт вымышленный конфликт", 30, 47, "На схеме мигают две таблички. Настоящих действий нет.", "DEMO", 56.84, 60.60),
            ("Приморский край", "Тихоокеанский штамп", "ROYAL TOILET HOLDING", "Территория защищена GORILLA DEFENSE GROUP", 16, 76, "GORILLA SQUAD нарисована у ворот завода.", "DEMO", 43.12, 131.89),
            ("Новосибирская область", "Хаб, который уже посчитали", "MEGA DUNG COMPANY", "Конфликт завершён", 12, 88, "В хронике склад остался у империи.", "DEMO", 55.03, 82.92),
            ("Калининградская область", "Анклавный ящик", "FECAL FOOD GROUP", "Под контролем POOP EMPIRE", 9, 71, "Короткий сюжет про пломбу.", "DEMO", 54.71, 20.51),
            ("Республика Саха (Якутия)", "Морозный архив", "ROYAL TOILET HOLDING", "Территория защищена GORILLA DEFENSE GROUP", 8, 69, "Фигуры греются в легенде у лаборатории.", "DEMO", 62.03, 129.73),
            ("Крым", "Южный сувенир", "MEGA DUNG COMPANY", "Спорная территория", 14, 51, "Две корпорации делят витрину на бумаге.", "DEMO", 44.95, 34.10),
        ]
        for region, title, foe, status, troops, influence, story, label, lat, lng in zones:
            db.session.add(ConflictZone(region=region, title=title, foe=foe, status=status, troops=troops, influence=influence, story=story, updated_label=label, lat=lat, lng=lng))
    if TimelineEvent.query.count() == 0:
        events = [
            (2009, "Первые двухпалые курицы", "two-toe", "цех-легенда", "Художественный старт империи: идея TWO-TOE CHICKEN CORP. Это первая разработка хроники, не регистрация фирмы."),
            (2012, "Первые какашечные производства", "golden-poop", "Артур Ахметвалеев", "Рядом с птицефабрикой в легенде появляется цех форм."),
            (2014, "Промышленный контур Артура", "golden-poop", "Артур Ахметвалеев", "Заводы и лаборатории собираются в POOP INDUSTRIES."),
            (2016, "SERGO ENERGY", "sergo-energy", "Серёга", "Помощник Артура ставит на полку первую банку."),
            (2018, "POOP DELIVERY", "poop-delivery", "Серёга", "Самокаты начинают возить заказы по таймеру, не по GPS."),
            (2020, "PANDA GROUP", "panda-group", "холдинг Руслана", "Панды, кафе и сувениры становятся отдельным направлением."),
            (2022, "Пасеки и шампиньоны", "shmileon", "Максуд ШмильЁн", "SHMILEON входит в холдинг как самостоятельная дочерняя компания."),
            (2024, "GORILLA DEFENSE GROUP", "gorilla", "Радмир Галлямов", "В хронике появляются гориллы охраны предприятий. Это игровой сюжет."),
            (2025, "POOP AIRLINES", "poop-airlines", "Тимур Сафин", "Демонстрационный авиапарк и маршруты без продажи билетов."),
            (2026, "Биржа холдинга", "poop-empire", "Руслан Триллионеркин", "POOP EMPIRE GROUP выходит на свою виртуальную биржу первой по капитализации."),
        ]
        for index, (year, title, slug, boss, body) in enumerate(events):
            db.session.add(TimelineEvent(year=year, title=title, company_slug=slug, boss=boss, body=body, sort_order=index))
    db.session.commit()


def install():
    from empire.art import ensure_bank_art

    copy_photos()
    ensure_bank_art()
    seed_companies()
    seed_leaders()
    seed_goods()
    seed_regions()
    seed_chronicle()


def _guard_peg(rows):
    peg = next((row for row in rows if row.ticker == "PEG"), None)
    if peg is None:
        return
    peg_cap = peg.price_kop * peg.shares
    for row in rows:
        if row.id == peg.id or not row.shares:
            continue
        limit = int(peg_cap * 0.72 / row.shares)
        if row.price_kop > limit:
            row.price_kop = max(100, limit)


def _apply_headlines(rows):
    due = MarketNews.query.filter(
        MarketNews.applied.is_(False),
        MarketNews.impact_bps != 0,
        or_(MarketNews.publish_at.is_(None), MarketNews.publish_at <= utcnow()),
    ).all()
    if not due:
        return False
    by_id = {row.id: row for row in rows}
    for item in due:
        if item.company_id and item.company_id in by_id:
            targets = [by_id[item.company_id]]
        elif (item.region or "") == "russia":
            targets = [row for row in rows if row.in_holding]
        else:
            targets = list(rows)
        factor = 1 + (item.impact_bps or 0) / 10000
        for row in targets:
            row.price_kop = max(100, int(row.price_kop * factor))
        item.applied = True
    _guard_peg(rows)
    for row in rows:
        db.session.add(StockTick(company_id=row.id, price_kop=row.price_kop))
    db.session.commit()
    return True


def advance_market():
    now = int(time.time())
    last = int(setting("market_tick", "0") or 0)
    rows = ListedCompany.query.filter_by(listed=True, is_active=True).all()
    if not rows:
        return rows
    _apply_headlines(rows)
    if utcnow().date() != date.fromtimestamp(last) and last:
        for row in rows:
            row.day_open_kop = row.price_kop
            row.volume = 0
    if now - last < 15:
        return rows
    rng = random.Random(now // 15)
    headlines = [
        "DEMO · смена на бирже закрыла отчёт шуткой",
        "DEMO · дочерняя компания отчиталась перед холдингом",
        "DEMO · конкурент выпустил пресс-релиз без завода",
        "DEMO · самокатный хаб добавил смену",
        "DEMO · пасека Максуда сдала банку в легенду",
    ]
    for row in rows:
        drift = rng.uniform(-0.004, 0.009) if row.ticker == "PEG" else rng.uniform(-0.018, 0.016)
        row.price_kop = max(100, int(row.price_kop * (1 + drift)))
        row.volume = (row.volume or 0) + rng.randint(500, 8000)
    _guard_peg(rows)
    for row in rows:
        db.session.add(StockTick(company_id=row.id, price_kop=row.price_kop))
    if rng.random() < 0.35:
        picked = rng.choice(rows)
        db.session.add(MarketNews(company_id=picked.id, title=rng.choice(headlines), body="Событие сгенерировано сервером симулятора. Это не новость рынка."))
    set_setting("market_tick", str(now))
    db.session.commit()
    for row in rows:
        extra = StockTick.query.filter_by(company_id=row.id).order_by(StockTick.id.desc()).offset(80).all()
        for old in extra:
            db.session.delete(old)
    db.session.commit()
    return rows


def quote_payload(rows=None):
    rows = rows or ListedCompany.query.filter_by(listed=True, is_active=True).order_by(ListedCompany.sort_order).all()
    items = []
    for row in rows:
        change = 0 if not row.day_open_kop else (row.price_kop - row.day_open_kop) / row.day_open_kop * 100
        items.append(
            {
                "ticker": row.ticker,
                "slug": row.slug,
                "name": row.name,
                "price": row.price_kop,
                "change": round(change, 2),
                "cap": row.cap_rub,
                "volume": row.volume,
                "boss": row.boss,
            }
        )
    items.sort(key=lambda item: item["cap"], reverse=True)
    return items


def history(company, limit=30):
    ticks = StockTick.query.filter_by(company_id=company.id).order_by(StockTick.id.desc()).limit(limit).all()
    return [tick.price_kop for tick in reversed(ticks)]


def trade(user, ticker, side, qty):
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        return {"ok": False, "error": "Количество должно быть числом"}, 400
    if qty < 1 or qty > 10000:
        return {"ok": False, "error": "За одну сделку от 1 до 10000 акций"}, 400
    if side not in {"buy", "sell"}:
        return {"ok": False, "error": "Нужна покупка или продажа"}, 400
    advance_market()
    company = ListedCompany.query.filter_by(ticker=ticker.upper(), listed=True, is_active=True).first()
    if company is None:
        return {"ok": False, "error": "Такой бумаги нет"}, 404
    price = company.price_kop
    cost = price * qty
    fresh = db.session.get(User, user.id)
    if side == "buy":
        updated = db.session.execute(
            text("UPDATE users SET invest_kop = invest_kop - :cost WHERE id = :id AND invest_kop >= :cost"),
            {"cost": cost, "id": fresh.id},
        )
        if updated.rowcount != 1:
            db.session.rollback()
            return {"ok": False, "error": "Не хватает инвестиционного баланса. Это не банковский счёт."}, 400
        db.session.expire(fresh)
        holding = StockHolding.query.filter_by(user_id=fresh.id, company_id=company.id).first()
        if holding is None:
            holding = StockHolding(user_id=fresh.id, company_id=company.id, qty=0, avg_kop=0)
            db.session.add(holding)
        total = holding.avg_kop * holding.qty + cost
        holding.qty += qty
        holding.avg_kop = int(total / holding.qty)
    else:
        holding = StockHolding.query.filter_by(user_id=fresh.id, company_id=company.id).first()
        if holding is None or holding.qty < qty:
            return {"ok": False, "error": "Столько акций нет в портфеле"}, 400
        holding.qty -= qty
        fresh.invest_kop = (fresh.invest_kop or 0) + cost
    signed = -cost if side == "buy" else cost
    db.session.add(StockTrade(user_id=fresh.id, company_id=company.id, side=side, qty=qty, price_kop=price))
    db.session.add(InvestLedger(user_id=fresh.id, kind=side, amount_kop=signed, note=f"{side} {qty} {company.ticker}"))
    db.session.commit()
    db.session.refresh(fresh)
    return {
        "ok": True,
        "ticker": company.ticker,
        "side": side,
        "qty": qty,
        "price": price,
        "balance": fresh.invest_kop,
        "shares": holding.qty,
    }, 200
