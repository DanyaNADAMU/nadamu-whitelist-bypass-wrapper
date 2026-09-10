"""
Inline keyboards and button layouts for WhitelistBypass Telegram Bot.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.telegram.locales import get_text


def get_user_main_keyboard(username: str, lang: str = "ru", is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=get_text("btn_qr", lang),
                callback_data=f"qr:{username}",
            ),
            InlineKeyboardButton(
                text=get_text("btn_rotate", lang),
                callback_data=f"rot_confirm:{username}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_text("btn_provider", lang),
                callback_data=f"prov_menu:{username}",
            ),
            InlineKeyboardButton(
                text=get_text("btn_status", lang),
                callback_data=f"status:{username}",
            ),
        ],
    ]

    if is_admin:
        rows.append(
            [
                InlineKeyboardButton(
                    text=get_text("btn_admin_list", lang),
                    callback_data="admin_list",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_provider_keyboard(username: str, current_provider: str, lang: str = "ru") -> InlineKeyboardMarkup:
    providers = [
        ("vk", "🔵 VK Calls"),
        ("telemost", "🔴 Яндекс.Телемост"),
        ("wbstream", "🟣 WB Stream"),
        ("dion", "🟢 DION"),
    ]

    buttons = []
    row = []
    for prov_key, label in providers:
        btn_text = f"{label} (текущий)" if prov_key == current_provider else label
        row.append(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"set_prov:{username}:{prov_key}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                text=get_text("btn_back", lang),
                callback_data=f"back_main:{username}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_rotate_confirm_keyboard(username: str, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, пересоздать",
                    callback_data=f"rot_do:{username}",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"back_main:{username}",
                ),
            ]
        ]
    )


def get_post_rotate_keyboard(username: str, lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("btn_qr", lang),
                    callback_data=f"qr:{username}",
                ),
                InlineKeyboardButton(
                    text=get_text("btn_status", lang),
                    callback_data=f"status:{username}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("btn_back", lang),
                    callback_data=f"back_main:{username}",
                )
            ],
        ]
    )
