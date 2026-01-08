import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import init_db, get_conn
from .tg_send import send_invite_message, send_game_result

# 导入 Bot 相关
from aiogram import Bot
from aiogram.types import Update
from bot.main import dp  # 导入 dispatcher

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "change_me")
DEFAULT_BALANCE = int(os.getenv("DEFAULT_BALANCE", "1000"))
DEFAULT_CHAT_ID = int(os.getenv("DEFAULT_CHAT_ID", "0"))  # 默认游戏群组ID
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
MINIAPP_URL = os.getenv("MINIAPP_URL", "http://127.0.0.1:8000")

# Webhook 配置
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = API_URL + WEBHOOK_PATH

# 后台任务控制
cleanup_task = None
bot_instance = None

# --------------------
# Models
# --------------------
class DebugUser(BaseModel):
    user_id: int
    username: str | None = None

class CreateRoomIn(BaseModel):
    user: DebugUser
    bet_amount: int = Field(ge=1, le=100000)
    chat_id: int | None = None  # 如果在群上下文创建，就填群 chat_id（负数）

class ShareRoomIn(BaseModel):
    user: DebugUser
    chat_id: int | None = None  # 群 chat_id（负数），如果不填则使用默认群组

class InitUserIn(BaseModel):
    user_id: int
    username: str | None = None

class JoinRoomIn(BaseModel):
    user_id: int
    username: str | None = None
    invite_token: str

class ReadyIn(BaseModel):
    user: DebugUser

class ClickIn(BaseModel):
    user: DebugUser

# --------------------
# Helpers
# --------------------
def require_internal(request: Request) -> None:
    key = request.headers.get("x-internal-key", "")
    if key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

def upsert_user(user_id: int, username: str | None) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO users(user_id, username, available, frozen) VALUES(?,?,?,0)",
            (user_id, username, DEFAULT_BALANCE)
        )
        cur.execute(
            "INSERT INTO ledger(tx_id, user_id, type, amount, ref) VALUES(?,?,?,?,?)",
            (str(uuid.uuid4()), user_id, "CREDIT", DEFAULT_BALANCE, "signup")
        )
    else:
        cur.execute(
            "UPDATE users SET username=?, last_active=datetime('now') WHERE user_id=?",
            (username, user_id)
        )
    conn.commit()
    conn.close()

