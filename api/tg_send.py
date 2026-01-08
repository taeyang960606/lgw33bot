import httpx

async def send_invite_message(
    bot_token: str,
    chat_id: int,
    text: str,
    invite_token: str
) -> None:
    """发送房间邀请消息到群聊"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # 构建按钮 - 使用URL按钮跳转到机器人
    buttons = [
        [{"text": "🎮 前往机器人查看房间", "url": "https://t.me/lgw33tokenbot"}]
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
