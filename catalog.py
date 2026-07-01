from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuildVariant:
    title: str
    callback_data: str
    caption: str
    funpay_url: str
    image_name: str
    delivery_type: str


@dataclass(frozen=True)
class OtherVariant:
    title: str
    callback_data: str
    caption: str
    image_name: str | None
    funpay_url: str
    delivery_type: str


@dataclass(frozen=True)
class LeakVariant:
    title: str
    callback_data: str
    caption: str


@dataclass(frozen=True)
class LeakMapVariant:
    title: str
    callback_data: str
    caption: str


@dataclass(frozen=True)
class LeakBuildVariant:
    title: str
    callback_data: str
    caption: str


@dataclass(frozen=True)
class LeakPluginVariant:
    title: str
    callback_data: str
    caption: str


WELCOME_TEXT = (
    "Добро пожаловать в бота DisSquad. Выберите нужный вам товар или слив:"
)

FREE_BUILD_TEXT = (
    "Выберите категорию сливов ниже."
)

# ================== СБОРКИ ==================

BUILD_VARIANTS: tuple[BuildVariant, ...] = (
    BuildVariant(
        title="REALLYWORLD GRIEF",
        callback_data="build_reallyworld_grief",
        caption=(
            "Сборка ReallyWorld GRIEF ( Май )\n\n"
            "Стоимость данной сборки <s>150</s> 125 ₽ ( с учётом скидки )"
        ),
        funpay_url="https://funpay.com/lots/offer?id=67418853",
        image_name="RWSBORKA.png",
        delivery_type="file",
    ),
    BuildVariant(
        title="REALLYWORLD FULL",
        callback_data="build_reallyworld_full",
        caption=(
            "Сборка ReallyWorld FULL ( Май )\n\n"
            "Стоимость данной сборки 200 ₽"
        ),
        funpay_url="https://funpay.com/lots/offer?id=68009619",
        image_name="RWSBORKA.png",
        delivery_type="file",
    ),
)

# ================== ПРОЧЕЕ ==================

OTHER_VARIANTS: tuple[OtherVariant, ...] = (
    OtherVariant(
        title="Базовые плагины на защиту от краша ( не авторские )",
        callback_data="other_basic_plugins",
        caption=(
            "<b>Базовые</b> плагины от краша ( не авторские )\n\n"
            "Стоимость данных плагинов - <s>40</s> 30 ₽"
        ),
        image_name="PLUGINSANTICRASH.png",
        funpay_url="https://funpay.com/lots/offer?id=66561156",
        delivery_type="file",
    ),
    OtherVariant(
        title="Ренейм нашей сборки",
        callback_data="other_rename_our_build",
        caption=(
            "Ренейм <b>НАШЕЙ</b> сборки\n\n"
            "Стоимость данной услуги <s>60</s> 50 ₽"
        ),
        image_name="RENAMEMY.png",
        funpay_url="https://funpay.com/lots/offer?id=68067037",
        delivery_type="rename",
    ),
    OtherVariant(
        title="Ренейм не нашей сборки",
        callback_data="other_rename_not_our_build",
        caption=(
            "Ренейм <b>НЕ НАШЕЙ</b> сборки\n\n"
            "Стоимость данной услуги <s>75</s> 65 ₽"
        ),
        image_name="RENAMEMY.png",
        funpay_url="https://funpay.com/lots/offer?id=67705657",
        delivery_type="rename",
    ),

    # ===== НОВОЕ =====

    OtherVariant(
        title="Создание связки Velocity",
        callback_data="other_velocity_bundle",
        caption=(
            "Создание связки Velocity\n\n"
            "Стоимость данной услуги - <s>40</s> 20 ₽"
        ),
        image_name="VelocitySvyaz.png",
        funpay_url="https://funpay.com/lots/offer?id=68394611",
        delivery_type="rename",
    ),
    OtherVariant(
        title="Фикс сборки",
        callback_data="other_fix_build",
        caption=(
            "Фикс сборки от багов\n\n"
            "Стоимость данной услуги - <s>50</s> 20 ₽ за 1 плагин ( также относятся конфиги )"
        ),
        image_name="FixSB.png",
        funpay_url="https://funpay.com/lots/offer?id=68139812",
        delivery_type="rename",
    ),
)

