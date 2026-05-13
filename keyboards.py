from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from catalog import LEAK_RESOURCEPACK_VARIANTS, BUILD_VARIANTS, LEAK_BUILD_VARIANTS, LEAK_MAP_VARIANTS, LEAK_PLUGIN_VARIANTS, LEAK_VARIANTS, OTHER_VARIANTS


def start_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить сборку", callback_data="buy_build")
    builder.button(text="📁 Прочее", callback_data="other")
    builder.button(text="🛠 Тех.Поддержка", callback_data="support")
    builder.button(text="⭐ Поддержать сливы (15 ⭐)", callback_data="boost")
    builder.button(text="🆓 Сливы", callback_data="free_builds")
    builder.button(text="Активировать промокод", callback_data="promo_activate")
    builder.button(text="Не нашли нужный вам товар?", callback_data="help_find_product")
    if is_admin:
        builder.button(text="🔒 Приватный режим", callback_data="admin_privacy_toggle")
        builder.adjust(3, 1, 1, 1, 1, 1)
    else:
        builder.adjust(3, 1, 1, 1)
    return builder.as_markup()


def leak_resourcepack_variants_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in LEAK_RESOURCEPACK_VARIANTS:
        builder.button(text=item.title, callback_data=item.callback_data)
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def build_variants_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for build in BUILD_VARIANTS:
        builder.button(text=build.title, callback_data=build.callback_data)
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def other_variants_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in OTHER_VARIANTS:
        builder.button(text=item.title, callback_data=item.callback_data)
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def leak_variants_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in LEAK_VARIANTS:
        builder.button(text=item.title, callback_data=item.callback_data)
    builder.button(text="❓ Не обновленный слив?", callback_data="leak_not_updated")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def leak_map_variants_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in LEAK_MAP_VARIANTS:
        builder.button(text=item.title, callback_data=item.callback_data)
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def leak_build_variants_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in LEAK_BUILD_VARIANTS:
        builder.button(text=item.title, callback_data=item.callback_data)
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def leak_plugin_variants_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in LEAK_PLUGIN_VARIANTS:
        builder.button(text=item.title, callback_data=item.callback_data)
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def download_link_menu(url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Скачать", url=url)
    return builder.as_markup()


def ready_to_pay_menu(item_key: str, url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Готов оплатить", callback_data=f"purchase:{item_key}")
    builder.button(text="🔙 Назад", callback_data="back_to_build_variants")
    builder.adjust(1)
    return builder.as_markup()


def payment_check_menu(url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Открыть товар", url=url)
    builder.button(text="✅ Я оплатил", callback_data="purchase_paid_yes")
    builder.button(text="❌ Я передумал", callback_data="purchase_paid_no")
    builder.adjust(1, 2)
    return builder.as_markup()


def admin_payment_menu(request_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить оплату", callback_data=f"admin_ok:{request_id}")
    builder.button(text="❌ Отклонить", callback_data=f"admin_no:{request_id}")
    builder.adjust(1)
    return builder.as_markup()


def support_request_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📨 Отправить обращение", callback_data="support_send")
    builder.button(text="❌ Отменить", callback_data="support_cancel")
    builder.adjust(1)
    return builder.as_markup()


def support_cancel_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data="support_cancel")
    builder.adjust(1)
    return builder.as_markup()


def admin_support_requests_menu(tickets: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ticket_id, label in tickets:
        builder.button(text=label, callback_data=f"admin_ticket:{ticket_id}")
    builder.button(text="🔄 Обновить", callback_data="admin_support_requests")
    builder.adjust(1)
    return builder.as_markup()


def admin_support_ticket_menu(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🟠 В рассмотрении", callback_data=f"admin_ticket_review:{ticket_id}")
    builder.button(text="🔴 Закрыть", callback_data=f"admin_ticket_close:{ticket_id}")
    builder.button(text="⬅️ К запросам", callback_data="admin_support_requests")
    builder.adjust(1)
    return builder.as_markup()


def admin_support_ticket_menu_closed(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Обращение закрыто: никаких действий со стороны администратора быть не должно
    builder.button(text="⬅️ К запросам", callback_data="admin_support_requests")
    builder.adjust(1)
    return builder.as_markup()


def admin_support_close_confirm_menu(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data=f"admin_ticket_close_cancel:{ticket_id}")
    builder.button(text="🔴 Закрыть", callback_data=f"admin_ticket_close_confirm:{ticket_id}")
    builder.adjust(1, 1)
    return builder.as_markup()