def freeze(user_id: int, amount: int, ref: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT available, frozen FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    if row["available"] < amount:
        raise HTTPException(400, "Insufficient balance")
    cur.execute(
        "UPDATE users SET available=available-?, frozen=frozen+?, last_active=datetime('now') WHERE user_id=?",
        (amount, amount, user_id)
    )
    cur.execute(
        "INSERT INTO ledger(tx_id, user_id, type, amount, ref) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), user_id, "FREEZE", amount, ref)
    )
    conn.commit()
    conn.close()

def unfreeze(user_id: int, amount: int, ref: str) -> None:
    """解冻用户资金"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT available, frozen FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    if row["frozen"] < amount:
        raise HTTPException(400, "Insufficient frozen balance")
    cur.execute(
        "UPDATE users SET available=available+?, frozen=frozen-?, last_active=datetime('now') WHERE user_id=?",
        (amount, amount, user_id)
    )
    cur.execute(
        "INSERT INTO ledger(tx_id, user_id, type, amount, ref) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), user_id, "UNFREEZE", amount, ref)
    )
    conn.commit()
    conn.close()

def transfer_frozen(from_user_id: int, to_user_id: int, amount: int, ref: str) -> None:
    """从一个用户的冻结资金转移到另一个用户的可用余额"""
    conn = get_conn()
    cur = conn.cursor()

    # 检查源用户冻结余额
    cur.execute("SELECT frozen FROM users WHERE user_id=?", (from_user_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Source user not found")
    if row["frozen"] < amount:
        raise HTTPException(400, "Insufficient frozen balance")

    # 扣除源用户冻结余额
    cur.execute(
        "UPDATE users SET frozen=frozen-?, last_active=datetime('now') WHERE user_id=?",
        (amount, from_user_id)
    )
    cur.execute(
        "INSERT INTO ledger(tx_id, user_id, type, amount, ref) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), from_user_id, "DEBIT", amount, ref)
    )

    # 增加目标用户可用余额
    cur.execute(
        "UPDATE users SET available=available+?, last_active=datetime('now') WHERE user_id=?",
        (amount, to_user_id)
    )
    cur.execute(
        "INSERT INTO ledger(tx_id, user_id, type, amount, ref) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), to_user_id, "CREDIT", amount, ref)
    )

    conn.commit()
    conn.close()

def cleanup_expired_rooms() -> int:
    """
    清理过期房间并退还押注
    返回清理的房间数量
    """
    conn = get_conn()
    cur = conn.cursor()

    # 查找所有过期的房间 (使用expires_at字段)
    cur.execute("""
        SELECT * FROM rooms
        WHERE status IN ('OPEN', 'FULL')
        AND datetime(expires_at) < datetime('now')
    """)

    expired_rooms = cur.fetchall()
    cleaned_count = 0

    for room in expired_rooms:
        try:
            # 退还房主押注
            unfreeze(room['host_id'], room['bet_amount'], ref=f"room:{room['room_id']}:expired")

            # 如果客人已加入,也退还客人押注
            if room['guest_id']:
                unfreeze(room['guest_id'], room['bet_amount'], ref=f"room:{room['room_id']}:expired")

            # 更新房间状态为CANCELLED
            cur.execute("UPDATE rooms SET status='CANCELLED' WHERE room_id=?", (room['room_id'],))
            cleaned_count += 1

            print(f"🧹 清理过期房间: {room['room_id']} (状态: {room['status']})")
        except Exception as e:
            print(f"❌ 清理房间 {room['room_id']} 失败: {e}")
            continue

    conn.commit()
    conn.close()

    return cleaned_count

async def periodic_cleanup():
    """定期清理过期房间的后台任务"""
    print("🚀 后台清理任务已启动")
    while True:
        try:
            await asyncio.sleep(30)  # 每30秒检查一次
            cleaned = cleanup_expired_rooms()
            if cleaned > 0:
                print(f"✅ 清理了 {cleaned} 个过期房间")
        except Exception as e:
            print(f"❌ 清理任务出错: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    init_db()
    global cleanup_task, bot_instance
    cleanup_task = asyncio.create_task(periodic_cleanup())

    # 设置 Telegram Webhook
    bot_instance = Bot(BOT_TOKEN)
    await bot_instance.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True
    )

    print("=" * 60)
    print("🎮 LGW33 API 服务已启动")
    print("=" * 60)
    print("✅ 数据库已初始化")
    print("✅ 后台清理任务已启动 (每30秒检查一次)")
    print("   - OPEN状态房间: 5分钟后自动关闭")
    print("   - FULL状态房间: 2分钟后自动关闭")
    print(f"✅ Telegram Webhook 已设置: {WEBHOOK_URL}")
    print("=" * 60)

    yield

    # 关闭时
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    # 删除 Webhook
    if bot_instance:
        await bot_instance.delete_webhook()
        await bot_instance.session.close()

    print("👋 LGW33 API 服务已关闭")

app = FastAPI(title="LGW33 PK MVP", lifespan=lifespan)

# --------------------
# Telegram Webhook
# --------------------
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """接收 Telegram Webhook 更新"""
    try:
        update_data = await request.json()
        update = Update(**update_data)

        # 使用全局 bot 实例处理更新
        if bot_instance:
            await dp.feed_update(bot_instance, update)

        return {"ok": True}
    except Exception as e:
        print(f"❌ Webhook 处理错误: {e}")
        return {"ok": False, "error": str(e)}

# --------------------
# Routes
# --------------------
@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, available, frozen FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Not found")
    return dict(row)

@app.post("/api/rooms")
def create_room(body: CreateRoomIn):
    # Debug/MVP: 先用 body.user 作为身份；上线后再换 WebApp initData 验签
    upsert_user(body.user.user_id, body.user.username)

    room_id = uuid.uuid4().hex[:12]
    invite_token = uuid.uuid4().hex  # 可以换成更短token
    # OPEN状态: 5分钟后过期
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # 冻结房主押注
    freeze(body.user.user_id, body.bet_amount, ref=f"room:{room_id}")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO rooms(room_id, chat_id, host_id, host_username, bet_amount, status, invite_token, expires_at)
           VALUES(?,?,?,?,?,?,?,?)""",
        (room_id, body.chat_id, body.user.user_id, body.user.username, body.bet_amount, "OPEN", invite_token, expires_at.isoformat())
    )
    conn.commit()
    conn.close()

    return {"room_id": room_id, "invite_token": invite_token, "bet_amount": body.bet_amount, "expires_at": expires_at.isoformat()}

