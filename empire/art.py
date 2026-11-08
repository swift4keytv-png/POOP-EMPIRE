"""Рисует карты и упаковку. Фото людей и кота не генерируются — только вёрстка поверх копий."""

import os

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from empire.config import ROOT

STATIC = os.path.join(ROOT, "static")


def font(size, bold=False):
    names = ["arialbd.ttf", "segoeuib.ttf"] if bold else ["arial.ttf", "segoeui.ttf"]
    for name in names:
        path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(size, stops):
    image = Image.new("RGB", size)
    px = image.load()
    w, h = size
    for y in range(h):
        for x in range(w):
            t = min(1, max(0, x / (w - 1) * 0.72 + y / (h - 1) * 0.28))
            if t < 0.5:
                color = _mix(stops[0], stops[1], t / 0.5)
            else:
                color = _mix(stops[1], stops[2], (t - 0.5) / 0.5)
            px[x, y] = color
    return image


PALETTES = {
    "silver": ((150, 154, 162), (236, 238, 242), (98, 102, 112)),
    "gold": ((92, 62, 16), (244, 214, 120), (122, 78, 18)),
    "black": ((18, 18, 20), (58, 48, 28), (8, 8, 10)),
}

TITLES = {
    "silver": "POOP SILVER",
    "gold": "POOP GOLD",
    "black": "POOP BLACK",
}


def _base_card(design):
    w, h = 1012, 638
    image = gradient((w, h), PALETTES.get(design, PALETTES["gold"]))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, w - 18, h - 18), radius=36, outline=(255, 236, 190), width=3)
    draw.rounded_rectangle((70, 150, 190, 250), radius=16, fill=(212, 175, 90), outline=(90, 60, 20))
    for i, yy in enumerate(range(168, 236, 14)):
        draw.line((84, yy, 176, yy), fill=(120, 84, 24) if i % 2 == 0 else (255, 230, 160), width=3)
    draw.rectangle((0, 430, w, 490), fill=(20, 16, 12))
    ink = (20, 16, 10) if design != "black" else (244, 220, 160)
    draw.text((70, 56), "POOP EMPIRE GROUP", font=font(42, True), fill=ink)
    draw.text((70, 280), TITLES.get(design, "POOP GOLD"), font=font(54, True), fill=ink)
    draw.text((70, 520), "LOYALTY", font=font(28, True), fill=(255, 220, 140) if design == "black" else (90, 60, 16))
    return image


def ensure_sample_cards():
    folder = os.path.join(STATIC, "images", "cards")
    os.makedirs(folder, exist_ok=True)
    paths = {}
    for design in ("silver", "gold", "black"):
        dest = os.path.join(folder, f"{design}.png")
        if not os.path.exists(dest):
            card = _base_card(design)
            draw = ImageDraw.Draw(card)
            ink = (20, 16, 10) if design != "black" else (244, 220, 160)
            draw.text((70, 360), "••••  ••••  ••••  ••••", font=font(40, True), fill=ink)
            draw.text((560, 520), "ИМЯ ДЕРЖАТЕЛЯ", font=font(26), fill=ink)
            card.save(dest, "PNG")
        paths[design] = f"images/cards/{design}.png"
    return paths


def render_personal_card(holder, number, design, relative):
    folder = os.path.join(STATIC, os.path.dirname(relative))
    os.makedirs(folder, exist_ok=True)
    card = _base_card(design)
    draw = ImageDraw.Draw(card)
    ink = (20, 16, 10) if design != "black" else (244, 220, 160)
    draw.text((70, 360), number, font=font(46, True), fill=ink)
    draw.text((560, 520), holder[:26], font=font(32, True), fill=ink)
    card.save(os.path.join(STATIC, relative.replace("/", os.sep)), "PNG")
    return relative


