import httpx

async def send_invite_message(
    bot_token: str,
    chat_id: int,
    text: str,
    invite_token: str
) -> None:
    """发送房间邀请消息到群聊"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # 构建按钮 - 只使用callback_data,不使用web_app(群组不支持)
    buttons = [
        [{"text": "加入房间挑战", "callback_data": f"join:{invite_token}"}]
    ]

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": buttons
        }
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()

async def send_game_result(
    bot_token: str,
    chat_id: int,
    text: str
) -> None:
    """发送游戏结果到群聊"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