# ================== СЛИВЫ ==================

LEAK_VARIANTS: tuple[LeakVariant, ...] = (
    LeakVariant(
        title="Карты, спавны, миры",
        callback_data="leaks_maps",
        caption="Раздел: Карты, спавны, миры",
    ),
    LeakVariant(
        title="Сборки",
        callback_data="leaks_builds",
        caption="Раздел: Сборки",
    ),
    LeakVariant(
        title="Плагины",
        callback_data="leaks_plugins",
        caption="Раздел: Плагины",
    ),
    LeakVariant(
        title="РесурсПаки",
        callback_data="leaks_resourcepacks",
        caption="Раздел: РесурсПаки",
    ),
)

LEAK_RESOURCEPACK_VARIANTS = (
    LeakVariant(
        title="РесурсПак RW",
        callback_data="leak_resourcepack_rw",
        caption="РесурсПак RW\n\nСкачать ниже.",
    ),
)

# ================== КАРТЫ ==================

LEAK_MAP_VARIANTS: tuple[LeakMapVariant, ...] = (
    LeakMapVariant(
        title="SPAWN REALLYWORLD",
        callback_data="leak_map_spawn_reallyworld",
        caption="Раздел: SPAWN REALLYWORLD",
    ),
    LeakMapVariant(
        title="SPAWN OreMine",
        callback_data="leak_map_oremine",
        caption="Раздел: SPAWN OreMine",
    ),
    LeakMapVariant(
        title="SPAWN AresMine",
        callback_data="leak_map_aresmine",
        caption="Раздел: SPAWN AresMine",
    ),
    LeakMapVariant(
        title="SPAWN LOBBY REALLYWORLD",
        callback_data="leak_map_spawn_lobby_reallyworld",
        caption="Раздел: SPAWN LOBBY REALLYWORLD",
    ),
)

# ================== СБОРКИ (СЛИВЫ) ==================

LEAK_BUILD_VARIANTS: tuple[LeakBuildVariant, ...] = (
    LeakBuildVariant(
        title="Сборка LOBBY REALLYWORLD",
        callback_data="leak_build_lobby_reallyworld",
        caption=(
            "Lobby R*alluWorld\n"
            "Данная сборка сделана командой DisSqd ( самыми первыми )\n\n"
            "Что нового?\n"
            "- Добавлено MOTD с R*alluWorld"
        ),
    ),
    LeakBuildVariant(
        title="Сборка REALLLYWORLD GRIEF",
        callback_data="leak_build_realllyworld_grief",
        caption="Сборка REALLLYWORLD GRIEF скоро будет доступна для скачивания.",
    ),
    LeakBuildVariant(
        title="Сборка REALLYWORLD FULL",
        callback_data="leak_build_reallyworld_full",
        caption="Сборка REALLYWORLD FULL скоро будет доступна для скачивания.",
    ),
)

# ================== ПЛАГИНЫ ==================

LEAK_PLUGIN_VARIANTS: tuple[LeakPluginVariant, ...] = (
    LeakPluginVariant(
        title="Плагин на бан HW",
        callback_data="leak_plugin_hw_ban",
        caption="Плагин на бан HW\n\nСкачать ниже.",
    ),
    LeakPluginVariant(
        title="MOTD с RW",
        callback_data="leak_plugin_motd_rw",
        caption=(
            "MOTD с R*alluWorld 2026 Май\n\n"
            "В папке находится .jar плагин и папка с конфигом.\n\n"
            "Ядро - Paper/Velocity/Purpur и другие\n\n"
            "Что нужно?\n"
            "- Загрузите .jar в папку /plugins\n"
            "- Папку PixelMOTD в ту же папку /plugins\n"
            "- После перемещения папки назовите её PixelMOTD, вместо PixelMOTD ( все ядра, кроме velocity ) или Velocity\n\n"
            "Сделано командой DisSquad.\n\n"
            "Что изменилось?\n"
            "- Добавил конфиг для Velocity."
        ),
    ),
)
