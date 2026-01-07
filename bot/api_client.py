import os
import httpx

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "change_me")

async def init_user(user_id: int, username: str | None) -> dict:
    """初始化用户账户"""
    url = f"{API_URL}/api/internal/init_user"
    headers = {"x-internal-key": INTERNAL_API_KEY}
    payload = {"user_id": user_id, "username": username}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            raise RuntimeError(r.text)
        return r.json()

async def join_room_as_user(invite_token: str, user_id: int, username: str | None) -> dict:
    url = f"{API_URL}/api/internal/join"
    headers = {"x-internal-key": INTERNAL_API_KEY}
    payload = {"invite_token": invite_token, "user_id": user_id, "username": username}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            raise RuntimeError(r.text)
        return r.json()
