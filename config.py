from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent


def _load_env() -> None:
    env_path = BASE_DIR / ".env"
    example_env_path = BASE_DIR / ".env.example"

    if env_path.exists():
        load_dotenv(env_path)
        return

    if example_env_path.exists():
        load_dotenv(example_env_path)


_load_env()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    free_build_path: Path
    free_build_url: str | None
    leak_lobby_build_url: str | None
    paid_grief_build_url: str | None
    paid_grief_build_password: str | None
    paid_full_build_url: str | None
    paid_full_build_password: str | None
    support_admin_id: int
    paid_grief_build_path: Path
    paid_full_build_path: Path
    paid_plugins_path: Path


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("Не найден BOT_TOKEN. Заполните .env на основе .env.example")

    free_build_raw = os.getenv("FREE_BUILD_PATH", "free/build.zip").strip()
    free_build_path = (BASE_DIR / free_build_raw).resolve()

    free_build_url = os.getenv("FREE_BUILD_URL", "").strip() or None
    leak_lobby_build_url = (
        os.getenv(
            "LEAK_LOBBY_BUILD_URL",
            "https://www.mediafire.com/file/q7bbcnvjfruz3hc/RWLOBBYDISSQUAD.zip/file",
        ).strip()
        or None
    )
    paid_grief_build_url = (
        os.getenv(
            "PAID_GRIEF_BUILD_URL",
            "https://workupload.com/file/vUnFpZGuKQ6",
        ).strip()
        or None
    )
    paid_grief_build_password = os.getenv("PAID_GRIEF_BUILD_PASSWORD", "RWGRIEFDISLETO").strip() or None
    paid_full_build_url = (
        os.getenv(
            "PAID_FULL_BUILD_URL",
            "https://workupload.com/file/qWLYrvtngyR",
        ).strip()
        or None
    )
    paid_full_build_password = os.getenv("PAID_FULL_BUILD_PASSWORD", "RWDISSQDLETO").strip() or None
    support_admin_id = int(os.getenv("SUPPORT_ADMIN_ID", "6517766247").strip())

    paid_grief_build_raw = os.getenv("PAID_GRIEF_BUILD_PATH", "paid/reallyworld-grief.zip").strip()
    paid_full_build_raw = os.getenv("PAID_FULL_BUILD_PATH", "paid/reallyworld-full.zip").strip()
    paid_plugins_raw = os.getenv("PAID_PLUGINS_PATH", "paid/pluginsanticrash.zip").strip()

    return Settings(
        bot_token=bot_token,
        free_build_path=free_build_path,
        free_build_url=free_build_url,
        leak_lobby_build_url=leak_lobby_build_url,
        paid_grief_build_url=paid_grief_build_url,
        paid_grief_build_password=paid_grief_build_password,
        paid_full_build_url=paid_full_build_url,
        paid_full_build_password=paid_full_build_password,
        support_admin_id=support_admin_id,
        paid_grief_build_path=(BASE_DIR / paid_grief_build_raw).resolve(),
        paid_full_build_path=(BASE_DIR / paid_full_build_raw).resolve(),
        paid_plugins_path=(BASE_DIR / paid_plugins_raw).resolve(),
    )