@app.post("/api/rooms/{room_id}/share")
async def share_room(room_id: str, body: ShareRoomIn):
    upsert_user(body.user.user_id, body.user.username)

    # 使用默认群组ID（如果未提供）
    chat_id = body.chat_id if body.chat_id else DEFAULT_CHAT_ID
    if not chat_id:
        raise HTTPException(400, "No chat_id provided and no default chat_id configured")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,))
    room = cur.fetchone()
    conn.close()
    if not room:
        raise HTTPException(404, "Room not found")

    if room["host_id"] != body.user.user_id:
        raise HTTPException(403, "Only host can share")

    if room["status"] != "OPEN":
        raise HTTPException(400, "Room is not open")

    text = (
        f"⚔️ <b>点击PK挑战（30秒）</b>\n"
        f"🎫 押注：<b>{room['bet_amount']} LGW33</b>\n"
        f"发起人：@{room['host_username'] or '玩家'}\n\n"
        f"👇 点下面按钮加入房间挑战"
    )

    try:
        print(f"[DEBUG] Sending invite message to chat_id={chat_id}")
        await send_invite_message(
            bot_token=BOT_TOKEN,
            chat_id=chat_id,
            text=text,
            invite_token=room["invite_token"]
        )
        print(f"[DEBUG] Invite message sent successfully")
    except Exception as e:
        print(f"[ERROR] Failed to send invite message: {e}")
        raise HTTPException(500, f"Failed to send invite message: {str(e)}")

    # 记录 chat_id（方便后续播报）
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE rooms SET chat_id=? WHERE room_id=?", (chat_id, room_id))
    conn.commit()
    conn.close()

    return {"ok": True}

