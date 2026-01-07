import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from .api_client import join_room_as_user, init_user

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """处理/start命令，为用户初始化账户"""
    user = message.from_user
    username = user.username or user.full_name

    try:
        # 调用API初始化用户
        user_data = await init_user(user.id, username)

        welcome_text = (
            f"🎮 欢迎来到 LGW33 PK 游戏！\n\n"
            f"👤 用户: @{username}\n"
            f"💰 初始余额: {user_data['available']} LGW33\n\n"
            f"📖 游戏规则：\n"
            f"1️⃣ 创建房间并设置押注金额\n"
            f"2️⃣ 分享邀请链接给好友\n"
            f"3️⃣ 双方Ready后开始30秒点击PK\n"
            f"4️⃣ 点击次数多的玩家获胜并赢得全部押注\n\n"
            f"💡 使用 /chatid 获取群组ID用于分享房间"
        )

        await message.reply(welcome_text)
    except Exception as e:
        await message.reply(f"❌ 初始化失败: {str(e)}")

@dp.message(Command("chatid"))
async def cmd_chatid(message: Message):
    """获取当前聊天的 chat_id"""
    chat = message.chat
    chat_type = chat.type

    if chat_type == "private":
        text = (
            f"📱 私聊 Chat ID\n\n"
            f"Chat ID: `{chat.id}`\n"
            f"用户: {message.from_user.full_name}\n\n"
            f"💡 这是你的私聊 ID，可以用来测试"
        )
    elif chat_type in ["group", "supergroup"]:
        text = (
            f"👥 群组 Chat ID\n\n"
            f"Chat ID: `{chat.id}`\n"
            f"群名称: {chat.title}\n\n"
            f"💡 复制这个 ID 用于分享房间邀请"
        )
    else:
        text = f"Chat ID: `{chat.id}`\nType: {chat_type}"

    await message.reply(text, parse_mode="Markdown")

    # 同时在控制台打印
    print(f"\n{'='*60}")
    print(f"收到 /chatid 命令")
    print(f"Chat Type: {chat_type}")
    print(f"Chat ID: {chat.id}")
    if chat_type in ["group", "supergroup"]:
        print(f"群名称: {chat.title}")
    print(f"{'='*60}\n")

@dp.callback_query(F.data.startswith("join:"))
async def on_join(callback: CallbackQuery):
    invite_token = callback.data.split("join:", 1)[1].strip()
    user = callback.from_user
    username = user.username or (user.full_name if user.full_name else None)

    try:
        res = await join_room_as_user(invite_token, user.id, username)
        await callback.answer("加入成功 ✅", show_alert=False)

        # MVP：先简单回个群消息，表示已经占位加入
        await callback.message.reply(
            f"✅ @{user.username or user.full_name} 已加入挑战！\n"
            f"房间：{res['room_id']} | 押注：{res['bet_amount']} LGW33\n"
            f"下一步：在 Mini App 里进入房间 → Ready → 开始"
        )
    except Exception as e:
        await callback.answer("加入失败 ❌（余额不足/房间已满/已过期）", show_alert=True)

async def main():
    bot = Bot(BOT_TOKEN)
    print("=" * 60)
    print("🤖 LGW33 Bot 已启动")
    print("=" * 60)
    print(f"Bot 用户名: @lgw33tokenbot")
    print(f"\n💡 获取 chat_id 的方法：")
    print(f"   1. 私聊 Bot 发送: /chatid")
    print(f"   2. 在群里发送: /chatid")
    print(f"   3. Bot 会回复 chat_id\n")
    print("=" * 60)
    print("等待消息中...\n")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
