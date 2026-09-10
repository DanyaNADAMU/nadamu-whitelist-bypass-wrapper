"""
VK Inline Keyboard builders for WhitelistBypass / Iris VK Bot.
"""

import json
from typing import Any
from bot.vk.locales import get_text


def _btn(label: str, payload_data: dict[str, Any], color: str = "secondary") -> dict[str, Any]:
    """Helper to create a VK text button with payload and color."""
    return {
        "action": {
            "type": "text",
            "label": label[:40],  # VK max label length is 40 chars
            "payload": json.dumps(payload_data, ensure_ascii=False),
        },
        "color": color,
    }


def get_user_main_keyboard(username: str, lang: str = "ru", is_admin: bool = False) -> dict[str, Any]:
    """Build main inline keyboard for a user."""
    buttons = [
        [
            _btn(get_text("btn_qr", lang), {"cmd": "qr", "user": username}, "primary"),
            _btn(get_text("btn_rotate", lang), {"cmd": "rot_confirm", "user": username}, "secondary"),
        ],
        [
            _btn(get_text("btn_provider", lang), {"cmd": "prov_menu", "user": username}, "secondary"),
            _btn(get_text("btn_status", lang), {"cmd": "status", "user": username}, "secondary"),
        ],
    ]

    if is_admin:
        buttons.append(
            [
                _btn(get_text("btn_admin_list", lang), {"cmd": "admin_list"}, "primary")
            ]
        )

    return {"inline": True, "buttons": buttons}


def get_provider_keyboard(username: str, current_provider: str, lang: str = "ru") -> dict[str, Any]:
    """Build inline keyboard for switching media provider."""
    providers = [
        ("vk", "🔵 VK Calls"),
        ("telemost", "🔴 Телемост"),
        ("wbstream", "🟣 WB Stream"),
        ("dion", "🟢 DION"),
    ]

    button_rows = []
    current_row = []

    for prov_key, label in providers:
        is_current = prov_key == current_provider
        btn_label = f"✓ {label}" if is_current else label
        color = "positive" if is_current else "secondary"
        current_row.append(
            _btn(btn_label, {"cmd": "set_prov", "user": username, "prov": prov_key}, color)
        )
        if len(current_row) == 2:
            button_rows.append(current_row)
            current_row = []

    if current_row:
        button_rows.append(current_row)

    button_rows.append(
        [
            _btn(get_text("btn_back", lang), {"cmd": "back_main", "user": username}, "secondary")
        ]
    )

    return {"inline": True, "buttons": button_rows}


def get_rotate_confirm_keyboard(username: str, lang: str = "ru") -> dict[str, Any]:
    """Build confirmation dialog buttons for room rotation."""
    return {
        "inline": True,
        "buttons": [
            [
                _btn("✅ Да, пересоздать", {"cmd": "rot_do", "user": username}, "positive"),
                _btn("❌ Отмена", {"cmd": "back_main", "user": username}, "negative"),
            ]
        ],
    }


def get_post_rotate_keyboard(username: str, lang: str = "ru") -> dict[str, Any]:
    """Build post-rotation action keyboard."""
    return {
        "inline": True,
        "buttons": [
            [
                _btn(get_text("btn_qr", lang), {"cmd": "qr", "user": username}, "primary"),
                _btn(get_text("btn_status", lang), {"cmd": "status", "user": username}, "secondary"),
            ],
            [
                _btn(get_text("btn_back", lang), {"cmd": "back_main", "user": username}, "secondary")
            ],
        ],
    }