@app.get("/api/rooms/{room_id}")
def get_room(room_id: str):
    """获取房间完整状态"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,))
    room = cur.fetchone()
    conn.close()

    if not room:
        raise HTTPException(404, "Room not found")

    return dict(room)

@app.get("/api/rooms/open/list")
def get_open_rooms():
    """获取所有开放状态的房间列表"""
    conn = get_conn()
    cur = conn.cursor()

    # 查询所有OPEN和FULL状态的房间,按创建时间倒序
    cur.execute("""
        SELECT room_id, host_id, host_username, guest_id, guest_username,
               bet_amount, status, created_at, expires_at
        FROM rooms
        WHERE status IN ('OPEN', 'FULL')
        AND datetime(expires_at) > datetime('now')
        ORDER BY created_at DESC
        LIMIT 50
    """)

    rooms = cur.fetchall()
    conn.close()

    # 转换为字典列表，直接返回数组
    room_list = [dict(room) for room in rooms]

    return room_list

@app.get("/api/users/{user_id}/rooms")
def get_user_rooms(user_id: int):
    """获取用户当前参与的房间"""
    conn = get_conn()
    cur = conn.cursor()

    # 查询用户作为房主或客人的所有未结束房间
    cur.execute("""
        SELECT * FROM rooms
        WHERE (host_id=? OR guest_id=?)
        AND status NOT IN ('FINISHED', 'CANCELLED')
        ORDER BY created_at DESC
    """, (user_id, user_id))

    rooms = cur.fetchall()
    conn.close()

    # 转换为字典列表
    room_list = [dict(room) for room in rooms]

    return {"rooms": room_list, "count": len(room_list)}

class JoinRoomByIdIn(BaseModel):
    user: DebugUser

@app.post("/api/rooms/{room_id}/join")
def join_room_by_id(room_id: str, body: JoinRoomByIdIn):
    """用户通过房间ID加入房间（MiniApp使用）"""
    upsert_user(body.user.user_id, body.user.username)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,))
    room = cur.fetchone()
    if not room:
        conn.close()
        raise HTTPException(404, "Room not found")

    if room["status"] != "OPEN":
        conn.close()
        raise HTTPException(400, "Room not open")

    if room["host_id"] == body.user.user_id:
        conn.close()
        raise HTTPException(400, "Host cannot join own room")

    # 冻结挑战者押注
    freeze(body.user.user_id, room["bet_amount"], ref=f"room:{room_id}")

    # 加入房间，更新过期时间为2分钟后
    new_expires_at = datetime.utcnow() + timedelta(minutes=2)
    cur.execute(
        "UPDATE rooms SET guest_id=?, guest_username=?, status='FULL', expires_at=? WHERE room_id=?",
        (body.user.user_id, body.user.username, new_expires_at.isoformat(), room_id)
    )
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "room_id": room_id,
        "bet_amount": room["bet_amount"],
        "host_id": room["host_id"],
        "guest_id": body.user.user_id
    }

@app.post("/api/rooms/{room_id}/ready")
def ready_room(room_id: str, body: ReadyIn):
    """玩家点击Ready"""
    upsert_user(body.user.user_id, body.user.username)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,))
    room = cur.fetchone()

    if not room:
        conn.close()
        raise HTTPException(404, "Room not found")

    if room["status"] != "FULL":
        conn.close()
        raise HTTPException(400, "Room is not full")

    # 判断是房主还是客人
    if room["host_id"] == body.user.user_id:
        cur.execute("UPDATE rooms SET host_ready=1 WHERE room_id=?", (room_id,))
    elif room["guest_id"] == body.user.user_id:
        cur.execute("UPDATE rooms SET guest_ready=1 WHERE room_id=?", (room_id,))
    else:
        conn.close()
        raise HTTPException(403, "Not a player in this room")

    conn.commit()

    # 检查是否双方都Ready
    cur.execute("SELECT host_ready, guest_ready FROM rooms WHERE room_id=?", (room_id,))
    ready_status = cur.fetchone()

    both_ready = ready_status["host_ready"] == 1 and ready_status["guest_ready"] == 1

    if both_ready:
        # 双方都Ready，开始游戏
        game_start_time = datetime.utcnow().isoformat()
        cur.execute(
            "UPDATE rooms SET status='PLAYING', game_start_time=? WHERE room_id=?",
            (game_start_time, room_id)
        )
        conn.commit()

    conn.close()

    return {"ok": True, "both_ready": both_ready}

@app.post("/api/rooms/{room_id}/click")
def click_room(room_id: str, body: ClickIn):
    """记录玩家点击"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,))
    room = cur.fetchone()

    if not room:
        conn.close()
        raise HTTPException(404, "Room not found")

    if room["status"] != "PLAYING":
        conn.close()
        raise HTTPException(400, "Game is not playing")

    # 检查游戏是否超时（30秒）
    if room["game_start_time"]:
        start_time = datetime.fromisoformat(room["game_start_time"])
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        if elapsed > 30:
            conn.close()
            raise HTTPException(400, "Game time expired")

    # 判断是房主还是客人，增加点击数
    if room["host_id"] == body.user.user_id:
        cur.execute("UPDATE rooms SET host_clicks=host_clicks+1 WHERE room_id=?", (room_id,))
    elif room["guest_id"] == body.user.user_id:
        cur.execute("UPDATE rooms SET guest_clicks=guest_clicks+1 WHERE room_id=?", (room_id,))
    else:
        conn.close()
        raise HTTPException(403, "Not a player in this room")

    conn.commit()

    # 返回当前点击数
    cur.execute("SELECT host_clicks, guest_clicks FROM rooms WHERE room_id=?", (room_id,))
    clicks = cur.fetchone()
    conn.close()

    return {
        "ok": True,
        "host_clicks": clicks["host_clicks"],
        "guest_clicks": clicks["guest_clicks"]
    }

