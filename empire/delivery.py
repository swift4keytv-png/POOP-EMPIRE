"""Демонстрационная доставка по таймеру. Это не GPS."""

import random
from datetime import timedelta

from empire.extensions import db
from empire.models import Courier, DeliveryEvent, Notice, utcnow
from empire.services import setting

HQ = "Максима Горького, 70/1"
HQ_HOURS = "ежедневно 10:00–21:00"

PICKUP = [
    "Заказ оформлен",
    "Заказ собирается",
    "Заказ передан в пункт самовывоза",
    "Заказ готов к выдаче",
    "Покупатель получил уведомление",
    "Заказ выдан покупателю",
]

COURIER = [
    "Заказ оформлен",
    "Заказ собирается",
    "Заказ передан курьеру",
    "Курьер выехал",
    "Курьер прибыл",
    "Заказ доставлен",
]

PICKUP_NOTE = (
    "ВАШ ЗАКАЗ ПРИБЫЛ В ШТАБ POOP EMPIRE! 💩\n\n"
    "Ваш заказ готов к выдаче. Вы можете забрать его по адресу: Максима Горького, 70/1.\n\n"
    "Покажите номер заказа сотруднику пункта выдачи. Спасибо за покупки в POOP EMPIRE!"
)


def is_pickup(order):
    return "самовывоз" in (order.delivery_name or "").lower()


def stages_for(order):
    return PICKUP if is_pickup(order) else COURIER


def bounds():
    try:
        low = int(setting("delivery_step_min", "8"))
        high = int(setting("delivery_step_max", "20"))
    except ValueError:
        low, high = 8, 20
    low = max(0, low)
    high = max(low, high)
    return low, high


def assign_courier(order):
    if is_pickup(order):
        order.courier_id = None
        order.courier_name = ""
        return None
    free = (
        Courier.query.filter_by(is_active=True, status="свободен")
        .order_by(Courier.done_count)
        .first()
    )
    row = free or Courier.query.filter_by(is_active=True).order_by(Courier.done_count).first()
    if row is None:
        order.courier_name = "Сергей «Серёга»"
        return None
    order.courier_id = row.id
    order.courier_name = f"{row.name} «{row.nickname}»" if row.nickname else row.name
    if row.status == "свободен":
        row.status = "занят"
    return row


def open_delivery(order):
    now = utcnow()
    order.delivery_demo = True
    order.delivery_stage = 0
    assign_courier(order)
    order.stage_updated_at = now
    low, high = bounds()
    order.next_stage_at = now + timedelta(seconds=random.randint(low, high))
    db.session.add(DeliveryEvent(order_id=order.id, stage=0, title=stages_for(order)[0]))


def notify_ready(order):
    if not is_pickup(order) or order.pickup_notified or not order.user_id:
        return
    if (order.delivery_stage or 0) < 3:
        return
    items = ", ".join(f"{item.name} ×{item.qty}" for item in order.items) or "состав в заказе"
    db.session.add(
        Notice(
            user_id=order.user_id,
            title="Заказ готов к выдаче",
            body=PICKUP_NOTE + f"\n\nНомер: {order.number}. Состав: {items}.",
            order_number=order.number,
        )
    )
    order.pickup_notified = True


def advance_delivery(order):
    if order is None or not order.delivery_demo:
        return order
    stages = stages_for(order)
    last = len(stages) - 1
    now = utcnow()
    moved = False
    for _ in range(8):
        if order.delivery_stage >= last or not order.next_stage_at or order.next_stage_at > now:
            break
        order.delivery_stage += 1
        order.stage_updated_at = now
        db.session.add(
            DeliveryEvent(order_id=order.id, stage=order.delivery_stage, title=stages[order.delivery_stage])
        )
        if order.delivery_stage >= last:
            order.next_stage_at = None
            order.status = "issued" if is_pickup(order) else "delivered"
            if order.courier_id:
                courier = db.session.get(Courier, order.courier_id)
                if courier:
                    courier.done_count = (courier.done_count or 0) + 1
                    courier.status = "свободен"
        else:
            low, high = bounds()
            order.next_stage_at = now + timedelta(seconds=random.randint(low, high))
        moved = True
    if is_pickup(order):
        notify_ready(order)
    if moved or order.pickup_notified:
        db.session.commit()
    return order


def payload(order):
    stages = stages_for(order)
    stage = min(order.delivery_stage or 0, len(stages) - 1)
    pickup = is_pickup(order)
    courier = db.session.get(Courier, order.courier_id) if order.courier_id else None
    return {
        "ok": True,
        "demo": True,
        "mode": "pickup" if pickup else "courier",
        "number": order.number,
        "stage": stage,
        "title": stages[stage],
        "steps": stages,
        "done": stage >= len(stages) - 1,
        "hint": HQ_HOURS if pickup else "Демонстрационный таймер, не GPS.",
        "banner": "🎉 ВАШИ КАКАШКИ ПРИЕХАЛИ! ПРИЯТНОГО АППЕТИТА, ЖОПКА! 💩" if stage >= len(stages) - 1 else "",
        "courier": "" if pickup else (order.courier_name or ""),
        "courier_mark": "" if pickup or courier is None else courier.mark,
        "courier_photo": "" if pickup or courier is None or not courier.photo else courier.photo,
        "courier_status": "" if courier is None else courier.status,
        "eta": "" if pickup else (courier.eta if courier else "по таймеру"),
        "hq": HQ if pickup else "",
        "hours": HQ_HOURS if pickup else "",
        "note": "Самовывоз из штаба, Максима Горького, 70/1. Это не маршрут и не GPS." if pickup else "Демонстрация по таймеру. Это не маршрут и не GPS.",
        "events": [
            {"stage": event.stage, "title": event.title, "at": event.created_at.strftime("%H:%M:%S")}
            for event in sorted(order.events, key=lambda item: item.id)
        ],
    }