def ensure_cereal_box(photo_path):
    dest = os.path.join(STATIC, "images", "cereal-box.png")
    back = os.path.join(STATIC, "images", "cereal-back.png")
    if os.path.exists(dest) and os.path.exists(back):
        return "images/cereal-box.png", "images/cereal-back.png"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    box = Image.new("RGB", (800, 1100), (22, 16, 10))
    draw = ImageDraw.Draw(box)
    draw.rectangle((30, 30, 770, 1070), outline=(226, 184, 74), width=8)
    draw.rectangle((50, 50, 750, 210), fill=(226, 184, 74))
    draw.text((80, 80), "ТИШКИНЫ ХЛОПЬЯ", font=font(54, True), fill=(30, 18, 8))
    draw.text((80, 150), "POOP EMPIRE GROUP", font=font(28, True), fill=(60, 36, 10))
    if os.path.exists(photo_path):
        cat = Image.open(photo_path).convert("RGB")
        cat = ImageEnhance.Contrast(cat).enhance(1.05)
        cat.thumbnail((680, 560))
        x = (800 - cat.width) // 2
        box.paste(cat, (x, 250))
    draw.rounded_rectangle((70, 860, 730, 1020), radius=20, fill=(226, 184, 74))
    draw.text((100, 890), "Тишка одобряет!", font=font(42, True), fill=(30, 18, 8))
    draw.text((100, 950), "Завтрак настоящего миллиардера", font=font(28), fill=(50, 30, 10))
    box.save(dest, "PNG")

    rear = Image.new("RGB", (800, 1100), (245, 236, 214))
    d2 = ImageDraw.Draw(rear)
    d2.rectangle((30, 30, 770, 1070), outline=(120, 84, 24), width=6)
    d2.text((70, 70), "СОСТАВ", font=font(48, True), fill=(40, 24, 8))
    lines = [
        "Овсяные хлопья",
        "Мёд",
        "Пищевое золото",
        "Тёплое молоко по желанию",
        "Одобрение кота Тишки",
        "",
        "Хруст, который заслужил даже кот.",
    ]
    y = 180
    for line in lines:
        d2.text((70, y), line, font=font(36), fill=(40, 24, 8))
        y += 70
    rear.save(back, "PNG")
    return "images/cereal-box.png", "images/cereal-back.png"


def ensure_bank_art():
    """Фирменные вывески банков. Фото людей не рисуются. Кота берём только из уже лежащего снимка."""

    os.makedirs(os.path.join(STATIC, "images"), exist_ok=True)
    tishka = os.path.join(STATIC, "images", "tishka-bank.jpg")
    kakashka = os.path.join(STATIC, "images", "kakashka-bank.jpg")
    cat_path = os.path.join(STATIC, "images", "tishka.jpg")
    if not os.path.exists(tishka):
        board = gradient((1400, 780), ((28, 18, 8), (92, 58, 16), (226, 184, 74)))
        draw = ImageDraw.Draw(board)
        draw.rounded_rectangle((48, 48, 1352, 732), radius=36, outline=(255, 236, 190), width=6)
        draw.text((90, 80), "TISHKABANK", font=font(72, True), fill=(255, 244, 214))
        draw.text((90, 170), "POOP EMPIRE GROUP  ·  DEMO", font=font(28, True), fill=(40, 24, 8))
        if os.path.exists(cat_path):
            cat = Image.open(cat_path).convert("RGB")
            cat.thumbnail((520, 460))
            board.paste(cat, (820, 160))
        draw.rounded_rectangle((90, 560, 760, 680), radius=18, fill=(20, 14, 8))
        draw.text((120, 590), "Бонусы карты  ·  не настоящий банк", font=font(32, True), fill=(244, 220, 160))
        board.save(tishka, "JPEG", quality=90)
    if not os.path.exists(kakashka):
        board = gradient((1400, 780), ((18, 12, 8), (70, 42, 12), (160, 110, 32)))
        draw = ImageDraw.Draw(board)
        draw.rounded_rectangle((48, 48, 1352, 732), radius=36, outline=(226, 184, 74), width=8)
        draw.ellipse((980, 140, 1280, 440), outline=(226, 184, 74), width=10)
        draw.text((1040, 250), "KB", font=font(72, True), fill=(255, 236, 190))
        draw.text((90, 160), "КАКАШКА БАНК", font=font(78, True), fill=(255, 236, 190))
        draw.text((90, 270), "Казначейство холдинга  ·  DEMO", font=font(32, True), fill=(255, 220, 150))
        draw.text((90, 560), "Карта и биржа в одном кабинете", font=font(36, True), fill=(255, 244, 214))
        draw.text((90, 630), "POOP COINS на рубли не меняются", font=font(28), fill=(244, 220, 160))
        board.save(kakashka, "JPEG", quality=90)
    return "images/tishka-bank.jpg", "images/kakashka-bank.jpg"


def write_product_mark(slug, title):
    folder = os.path.join(STATIC, "images", "products")
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, f"{slug}.svg")
    if os.path.exists(dest):
        return f"images/products/{slug}.svg"
    safe = (
        title.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800">
<rect width="800" height="800" fill="#14110c"/>
<rect x="48" y="48" width="704" height="704" rx="36" fill="none" stroke="#e0b44a" stroke-width="4"/>
<circle cx="400" cy="300" r="110" fill="#2a2114" stroke="#e0b44a" stroke-width="3"/>
<text x="400" y="318" text-anchor="middle" fill="#f3e2a8" font-size="54" font-family="Georgia">POOP</text>
<text x="400" y="560" text-anchor="middle" fill="#f6f1e6" font-size="36" font-family="Georgia">{safe}</text>
</svg>"""
    with open(dest, "w", encoding="utf-8") as handle:
        handle.write(svg)
    return f"images/products/{slug}.svg"
