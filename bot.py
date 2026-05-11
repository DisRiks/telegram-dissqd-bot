from __future__ import annotations

import asyncio
import ssl
import urllib.request
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiohttp.client_exceptions import ClientConnectorError
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, LabeledPrice, Message, PreCheckoutQuery, InlineQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
 

from catalog import BUILD_VARIANTS, LEAK_BUILD_VARIANTS, LEAK_MAP_VARIANTS, LEAK_PLUGIN_VARIANTS, LEAK_VARIANTS, OTHER_VARIANTS, WELCOME_TEXT
from config import load_settings
from keyboards import (
    admin_payment_menu,
    admin_support_close_confirm_menu,
    admin_support_requests_menu,
    admin_support_ticket_menu,
    build_variants_menu,
    download_link_menu,
    leak_build_variants_menu,
    leak_map_variants_menu,
    leak_plugin_variants_menu,
    leak_variants_menu,
    other_variants_menu,
    payment_check_menu,
    ready_to_pay_menu,
    support_cancel_menu,
    start_menu,
    support_request_menu,
    leak_resourcepack_variants_menu,
)


@dataclass
class PendingPurchase:
    item_key: str
    step: str
    funpay_nick: str | None = None


@dataclass
class PaymentRequest:
    request_id: int
    user_id: int
    username: str
    full_name: str
    item_key: str
    item_title: str
    funpay_nick: str
    funpay_url: str
    delivery_type: str
    status: str = "pending"


@dataclass
class RenameFlow:
    item_title: str
    notified_admin: bool = False


@dataclass
class SupportTicket:
    ticket_id: int
    user_id: int
    username: str
    full_name: str
    text: str
    purchases_text: str
    status: str = "new"
    admin_replies: list[str] = field(default_factory=list)


@dataclass
class AdminReplyState:
    ticket_id: int
    action: str
    chat_id: int
    message_id: int
    pending_text: str | None = None


dp = Dispatcher()
settings = load_settings()

# For "Не обновленный слив?" flow
LEAK_NOT_UPDATED_USERS: set[int] = set()

# Channels for subscription check
# Bot must be admin in these channels to check subscriptions
CHANNELS = [
    {"username": "@dissqd", "link": "https://t.me/dissqd"},
    {"username": "@dissqdsborki", "link": "https://t.me/dissqdsborki"},
    {"chat_id": "-1003577471589", "link": "https://t.me/+QN1VftNKP8VlNjMy", "private": True},
]

async def check_subscription(user_id: int, bot: Bot) -> tuple[list[str], list[str]]:
    """Return (list of channel links where user is not subscribed, list of errors)."""
    not_subscribed = []
    errors = []
    for ch in CHANNELS:
        try:
            # Determine chat_id for API call
            if ch.get("private"):
                chat_id = ch["chat_id"]  # use the numeric ID for private channel
            elif ch.get("username"):
                chat_id = ch["username"]
            else:
                chat_id = ch["link"]
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            # Check if member is subscribed
            if member.status in ("left", "kicked", "restricted"):
                not_subscribed.append(ch["link"])
        except Exception as e:
            # Bot likely not admin in channel
            link = ch.get("link", ch.get("username", ch.get("chat_id", "")))
            errors.append(f"{link}: бот не админ")
            not_subscribed.append(link)
    return not_subscribed, errors

async def send_subscription_prompt(target, bot, not_subscribed_links, errors=None):
    builder = InlineKeyboardBuilder()
    for link in not_subscribed_links:
        builder.button(text="📢 Подписаться", url=link)
    builder.button(text="✅ Проверить подписку", callback_data="check_subscription")
    builder.adjust(1)
    text = "❌ Вы не подписаны на все каналы. Подпишитесь и нажмите кнопку проверки:\n\n"
    for link in not_subscribed_links:
        text += f"• {link}\n"
    if errors:
        text += "\n⚠️ Ошибки проверки (убедитесь, что бот добавлен как админ в каналы):\n"
        for err in errors:
            text += f"• {err}\n"
    if hasattr(target, 'message'):  # it's a callback query
        await target.message.edit_text(text, reply_markup=builder.as_markup())
        await target.answer()
    else:
        await target.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot) -> None:
    user_id = callback.from_user.id
    not_subscribed, errors = await check_subscription(user_id, bot)
    if not_subscribed:
        await send_subscription_prompt(callback, bot, not_subscribed, errors)
    else:
        # Subscribed, register and show welcome
        REGISTERED_USERS.add(user_id)
        if callback.from_user.username:
            USERNAME_TO_ID[callback.from_user.username.lower()] = user_id
        SUPPORT_DRAFTS.pop(user_id, None)
        PENDING_PURCHASES.pop(user_id, None)
        RENAME_FLOWS.pop(user_id, None)
        ADMIN_REPLY_STATES.pop(user_id, None)
        await callback.message.delete()
        await callback.message.answer(
            WELCOME_TEXT,
            reply_markup=start_menu(is_admin=is_admin(user_id))
        )
        await callback.answer()

# Menu editor removed

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
FREE_DIR = Path(__file__).resolve().parent / "free"
USER_LOG_PATH = Path(__file__).resolve().parent / "user_activity.log"
REQUEST_COUNTER = count(1)
SUPPORT_TICKET_COUNTER = count(1)
SUPPORT_STARS_AMOUNT = 15

BUILD_ITEMS_BY_CALLBACK = {item.callback_data: item for item in BUILD_VARIANTS}
OTHER_ITEMS_BY_CALLBACK = {item.callback_data: item for item in OTHER_VARIANTS}
LEAK_ITEMS_BY_CALLBACK = {item.callback_data: item for item in LEAK_VARIANTS}
LEAK_BUILD_ITEMS_BY_CALLBACK = {item.callback_data: item for item in LEAK_BUILD_VARIANTS}
LEAK_MAP_ITEMS_BY_CALLBACK = {item.callback_data: item for item in LEAK_MAP_VARIANTS}
LEAK_PLUGIN_ITEMS_BY_CALLBACK = {item.callback_data: item for item in LEAK_PLUGIN_VARIANTS}
ALL_ITEMS_BY_CALLBACK = {**BUILD_ITEMS_BY_CALLBACK, **OTHER_ITEMS_BY_CALLBACK}