@app.post("/api/rooms/{room_id}/settle")
async def settle_room(room_id: str, body: DebugUser):
    """结算游戏（可由任一玩家或系统触发）"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,))
    room = cur.fetchone()

    if not room:
        conn.close()
        raise HTTPException(404, "Room not found")

    if room["status"] != "PLAYING":
        conn.close()
        raise HTTPException(400, "Game is not playing")

    # 检查游戏是否已经超过30秒
    if room["game_start_time"]:
        start_time = datetime.fromisoformat(room["game_start_time"])
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        if elapsed < 30:
            conn.close()
            raise HTTPException(400, f"Game not finished yet ({int(30-elapsed)}s remaining)")

    # 判断胜者
    host_clicks = room["host_clicks"]
    guest_clicks = room["guest_clicks"]
    bet_amount = room["bet_amount"]
    host_id = room["host_id"]
    guest_id = room["guest_id"]

    if host_clicks > guest_clicks:
        winner_id = host_id
        loser_id = guest_id
        winner_username = room["host_username"]
    elif guest_clicks > host_clicks:
        winner_id = guest_id
        loser_id = host_id
        winner_username = room["guest_username"]
    else:
        # 平局，双方退回押注
        winner_id = None
        loser_id = None
        winner_username = None

    game_end_time = datetime.utcnow().isoformat()

    # 更新房间状态
    cur.execute(
        "UPDATE rooms SET status='FINISHED', game_end_time=?, winner_id=? WHERE room_id=?",
        (game_end_time, winner_id, room_id)
    )
    conn.commit()
    conn.close()

    # 处理资金结算
    if winner_id is None:
        # 平局，双方解冻押注
        unfreeze(host_id, bet_amount, ref=f"room:{room_id}:draw")
        unfreeze(guest_id, bet_amount, ref=f"room:{room_id}:draw")
        result_text = "平局"
    else:
        # 有胜者，转移资金
        # 胜者：解冻自己的押注 + 获得对方的押注
        unfreeze(winner_id, bet_amount, ref=f"room:{room_id}:win")
        transfer_frozen(loser_id, winner_id, bet_amount, ref=f"room:{room_id}:win")
        result_text = f"@{winner_username} 获胜"

    # 发送结果到群聊
    if room["chat_id"]:
        result_message = (
            f"🎮 <b>游戏结束！</b>\n\n"
            f"🏆 结果：{result_text}\n"
            f"📊 点击数：\n"
            f"  • @{room['host_username']}: {host_clicks} 次\n"
            f"  • @{room['guest_username']}: {guest_clicks} 次\n"
            f"💰 押注：{bet_amount} LGW33"
        )

        try:
            await send_game_result(
                bot_token=BOT_TOKEN,
                chat_id=room["chat_id"],
                text=result_message
            )
        except Exception as e:
            print(f"Failed to send game result: {e}")

    return {
        "ok": True,
        "winner_id": winner_id,
        "host_clicks": host_clicks,
        "guest_clicks": guest_clicks,
        "result": result_text
    }

@app.post("/api/internal/init_user")
def internal_init_user(request: Request, body: InitUserIn):
    """初始化用户账户（Bot专用）"""
    require_internal(request)

    upsert_user(body.user_id, body.username)

    # 返回用户信息
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, available, frozen FROM users WHERE user_id=?", (body.user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, "User not found")

    return dict(row)

@app.post("/api/internal/join")
def internal_join_room(request: Request, body: JoinRoomIn):
    # 只允许 Bot 调用
    require_internal(request)

    upsert_user(body.user_id, body.username)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms WHERE invite_token=?", (body.invite_token,))
    room = cur.fetchone()
    if not room:
        conn.close()
        raise HTTPException(404, "Room not found")

    if room["status"] != "OPEN":
        conn.close()
        raise HTTPException(400, "Room not open")

    if room["host_id"] == body.user_id:
        conn.close()
        raise HTTPException(400, "Host cannot join own room")

    # 冻结挑战者押注
    freeze(body.user_id, room["bet_amount"], ref=f"room:{room['room_id']}")

    # 占位加入,并更新过期时间为2分钟后
    new_expires_at = datetime.utcnow() + timedelta(minutes=2)
    cur.execute(
        "UPDATE rooms SET guest_id=?, guest_username=?, status='FULL', expires_at=? WHERE room_id=?",
        (body.user_id, body.username, new_expires_at.isoformat(), room["room_id"])
    )
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "room_id": room["room_id"],
        "bet_amount": room["bet_amount"],
        "host_id": room["host_id"],
        "guest_id": body.user_id
    }

# --------------------
# Serve Mini App (static)
# --------------------
@app.get("/")
def root():
    """根路径重定向到 Mini App"""
    return RedirectResponse(url="/miniapp/index.html")

# 挂载整个 miniapp 目录为静态文件
miniapp_path = os.path.join(os.path.dirname(__file__), "..", "miniapp")
app.mount("/miniapp", StaticFiles(directory=miniapp_path, html=True), name="miniapp")