def back_button(callback_data: str) -> InlineKeyboardBuilder:
    """Helper to create a back button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data=callback_data)
    return builder


# Promo system data
@dataclass
class PromoCode:
    code: str
    discount_percent: int = 0
    discount_flat: int | None = None
    max_uses: int = 0
    activations: int = 0
    active: bool = True
    created_by: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    description: str | None = None
    # Pending activations from users awaiting admin approval
    pending_activations: set[int] = field(default_factory=set)
@dataclass
class PendingPromoDraft:
    code: str | None = None
    discount_percent: int | None = None
    max_uses: int | None = None
    description: str | None = None
    created_by: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

# Global promo storage
PROMO_CODES: dict[str, PromoCode] = {}
REGISTERED_USERS: set[int] = set()
PROMO_DRAFTS: dict[int, PendingPromoDraft] = {}
USER_PROMOS: dict[int, str] = {}
USER_PROMO_ACTIVATED_AT: dict[int, datetime] = {}
USERNAME_TO_ID: dict[str, int] = {}  # mapping username (without @) to user_id

SUPPORT_DRAFTS: dict[int, list[str]] = {}
PENDING_PURCHASES: dict[int, PendingPurchase] = {}
PAYMENT_REQUESTS: dict[int, PaymentRequest] = {}
RENAME_FLOWS: dict[int, RenameFlow] = {}
PURCHASE_HISTORY: dict[int, list[str]] = {}
SUPPORT_TICKETS: dict[int, SupportTicket] = {}
ADMIN_REPLY_STATES: dict[int, AdminReplyState] = {}


def is_admin(user_id: int) -> bool:
    return user_id == settings.support_admin_id


def log_user_activity(message: Message | CallbackQuery, action: str) -> None:
    user = message.from_user
    if not user:
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    username = f"@{user.username}" if user.username else "-"
    full_name = user.full_name.replace("\n", " ").strip()
    line = (
        f"{timestamp} | action={action} | user_id={user.id} | "
        f"username={username} | full_name={full_name}\n"
    )
    USER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with USER_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(line)


def get_paid_file_path(item_key: str) -> Path | None:
    mapping = {
        "build_reallyworld_grief": settings.paid_grief_build_path,
        "build_reallyworld_full": settings.paid_full_build_path,
        "other_basic_plugins": settings.paid_plugins_path,
    }
    return mapping.get(item_key)


def remember_purchase(user_id: int, item_title: str) -> None:
    history = PURCHASE_HISTORY.setdefault(user_id, [])
    if item_title not in history:
        history.append(item_title)


def support_status_icon(status: str) -> str:
    return {
        "new": "🟢",
        "review": "🟠",
        "closed": "🔴",
    }.get(status, "🟢")


def support_ticket_label(ticket: SupportTicket) -> str:
    return f"{support_status_icon(ticket.status)} #{ticket.ticket_id} {ticket.full_name}"


def support_ticket_text(ticket: SupportTicket) -> str:
    replies = ""
    if ticket.admin_replies:
        replies = "\n\n✉️ Ответы:\n" + "\n\n".join(ticket.admin_replies)
    return (
        f"{support_status_icon(ticket.status)} Обращение #{ticket.ticket_id}\n\n"
        f"👤 Пользователь: {ticket.full_name}\n"
        f"🔗 Username: {ticket.username}\n"
        f"🆔 User ID: {ticket.user_id}\n"
        f"🧾 Покупки: {ticket.purchases_text}\n\n"
        f"📝 Текст обращения:\n{ticket.text}\n"
        f"{get_user_promo_status(ticket.user_id)}\n"
        f"{replies}"
    )


def support_ticket_list() -> list[tuple[int, str]]:
    order = {"new": 0, "review": 1, "closed": 2}
    tickets = sorted(SUPPORT_TICKETS.values(), key=lambda item: (order.get(item.status, 9), item.ticket_id))
    return [(ticket.ticket_id, support_ticket_label(ticket)) for ticket in tickets]

def is_ticket_closed(ticket_id: int) -> bool:
    t = SUPPORT_TICKETS.get(ticket_id)
    return bool(t and t.status == "closed")


def user_promo_status_text(user_id: int) -> str:
    code = USER_PROMOS.get(user_id)
    if not code:
        return "Промокод: отсутствует"
    # Проверяем, не прошло ли 3 дня с активации
    activated_at = USER_PROMO_ACTIVATED_AT.get(user_id)
    if activated_at and (datetime.utcnow() - activated_at).days >= 3:
        # Удаляем промокод из техподдержки по истечении 3 дней
        USER_PROMOS.pop(user_id, None)
        USER_PROMO_ACTIVATED_AT.pop(user_id, None)
        return "Промокод: отсутствует"
    promo = PROMO_CODES.get(code)
    if not promo:
        return f"Промокод: {code} (неактивен)"
    if promo.discount_flat is not None:
        prize = f"{promo.discount_flat} ₽"
    else:
        prize = f"{promo.discount_percent}%"
    return f"Промокод: {code}\nПриз: {prize}"

def get_user_promo_status(user_id: int) -> str:
    code = USER_PROMOS.get(user_id)
    if not code:
        return "У вас нет активного промокода."
    activated_at = USER_PROMO_ACTIVATED_AT.get(user_id)
    if not activated_at:
        return f"Промокод {code} активирован, но время не записано."
    now = datetime.utcnow()
    elapsed_seconds = (now - activated_at).total_seconds()
    seconds_in_day = 86400
    days_left = 3 - elapsed_seconds / seconds_in_day
    if days_left <= 0:
        USER_PROMOS.pop(user_id, None)
        USER_PROMO_ACTIVATED_AT.pop(user_id, None)
        return "Срок действия промокода истёк."
    promo = PROMO_CODES.get(code)
    if not promo:
        return f"Промокод {code} не найден."
    prize = f"{promo.discount_flat} ₽" if promo.discount_flat is not None else f"{promo.discount_percent}%"
    days_left_int = max(1, int(days_left))
    return f"Промокод: {code}\nПриз: {prize}\nОсталось дней: {days_left_int}"

async def show_support_ticket(callback: CallbackQuery, ticket_id: int) -> None:
    ticket = SUPPORT_TICKETS.get(ticket_id)
    if not ticket:
        await callback.message.edit_text("Обращение не найдено.")
        await callback.answer()
        return

    from keyboards import admin_support_ticket_menu_closed
    if ticket.status == "closed":
        markup = admin_support_ticket_menu_closed(ticket.ticket_id)
    else:
        markup = admin_support_ticket_menu(ticket.ticket_id)
    await callback.message.edit_text(
        support_ticket_text(ticket),
        reply_markup=markup,
    )
    await callback.answer()


@dp.message(CommandStart())
async def start_handler(message: Message, bot: Bot) -> None:
    log_user_activity(message, "start")
    user_id = message.from_user.id
    # Check subscription
    not_subscribed, errors = await check_subscription(user_id, bot)
    if not_subscribed:
        await send_subscription_prompt(message, bot, not_subscribed, errors)
        return
    # If subscribed, register user and show welcome
    REGISTERED_USERS.add(user_id)
    if message.from_user.username:
        USERNAME_TO_ID[message.from_user.username.lower()] = user_id
    SUPPORT_DRAFTS.pop(user_id, None)
    PENDING_PURCHASES.pop(user_id, None)
    RENAME_FLOWS.pop(user_id, None)
    ADMIN_REPLY_STATES.pop(user_id, None)
    # Send logo first
    logo_path = ASSETS_DIR / "logo.jpg"
    if logo_path.exists():
        await message.answer_photo(photo=FSInputFile(logo_path))
    await message.answer(WELCOME_TEXT, reply_markup=start_menu(is_admin=is_admin(user_id)))

    # Initialize promo draft for user (if автоматическое активации не требуется,
    # промокод активируется через отдельную команду/пользовательский ввод)


@dp.message(Command(commands=["promo_create"]))
async def promo_create_cmd(message: Message) -> None:
    # Simple admin-only promo creation: /promo_create CODE DISCOUNT MAX_USES [DESCRIPTION]
    if not is_admin(message.from_user.id):
        await message.answer("Недоступно.")
        return

    parts = message.text.split(None, 4)
    if len(parts) < 4:
        await message.answer("Использование: /promo_create CODE DISCOUNT(MAX%) MAX_USES [DESCRIPTION]")
        return
    code = parts[1]
    try:
        discount = int(parts[2])
        max_uses = int(parts[3])
    except ValueError:
        await message.answer("Дисконт и max_uses должны быть числами.")
        return
    description = parts[4] if len(parts) > 4 else None
    promo = PromoCode(code=code, discount_percent=discount, max_uses=max_uses, created_by=message.from_user.id, description=description)
    PROMO_CODES[code] = promo
    await announce_promo_creation(promo, code, message.bot)


@dp.message(Command(commands=["promo_broadcast"]))
async def promo_broadcast_cmd(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Недоступно.")
        return
    parts = message.text.split(None, 2)
    if len(parts) < 2:
        await message.answer("Использование: /promo_broadcast CODE")
        return
    code = parts[1]
    promo = PROMO_CODES.get(code)
    if not promo:
        await message.answer("Промокод не найден.")
        return
    await broadcast_promo_code(promo, message.bot)
    await message.answer("Промокод распространён всем пользователям.")


@dp.message(Command(commands=["promo_create_flat"]))
async def promo_create_flat_cmd(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Недоступно.")
        return
    parts = message.text.split(None, 4)
    if len(parts) < 4:
        await message.answer("Использование: /promo_create_flat CODE AMOUNT MAX_USES [DESCRIPTION]")
        return
    code = parts[1]
    try:
        amount = int(parts[2])
        max_uses = int(parts[3])
    except ValueError:
        await message.answer("Данные должны быть числами: amount и max_uses")
        return
    description = parts[4] if len(parts) > 4 else None
    promo = PromoCode(code=code, discount_percent=0, discount_flat=amount, max_uses=max_uses, created_by=message.from_user.id, description=description)
    PROMO_CODES[code] = promo
    # Удалено отдельное уведомление о создании; используем единое объявление ниже
    await announce_promo_creation(promo, code, message.bot)


@dp.callback_query(F.data == "promo_activate")
async def promo_activate_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "activate_promo_prompt")
    PROMO_DRAFTS[callback.from_user.id] = PendingPromoDraft()
    await callback.message.answer("Введите промокод для активации:")
    await callback.answer()


@dp.message(Command(commands=["promo_approve"]))
async def promo_approve_handler(message: Message, bot: Bot) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Недоступно.")
        return
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.answer("Использование: /promo_approve CODE")
        return
    code = parts[1].strip()
    promo = PROMO_CODES.get(code)
    if not promo:
        await message.answer("Промокод не найден.")
        return
    if not promo.pending_activations:
        await message.answer("Нет запросов на активацию для этого промокода.")
        return
    if promo.pending_activations:
        user_id = promo.pending_activations.pop()
    else:
        user_id = None
    PROMO_CODES[code] = promo
    # Привязываем промокод к пользователю (один код на пользователя в простейшей реализации)
    if user_id is not None:
        promo.activations += 1
        USER_PROMOS[user_id] = code
        USER_PROMO_ACTIVATED_AT[user_id] = datetime.utcnow()
        try:
            await bot.send_message(user_id, f"Промокод {code} активирован. На активацию промокода дается 3 дня. Осталось 3 дня. Чтобы получить приз напишите в Тех.Поддержку")
        except Exception:
            pass

async def broadcast_promo_code(promo: PromoCode, bot: Bot) -> None:
    if not REGISTERED_USERS:
        return
    prize = f"{promo.discount_flat} ₽" if promo.discount_flat is not None else f"{promo.discount_percent}%"
    text = (
        f"Новый промокод - ({promo.code})\n"
        f"Активаций - ({promo.max_uses})\n"
        f"Приз - ({prize})"
    )
    for uid in list(REGISTERED_USERS):
        try:
            await bot.send_message(uid, text)
        except Exception:
            pass


async def announce_promo_creation(promo: PromoCode, code: str, bot: Bot) -> None:
    # Announcement formatted per request:
    prize = f"{promo.discount_flat} ₽" if promo.discount_flat is not None else f"{promo.discount_percent}%"
    description_text = promo.description if promo.description else "нет описания"
    text = (
        f"Новый промокод - ({code})\n"
        f"Активаций - ({promo.max_uses})\n"
        f"Приз - ({prize})\n"
        f"Описание - ({description_text})"
    )
    if not REGISTERED_USERS:
        return
    for uid in list(REGISTERED_USERS):
        try:
            await bot.send_message(uid, text)
        except Exception:
            pass

async def announce_promo_activation(promo: PromoCode, code: str, user_id: int, bot: Bot) -> None:
    # Функция не используется, оставлена для совместимости
    pass


def promo_help_text() -> str:
    return (
        "Команды (администратору):\n"
        "/promo_create CODE DISCOUNT MAX_USES [DESCRIPTION] - создать промокод (процент)\n"
        "/promo_create_flat CODE AMOUNT MAX_USES [DESCRIPTION] - создать промокод (фиксированная сумма ₽)\n"
        "/promo_broadcast CODE - распространить промокод всем пользователям\n"
        "/promo_approve CODE - подтвердить активацию промокода для пользователя\n"
        "/promo_activate - начать активацию промокода через бота\n"
        "/check_status_promos @username - проверить статус промокода пользователя\n"
        "/user_promo_yes CODE @username - подтвердить выдачу приза и деактивировать промокод\n"
        "/promo_help - показать эту справку\n"
    )

@dp.message(Command(commands=["promo_help"]))
async def promo_help_handler(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Недоступно.")
        return
    await message.answer(promo_help_text())

@dp.message(Command(commands=["check_status_promos"]))
async def check_status_promos_handler(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Недоступно.")
        return
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        await message.answer("Использование: /check_status_promos @username")
        return
    username = parts[1].lstrip('@').lower()
    user_id = USERNAME_TO_ID.get(username)
    if not user_id:
        await message.answer(f"Пользователь @{username} не найден.")
        return
    status = get_user_promo_status(user_id)
    await message.answer(f"Статус промокода для @{username}:\n{status}")

@dp.message(Command(commands=["user_promo_yes"]))
async def user_promo_yes_handler(message: Message, bot: Bot) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Недоступно.")
        return
    parts = message.text.split(None, 2)
    if len(parts) < 3:
        await message.answer("Использование: /user_promo_yes CODE @username")
        return
    code = parts[1]
    username = parts[2].lstrip('@').lower()
    user_id = USERNAME_TO_ID.get(username)
    if not user_id:
        await message.answer(f"Пользователь @{username} не найден.")
        return
    promo = PROMO_CODES.get(code)
    if not promo:
        await message.answer(f"Промокод {code} не найден.")
        return
    # Проверяем, активен ли у пользователя этот промокод
    current_code = USER_PROMOS.get(user_id)
    if current_code != code:
        await message.answer(f"У пользователя @{username} нет активного промокода {code}. Текущий: {current_code or 'нет'}.")
        return
    # Выдаём приз и удаляем промокод
    USER_PROMOS.pop(user_id, None)
    USER_PROMO_ACTIVATED_AT.pop(user_id, None)
    try:
        await bot.send_message(user_id, f"Поздравляем! Вы получили приз по промокоду {code}.")
    except Exception:
        pass
    await message.answer(f"Приз по промокоду {code} выдан пользователю @{username}. Промокод деактивирован.")

@dp.callback_query(F.data == "buy_build")
async def buy_build_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_buy_build")
    await callback.message.answer(
        "Выберите сборку для покупки:",
        reply_markup=build_variants_menu(),
    )
    await callback.answer()


async def send_paid_item_card(callback: CallbackQuery, item_key: str) -> None:
    # Безопасно получаем товар по ключу, чтобы избежать KeyError,
    # если вдруг передан неизвестный callback_data.
    item = ALL_ITEMS_BY_CALLBACK.get(item_key)
    if item is None:
        await callback.message.edit_text("Не найден товар для выбранной опции.")
        await callback.answer()
        return
    image_path = ASSETS_DIR / item.image_name if item.image_name else None

    if image_path and image_path.exists():
        await callback.message.answer_photo(
            photo=FSInputFile(image_path),
            caption=item.caption,
            reply_markup=ready_to_pay_menu(item.callback_data, item.funpay_url),
            parse_mode="HTML",
            protect_content=True,
        )
    else:
        await callback.message.answer(
            item.caption,
            reply_markup=ready_to_pay_menu(item.callback_data, item.funpay_url),
            parse_mode="HTML",
        )
    await callback.answer()


@dp.callback_query(F.data == "build_reallyworld_grief")
async def build_reallyworld_grief_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "view_build_reallyworld_grief")
    await send_paid_item_card(callback, "build_reallyworld_grief")


@dp.callback_query(F.data == "build_reallyworld_full")
async def build_reallyworld_full_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "view_build_reallyworld_full")
    await send_paid_item_card(callback, "build_reallyworld_full")


@dp.callback_query(F.data == "other")
async def other_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_other")
    await callback.message.answer(
        "Выберите что хотите купить:",
        reply_markup=other_variants_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data == "other_basic_plugins")
async def other_basic_plugins_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "view_other_basic_plugins")
    await send_paid_item_card(callback, "other_basic_plugins")


@dp.callback_query(F.data == "other_rename_our_build")
async def other_rename_our_build_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "view_other_rename_our_build")
    await send_paid_item_card(callback, "other_rename_our_build")


@dp.callback_query(F.data == "other_rename_not_our_build")
async def other_rename_not_our_build_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "view_other_rename_not_our_build")
    await send_paid_item_card(callback, "other_rename_not_our_build")


@dp.callback_query(F.data == "other_velocity_bundle")
async def other_velocity_bundle_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "view_other_velocity_bundle")
    await send_paid_item_card(callback, "other_velocity_bundle")


@dp.callback_query(F.data == "other_fix_build")
async def other_fix_build_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "view_other_fix_build")
    await send_paid_item_card(callback, "other_fix_build")


@dp.callback_query(F.data == "help_find_product")
async def help_find_product_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_help_find_product")
    user_id = callback.from_user.id
    # Инициализируем очередь вопросов к поддержке, чтобы пользователь мог писать обращения
    if user_id not in SUPPORT_DRAFTS:
        SUPPORT_DRAFTS[user_id] = []
    await callback.message.answer(
        "Мы не знаем, какой товар именно нужен.\nНапишите нам — мы ответим, сможем ли выполнить заказ.",
        reply_markup=support_request_menu(),
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
    except Exception:
        pass
    await callback.message.answer(
        WELCOME_TEXT,
        reply_markup=start_menu(is_admin=is_admin(callback.from_user.id))
    )

@dp.callback_query(F.data == "back_to_build_variants")
async def back_to_build_variants_handler(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Выберите сборку для покупки:",
        reply_markup=build_variants_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_leak_maps")
async def back_to_leak_maps_handler(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Выберите карту, спавн или мир:",
        reply_markup=leak_map_variants_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_leak_builds")
async def back_to_leak_builds_handler(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Выберите сборку для скачивания:",
        reply_markup=leak_build_variants_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_leak_plugins")
async def back_to_leak_plugins_handler(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Выберите плагин для скачивания:",
        reply_markup=leak_plugin_variants_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_leak_resourcepacks")
async def back_to_leak_resourcepacks_handler(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Выберите РесурсПак для скачивания:",
        reply_markup=leak_resourcepack_variants_menu()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("purchase:"))
async def purchase_start_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "start_purchase")
    item_key = callback.data.split(":", 1)[1]
    item = ALL_ITEMS_BY_CALLBACK[item_key]
    PENDING_PURCHASES[callback.from_user.id] = PendingPurchase(
        item_key=item_key,
        step="await_funpay_nick",
    )
    await callback.message.answer(
        f"Вы выбрали: {item.title}\n\n"
        "Теперь отправьте ваш ник на FunPay одним сообщением.\n\n"
        "Внимание: при неправильном указании ника деньги не возвращаются."
    )
    await callback.answer()


@dp.callback_query(F.data == "purchase_paid_yes")
async def purchase_paid_yes_handler(callback: CallbackQuery, bot: Bot) -> None:
    log_user_activity(callback, "purchase_paid_yes")
    pending = PENDING_PURCHASES.get(callback.from_user.id)
    if not pending or pending.step != "await_payment_confirmation" or not pending.funpay_nick:
        await callback.message.answer("Сначала укажите ник на FunPay.")
        await callback.answer()
        return

    item = ALL_ITEMS_BY_CALLBACK[pending.item_key]
    request_id = next(REQUEST_COUNTER)
    username = f"@{callback.from_user.username}" if callback.from_user.username else "без username"
    request = PaymentRequest(
        request_id=request_id,
        user_id=callback.from_user.id,
        username=username,
        full_name=callback.from_user.full_name,
        item_key=item.callback_data,
        item_title=item.title,
        funpay_nick=pending.funpay_nick,
        funpay_url=item.funpay_url,
        delivery_type=item.delivery_type,
    )
    PAYMENT_REQUESTS[request_id] = request
    PENDING_PURCHASES.pop(callback.from_user.id, None)

    admin_text = (
        f"💳 Новый запрос на проверку оплаты\n\n"
        f"📦 Товар: {request.item_title}\n"
        f"🎮 Ник на FunPay: {request.funpay_nick}\n"
        f"👤 Пользователь: {request.full_name}\n"
        f"🔗 Username: {request.username}\n"
        f"🆔 User ID: {request.user_id}\n"
        f"🛒 Ссылка FunPay: {request.funpay_url}"
    )
    await bot.send_message(
        settings.support_admin_id,
        admin_text,
        reply_markup=admin_payment_menu(request_id),
    )
    await callback.message.answer("Запрос на проверку оплаты отправлен. Ожидайте ответа.")
    await callback.answer()


@dp.callback_query(F.data == "purchase_paid_no")
async def purchase_paid_no_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "purchase_cancelled")
    pending = PENDING_PURCHASES.get(callback.from_user.id)
    if not pending or pending.step != "await_payment_confirmation":
        await callback.message.answer("Сначала укажите ник на FunPay.")
        await callback.answer()
        return

    await callback.message.answer(
        "Покупка отменена. Если захотите купить позже, снова нажмите `Готов оплатить`.",
        parse_mode="Markdown",
    )
    PENDING_PURCHASES.pop(callback.from_user.id, None)
    await callback.answer()


async def deliver_paid_file(bot: Bot, request: PaymentRequest) -> None:
    if request.item_key == "build_reallyworld_grief" and settings.paid_grief_build_url:
        password_text = (
            f"\n\nПароль: <code>{settings.paid_grief_build_password}</code>"
            if settings.paid_grief_build_password
            else ""
        )
        await bot.send_message(
            request.user_id,
            (
                f"Оплата найдена. Ваш товар: {request.item_title}.{password_text}\n\n"
                "Если ссылка не открывается или файл нужен на другом файлообменнике, "
                "напишите в Тех.Поддержку."
            ),
            reply_markup=download_link_menu(settings.paid_grief_build_url),
            parse_mode="HTML",
        )
        return

    paid_file_path = get_paid_file_path(request.item_key)
    if paid_file_path and paid_file_path.exists():
        await bot.send_document(
            chat_id=request.user_id,
            document=FSInputFile(paid_file_path),
            caption=f"Оплата найдена. Ваш товар: {request.item_title}",
            protect_content=True,
        )
        return

    await bot.send_message(
        request.user_id,
        "Оплата найдена. Товар будет отправлен вручную, файл пока не добавлен в бота.",
    )
    await bot.send_message(
        settings.support_admin_id,
        f"⚠️ Файл для товара `{request.item_title}` не найден в проекте.",
        parse_mode="Markdown",
    )


@dp.callback_query(F.data.startswith("admin_ok:"))
async def admin_approve_payment_handler(callback: CallbackQuery, bot: Bot) -> None:
    log_user_activity(callback, "admin_approve_payment")
    request_id = int(callback.data.split(":", 1)[1])
    request = PAYMENT_REQUESTS.get(request_id)

    if not request:
        await callback.answer("Запрос не найден.", show_alert=True)
        return

    request.status = "approved"
    remember_purchase(request.user_id, request.item_title)
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ Оплата подтверждена.",
    )

    if request.delivery_type == "file":
        await deliver_paid_file(bot, request)
    else:
        RENAME_FLOWS[request.user_id] = RenameFlow(item_title=request.item_title)
        await bot.send_message(
            request.user_id,
            "Оплата найдена. Теперь отправьте сборку, название вашего сервера, соцсети и сайт.",
        )

    await callback.answer("Оплата подтверждена.")


@dp.callback_query(F.data.startswith("admin_no:"))
async def admin_reject_payment_handler(callback: CallbackQuery, bot: Bot) -> None:
    log_user_activity(callback, "admin_reject_payment")
    request_id = int(callback.data.split(":", 1)[1])
    request = PAYMENT_REQUESTS.get(request_id)

    if not request:
        await callback.answer("Запрос не найден.", show_alert=True)
        return

    request.status = "rejected"
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ Оплата отклонена.",
    )
    await bot.send_message(request.user_id, "Оплата не найдена.")
    await callback.answer("Оплата отклонена.")


@dp.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_support")
    SUPPORT_DRAFTS[callback.from_user.id] = []
    await callback.message.answer(
        "Напишите ваш вопрос. Можно отправить несколько сообщений, а потом нажать кнопку ниже.",
        reply_markup=support_cancel_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data == "support_send")
async def support_send_handler(callback: CallbackQuery, bot: Bot) -> None:
    log_user_activity(callback, "send_support_request")
    user_id = callback.from_user.id
    draft = SUPPORT_DRAFTS.get(user_id, [])

    if not draft:
        await callback.message.answer(
            "Сначала напишите обращение, потом нажмите кнопку отправки.",
            reply_markup=support_request_menu(),
        )
        await callback.answer()
        return

    purchases = PURCHASE_HISTORY.get(user_id, [])
    ticket = SupportTicket(
        ticket_id=next(SUPPORT_TICKET_COUNTER),
        user_id=user_id,
        username=f"@{callback.from_user.username}" if callback.from_user.username else "без username",
        full_name=callback.from_user.full_name,
        text="\n\n".join(draft),
        purchases_text=", ".join(purchases) if purchases else "нет подтвержденных покупок",
    )
    SUPPORT_TICKETS[ticket.ticket_id] = ticket
    SUPPORT_DRAFTS.pop(user_id, None)

    await bot.send_message(
        settings.support_admin_id,
        f"🟢 Новое обращение #{ticket.ticket_id}\n\n"
        f"👤 Пользователь: {ticket.full_name}\n"
        f"🧾 Покупки: {ticket.purchases_text}\n\n"
        "Откройте раздел Активные запросы, чтобы ответить.",
    )
    await callback.message.answer("Ваше обращение отправлено. Ожидайте ответа от поддержки.")
    await callback.answer()


@dp.callback_query(F.data == "support_cancel")
async def support_cancel_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "cancel_support_request")
    SUPPORT_DRAFTS.pop(callback.from_user.id, None)
    await callback.message.answer("Обращение отменено.")
    await callback.answer()


@dp.callback_query(F.data == "admin_support_requests")
async def admin_support_requests_handler(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно.", show_alert=True)
        return

    log_user_activity(callback, "open_admin_support_requests")
    tickets = support_ticket_list()
    if not tickets:
        await callback.message.edit_text("Активных запросов пока нет.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "Список обращений:",
        reply_markup=admin_support_requests_menu(tickets),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_ticket:"))
async def admin_support_ticket_handler(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно.", show_alert=True)
        return

    ticket_id = int(callback.data.split(":", 1)[1])
    await show_support_ticket(callback, ticket_id)


@dp.callback_query(F.data.startswith("admin_ticket_review:"))
async def admin_support_ticket_review_handler(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно.", show_alert=True)
        return

    ticket_id = int(callback.data.split(":", 1)[1])
    ticket = SUPPORT_TICKETS.get(ticket_id)
    if not ticket:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return

    # Запрещаем рассмотрение закрытых обращений
    if is_ticket_closed(ticket_id):
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return

    log_user_activity(callback, f"admin_ticket_review:{ticket_id}")
    ticket.status = "review"
    await bot.send_message(ticket.user_id, "Ваше обращение на рассмотрении.")
    await callback.message.edit_text(
        support_ticket_text(ticket),
        reply_markup=admin_support_ticket_menu(ticket.ticket_id),
    )
    await callback.answer("Статус изменен на: в рассмотрении.")


@dp.callback_query(F.data.startswith("admin_ticket_close:"))
async def admin_support_ticket_close_handler(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно.", show_alert=True)
        return

    ticket_id = int(callback.data.split(":", 1)[1])
    if ticket_id not in SUPPORT_TICKETS:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return

    # Если обращение уже закрыто, не разрешать повторно закрывать или отвечать
    ticket = SUPPORT_TICKETS.get(ticket_id)
    if is_ticket_closed(ticket_id):
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return

    log_user_activity(callback, f"admin_ticket_close:{ticket_id}")

    ADMIN_REPLY_STATES[callback.from_user.id] = AdminReplyState(
        ticket_id=ticket_id,
        action="close",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
    )
    await callback.message.answer("Введите текст для ответа.")
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_ticket_close_cancel:"))
async def admin_support_ticket_close_cancel_handler(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно.", show_alert=True)
        return

    ticket_id = int(callback.data.split(":", 1)[1])
    state = ADMIN_REPLY_STATES.get(callback.from_user.id)
    if not state or state.ticket_id != ticket_id:
        await callback.answer("Черновик ответа не найден.", show_alert=True)
        return

    # Запрещаем отмену закрытия, если обращение уже закрыто
    if is_ticket_closed(ticket_id):
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return
    ticket = SUPPORT_TICKETS.get(ticket_id)

    ADMIN_REPLY_STATES.pop(callback.from_user.id, None)
    await callback.message.edit_text("Закрытие обращения отменено.")
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_ticket_close_confirm:"))
async def admin_support_ticket_close_confirm_handler(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно.", show_alert=True)
        return

    ticket_id = int(callback.data.split(":", 1)[1])
    state = ADMIN_REPLY_STATES.get(callback.from_user.id)
    # Если обращение уже закрыто, нечего подтверждать
    ticket = SUPPORT_TICKETS.get(ticket_id)
    if ticket and ticket.status == "closed":
        await callback.answer("Обращение уже закрыто.", show_alert=True)
        return

    if not state or state.ticket_id != ticket_id or not state.pending_text:
        await callback.answer("Сначала введите текст для ответа.", show_alert=True)
        return

    ticket = SUPPORT_TICKETS.get(ticket_id)
    if not ticket:
        ADMIN_REPLY_STATES.pop(callback.from_user.id, None)
        await callback.answer("Обращение не найдено.", show_alert=True)
        return

    ticket.status = "closed"
    ticket.admin_replies.append(f"Решение: {state.pending_text}")
    await bot.send_message(
        ticket.user_id,
        f"Обращение (#{ticket.ticket_id}) закрыто:\n{state.pending_text}",
    )
    ADMIN_REPLY_STATES.pop(callback.from_user.id, None)
    await bot.edit_message_text(
        chat_id=state.chat_id,
        message_id=state.message_id,
        text=support_ticket_text(ticket),
        reply_markup=admin_support_ticket_menu(ticket.ticket_id),
    )
    await callback.message.edit_text("Обращение закрыто.")
    await callback.answer("Готово.")


@dp.callback_query(F.data == "boost")
async def boost_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_boost_payment")
    await callback.message.answer_invoice(
        title="Поддержать сливы",
        description="Поддержка сливов на 15 Telegram Stars.",
        payload="support_slivy_15_stars",
        currency="XTR",
        prices=[LabeledPrice(label="Поддержка", amount=SUPPORT_STARS_AMOUNT)],
        provider_token="",
    )
    await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message) -> None:
    log_user_activity(message, "successful_stars_payment")
    await message.answer("Спасибо за поддержку! Оплата на 15 звезд прошла успешно.")


@dp.callback_query(F.data == "free_builds")
async def free_build_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_free_builds")
    await callback.message.answer(
        "Выберите категорию сливов:",
        reply_markup=leak_variants_menu(),
    )
    await callback.answer()

@dp.inline_query()
async def inline_query_handler(query: InlineQuery) -> None:
    # Простейшая заглушка на входящие inline-запросы,
    # чтобы обновления не оставались необработанными и не засоряли логи.
    # Возвращаем пустой набор результатов, чтобы не показывать ничего.
    try:
        await query.answer([])
    except Exception:
        # Игнорируем любые ошибки, чтобы не ломать работу бота
        pass


@dp.callback_query(F.data == "leaks_maps")
async def leaks_maps_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_leaks_maps")
    await callback.message.answer(
        "Выберите карту, спавн или мир:",
        reply_markup=leak_map_variants_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data == "leaks_builds")
async def leaks_builds_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_leaks_builds")
    await callback.message.answer(
        "Выбери сборку для скачивания:",
        reply_markup=leak_build_variants_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data == "leak_build_lobby_reallyworld")
async def leak_build_lobby_reallyworld_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_leak_build_lobby_reallyworld")
    caption = LEAK_BUILD_ITEMS_BY_CALLBACK["leak_build_lobby_reallyworld"].caption 
    if settings.leak_lobby_build_url:
        await callback.message.answer(
            caption,
            reply_markup=download_link_menu(settings.leak_lobby_build_url),
        )
    else:
        await callback.message.answer(caption + "\n\nСсылка на скачивание пока не добавлена.")

    await callback.message.edit_reply_markup(reply_markup=back_button("back_to_leak_builds").as_markup())

    await callback.answer()


@dp.callback_query(F.data == "leak_build_realllyworld_grief")
async def leak_build_realllyworld_grief_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_leak_build_realllyworld_grief")
    await callback.message.answer(LEAK_BUILD_ITEMS_BY_CALLBACK["leak_build_realllyworld_grief"].caption)
    
    await callback.message.edit_reply_markup(reply_markup=back_button("back_to_leak_builds").as_markup())
    
    await callback.answer()


@dp.callback_query(F.data == "leak_build_reallyworld_full")
async def leak_build_reallyworld_full_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_leak_build_reallyworld_full")
    await callback.message.answer(LEAK_BUILD_ITEMS_BY_CALLBACK["leak_build_reallyworld_full"].caption)
    
    await callback.message.edit_reply_markup(reply_markup=back_button("back_to_leak_builds").as_markup())
    
    await callback.answer()


@dp.callback_query(F.data == "leaks_plugins")
async def leaks_plugins_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_leaks_plugins")
    await callback.message.answer(
        "Выберите плагин для скачивания:",
        reply_markup=leak_plugin_variants_menu(),
    )
    
    builder = back_button("back_to_leak_plugins")
    await callback.message.edit_reply_markup(reply_markup=back_button("back_to_leak_plugins").as_markup())
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    
    await callback.answer()


@dp.callback_query(F.data == "leak_not_updated")
async def leak_not_updated_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    # Initialize support draft without "Отправить обращение" button initially
    SUPPORT_DRAFTS[user_id] = []
    # Mark user as in "leak not updated" flow
    LEAK_NOT_UPDATED_USERS.add(user_id)
    await callback.message.answer(
        "Опишите проблему с не обновленным сливом. Отправьте сообщение."
        # No reply_markup - no button
    )
    await callback.answer()


@dp.callback_query(F.data == "leak_plugin_hw_ban")
async def leak_plugin_hw_ban_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_leak_plugin_hw_ban")

    plugin_path = FREE_DIR / "HWban.jar"

    # Текст
    await callback.message.answer("Плагин на бан с HW\n\nСкачать ниже.")

    # Файл
    if plugin_path.exists():
        await callback.message.answer_document(
            document=FSInputFile(plugin_path),
            protect_content=True
        )
    else:
        await callback.message.answer("Файл пока не добавлен.")

    await callback.answer()


@dp.callback_query(F.data == "leak_plugin_motd_rw")
async def leak_plugin_motd_rw_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_leak_plugin_motd_rw")
    
    caption = LEAK_PLUGIN_ITEMS_BY_CALLBACK["leak_plugin_motd_rw"].caption
    archive_path = FREE_DIR / "MOTDbyDisSqd.zip"
    
    if archive_path.exists():
        await callback.message.answer_document(
            document=FSInputFile(archive_path),
            caption=caption,
            protect_content=True,
        )
    else:
        await callback.message.answer(caption + "\n\nФайл пока не добавлен.")
    
    builder = back_button("back_to_leak_plugins")
    await callback.message.edit_reply_markup(reply_markup=back_button("back_to_leak_plugins").as_markup())
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    
    await callback.answer()


@dp.callback_query(F.data == "leak_resourcepack_rw")
async def leak_resourcepack_rw_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    log_user_activity(callback, "open_leak_resourcepack_rw")

    archive_path = FREE_DIR / "RWRPDISSQD.zip"
    caption = "Оригинальный РесурсПак RW."

    if archive_path.exists():
        await callback.message.answer_document(
            document=FSInputFile(archive_path),
            caption=caption,
            protect_content=True,
        )
    else:
        await callback.message.answer("❌ Файл пока не добавлен.")


@dp.callback_query(F.data == "leaks_resourcepacks")
async def leaks_resourcepacks_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    log_user_activity(callback, "open_leaks_resourcepacks")
    await callback.message.edit_text(
        "Выберите РесурсПак для скачивания:",
        reply_markup=leak_resourcepack_variants_menu(),
    )


@dp.callback_query(F.data == "leak_map_spawn_reallyworld")
async def leak_map_spawn_reallyworld_handler(callback: CallbackQuery) -> None:
    await callback.answer()  # Immediately answer to avoid timeout
    log_user_activity(callback, "open_leak_map_spawn_reallyworld")
    caption = "Красивейший спавн R*alluWorld\n\nМай 2026\n\nСкачать ниже."
    image_one = ASSETS_DIR / "spawn_reallyworld_1.png"
    image_two = ASSETS_DIR / "spawn_reallyworld_2.png"
    image_three = ASSETS_DIR / "spawn_reallyworld_3.png"
    archive_path = FREE_DIR / "RWPAWNFULL.zip"

    if image_one.exists() and image_two.exists() and image_three.exists():
        media = [
            InputMediaPhoto(media=FSInputFile(image_one), caption=caption),
            InputMediaPhoto(media=FSInputFile(image_two)),
            InputMediaPhoto(media=FSInputFile(image_three)),
        ]
        await callback.message.answer_media_group(media=media, protect_content=True)
    elif image_one.exists() and image_two.exists():
        media = [
            InputMediaPhoto(media=FSInputFile(image_one), caption=caption),
            InputMediaPhoto(media=FSInputFile(image_two)),
        ]
        await callback.message.answer_media_group(media=media, protect_content=True)
    elif image_one.exists():
        await callback.message.answer_photo(
            photo=FSInputFile(image_one),
            caption=caption,
            protect_content=True,
        )
    else:
        await callback.message.answer(caption)

    if archive_path.exists():
        await callback.message.answer_document(document=FSInputFile(archive_path))
    else:
        await callback.message.answer("Архив пока не добавлен.")

    await callback.message.edit_reply_markup(reply_markup=back_button("back_to_leak_maps").as_markup())
    await callback.answer()


@dp.callback_query(F.data == "leak_map_oremine")
async def leak_map_oremine_handler(callback: CallbackQuery) -> None:
    await callback.answer()  # Immediately answer to avoid timeout
    log_user_activity(callback, "open_leak_map_oremine")
    caption = "Красивейший спавн сервера Or*Mine\n\nСкачать ниже\n\nИмеется небольшой баг.\n\nНо спавн не перестает быть красивым 🔥"
    image_one = ASSETS_DIR / "spawn_oremine_1.png"
    image_two = ASSETS_DIR / "spawn_oremine_2.png"
    archive_path = FREE_DIR / "OreMineByDisSqd.zip"

    if image_one.exists() and image_two.exists():
        media = [
            InputMediaPhoto(media=FSInputFile(image_one), caption=caption),
            InputMediaPhoto(media=FSInputFile(image_two)),
        ]
        await callback.message.answer_media_group(media=media, protect_content=True)
    elif image_one.exists():
        await callback.message.answer_photo(
            photo=FSInputFile(image_one),
            caption=caption,
            protect_content=True,
        )
    else:
        await callback.message.answer(caption)

    if archive_path.exists():
        await callback.message.answer_document(document=FSInputFile(archive_path))
    else:
        await callback.message.answer("Архив пока не добавлен.")

    await callback.message.edit_reply_markup(reply_markup=back_button("back_to_leak_maps").as_markup())
    await callback.answer()


@dp.callback_query(F.data == "leak_map_aresmine")
async def leak_map_aresmine_handler(callback: CallbackQuery) -> None:
    await callback.answer()  # Immediately answer to avoid timeout
    log_user_activity(callback, "open_leak_map_aresmine")
    caption = "Красивейший спавн Ar*sMine\n\nНовый вайп.\n\nСкачать ниже"
    image_one = ASSETS_DIR / "spawn_aresmine_1.png"
    image_two = ASSETS_DIR / "spawn_aresmine_2.png"
    archive_path = FREE_DIR / "SpawnAresMineByDisSqd.zip"

    if image_one.exists() and image_two.exists():
        media = [
            InputMediaPhoto(media=FSInputFile(image_one), caption=caption),
            InputMediaPhoto(media=FSInputFile(image_two)),
        ]
        await callback.message.answer_media_group(media=media, protect_content=True)
    elif image_one.exists():
        await callback.message.answer_photo(
            photo=FSInputFile(image_one),
            caption=caption,
            protect_content=True,
        )
    else:
        await callback.message.answer(caption)

    if archive_path.exists():
        await callback.message.answer_document(document=FSInputFile(archive_path))
    else:
        await callback.message.answer("Архив пока не добавлен.")

    await callback.message.edit_reply_markup(reply_markup=back_button("back_to_leak_maps").as_markup())
    await callback.answer()


@dp.callback_query(F.data == "leak_map_spawn_lobby_reallyworld")
async def leak_map_spawn_lobby_reallyworld_handler(callback: CallbackQuery) -> None:
    log_user_activity(callback, "open_leak_map_spawn_lobby_reallyworld")
    archive_path = FREE_DIR / "HUB RW NEW.zip"
    caption = "Карта lobby R*allyWorld\n\nСкачать ниже"

    if archive_path.exists():
        await callback.message.answer_document(
            document=FSInputFile(archive_path),
            caption=caption,
            protect_content=True,
        )
    else:
        await callback.message.answer("Архив пока не добавлен.")

    await callback.message.edit_reply_markup(reply_markup=back_button("back_to_leak_maps").as_markup())
    await callback.answer()


async def handle_pending_purchase_message(message: Message) -> bool:
    pending = PENDING_PURCHASES.get(message.from_user.id)
    if not pending:
        return False

    if pending.step == "await_funpay_nick":
        log_user_activity(message, "enter_funpay_nick")
        message_text = (message.text or message.caption or "").strip()
        if not message_text:
            await message.answer("Отправьте ник на FunPay текстом одним сообщением.")
            return True

        pending.funpay_nick = message_text
        pending.step = "await_payment_confirmation"
        item = ALL_ITEMS_BY_CALLBACK[pending.item_key]
        await message.answer(
            f"Хорошо! Теперь оплатите товар:\n{item.funpay_url}",
            reply_markup=payment_check_menu(item.funpay_url),
        )
        return True

    if pending.step == "await_payment_confirmation":
        item = ALL_ITEMS_BY_CALLBACK[pending.item_key]
        await message.answer(
            "Когда оплатите товар, нажмите `Я оплатил`. Если передумали, нажмите `Я передумал`.",
            reply_markup=payment_check_menu(item.funpay_url),
            parse_mode="Markdown",
        )
        return True

    return False


async def handle_rename_flow_message(message: Message, bot: Bot) -> bool:
    flow = RENAME_FLOWS.get(message.from_user.id)
    if not flow:
        return False

    log_user_activity(message, "send_rename_data")

    username = f"@{message.from_user.username}" if message.from_user.username else "без username"
    if not flow.notified_admin:
        await bot.send_message(
            settings.support_admin_id,
            (
                f"🛠 Пользователь начал отправлять данные для услуги {flow.item_title}\n\n"
                f"👤 Пользователь: {message.from_user.full_name}\n"
                f"🔗 Username: {username}\n"
                f"🆔 User ID: {message.from_user.id}"
            ),
        )
        flow.notified_admin = True

    if message.text:
        await bot.send_message(
            settings.support_admin_id,
            f"📄 Данные от пользователя:\n\n{message.text}",
        )
    else:
        await message.copy_to(settings.support_admin_id)

    await message.answer(
        "Данные получены и отправлены. Если нужно, можете отправить еще сообщения или вернуться в меню через /start."
    )
    return True


async def handle_admin_support_reply(message: Message, bot: Bot) -> bool:
    if not is_admin(message.from_user.id):
        return False

    state = ADMIN_REPLY_STATES.get(message.from_user.id)
    if not state:
        return False

    ticket = SUPPORT_TICKETS.get(state.ticket_id)
    if not ticket:
        ADMIN_REPLY_STATES.pop(message.from_user.id, None)
        await message.answer("Обращение не найдено.")
        return True

    # Если обращение уже закрыто, не разрешать ADMIN-ответы
    if ticket.status == "closed":
        ADMIN_REPLY_STATES.pop(message.from_user.id, None)
        await message.answer("Обращение уже закрыто.")
        return True

    reply_text = (message.text or message.caption or "").strip()
    if not reply_text:
        await message.answer("Отправьте ответ текстом одним сообщением.")
        return True

    log_user_activity(message, f"admin_support_{state.action}")
    state.pending_text = reply_text
    await message.answer(
        f"Введите текст для ответа:\n\n{reply_text}",
        reply_markup=admin_support_close_confirm_menu(ticket.ticket_id),
    )
    return True


@dp.message()
async def user_message_handler(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id
    # Check subscription first - block all usage if not subscribed
    if message.text and message.text.startswith("/start"):
        # /start handler will deal with it
        pass
    else:
        not_subscribed, errors = await check_subscription(user_id, bot)
        if not_subscribed:
            await send_subscription_prompt(message, bot, not_subscribed, errors)
            return
    # Сохраняем username для поиска
    if message.from_user.username:
        USERNAME_TO_ID[message.from_user.username.lower()] = message.from_user.id
    # Промокод: первая часть активации через администратора
    if user_id in PROMO_DRAFTS:
        draft = PROMO_DRAFTS[user_id]
        # если код ещё не введён, трактуем сообщение как ввод кода
        if not draft.code:
            code = (message.text or message.caption or "").strip()
            if not code:
                await message.answer("Пожалуйста, введите промокод для активации.")
                return
            promo = PROMO_CODES.get(code)
            if not promo:
                await message.answer("Неверный промокод. Попробуйте ещё раз или отмените.")
                return
            # Проверяем, нет ли уже активного промокода
            existing = USER_PROMOS.get(user_id)
            if existing:
                activated_at = USER_PROMO_ACTIVATED_AT.get(user_id)
                if activated_at and (datetime.utcnow() - activated_at).total_seconds() < 3 * 86400:
                    await message.answer("У вас уже есть активный промокод. Дождитесь истечения срока (3 дня).")
                    return
                else:
                    # Удаляем истёкший
                    USER_PROMOS.pop(user_id, None)
                    USER_PROMO_ACTIVATED_AT.pop(user_id, None)
            # Активируем промокод
            PROMO_CODES[code] = promo
            USER_PROMOS[user_id] = code
            PROMO_DRAFTS.pop(user_id, None)
            USER_PROMO_ACTIVATED_AT[user_id] = datetime.utcnow()
            await message.answer(
                f"Промокод {code} активирован. На активацию промокода дается 3 дня. Осталось 3 дня. Чтобы получить приз напишите в Тех.Поддержку"
            )
            return
        # если код уже введён, ничего не делаем здесь
        return

    if await handle_admin_support_reply(message, bot):
        return

    if await handle_pending_purchase_message(message):
        return

    if await handle_rename_flow_message(message, bot):
        return

    draft = SUPPORT_DRAFTS.get(message.from_user.id)
    if draft is not None:
        log_user_activity(message, "write_support_message")
        message_text = message.text or message.caption
        if not message_text:
            await message.answer(
                "Пока можно отправлять только текстовые обращения.",
                reply_markup=support_request_menu(),
            )
            return
        
        draft.append(message_text.strip())
        # Check if this is first message in "leak not updated" flow
        if message.from_user.id in LEAK_NOT_UPDATED_USERS and len(draft) == 1:
            # Send separate message with "Отправить обращение" button
            await message.answer(
                "Сообщение добавлено. Нажмите кнопку для отправки.",
                reply_markup=support_request_menu(),
            )
            LEAK_NOT_UPDATED_USERS.remove(message.from_user.id)
            return
        await message.answer(
            "Сообщение добавлено в обращение. Когда закончите, нажмите `Отправить обращение`.",
            reply_markup=support_request_menu(),
            parse_mode="Markdown",
        )
        return

    await message.answer("Неизвестная команда. Используйте /start")


@dp.edited_message()
async def edited_message_handler(message: Message) -> None:
    # Игнорируем редактируемые сообщения, чтобы не помечать их как необработанные
    return

async def test_bot_token_health() -> bool:
    token = settings.bot_token
    url = f"https://api.telegram.org/bot{token}/getMe"
    loop = asyncio.get_event_loop()
    def _sync_test():
        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(url, timeout=15, context=ctx) as resp:
                return resp.getcode() == 200
        except Exception as e:
            logging.exception("Health test error: %s", e)
            return False
    return await loop.run_in_executor(None, _sync_test)

async def main() -> None:
    bot = Bot(token=settings.bot_token)
    # Предстартовый health-check токена (неблокирующий)
    if not await test_bot_token_health():
        logging.warning("Health-check токена не прошёл, но бот будет запущен (будут повторные попытки).")

    retry = 0
    while True:
        try:
            await dp.start_polling(bot)
            break
        except (TelegramNetworkError, ClientConnectorError) as error:
            delay = min(60, 5 * (2 ** retry))
            logging.warning(
                "Telegram API connection error: %s. Повтор через %d секунд.",
                error,
                delay,
            )
            await asyncio.sleep(delay)
            retry = min(retry + 1, 6)
        except Exception as error:
            logging.exception("Неожиданная ошибка в работе бота: %s", error)
            delay = min(60, 5 * (2 ** retry))
            await asyncio.sleep(delay)
            retry = min(retry + 1, 6)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
