import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command

from .api_client import join_room_as_user, init_user

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://web-production-a95dc.up.railway.app")

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
            f"1️⃣ 点击下方按钮打开游戏\n"
            f"2️⃣ 创建房间并设置押注金额\n"
            f"3️⃣ 分享邀请链接给好友\n"
            f"4️⃣ 双方Ready后开始30秒点击PK\n"
            f"5️⃣ 点击次数多的玩家获胜并赢得全部押注\n\n"
            f"💡 使用 /chatid 获取群组ID用于分享房间"
        )

        # 创建 Web App 按钮
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎮 开始游戏",
                web_app=WebAppInfo(url=MINIAPP_URL)
            )],
            [InlineKeyboardButton(
                text="💰 查看余额",
                callback_data="check_balance"
            )]
        ])

        await message.reply(welcome_text, reply_markup=keyboard)
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

@dp.callback_query(F.data == "check_balance")
async def on_check_balance(callback: CallbackQuery):
    """处理查看余额按钮"""
    user = callback.from_user
    try:
        from .api_client import get_user_balance
        balance = await get_user_balance(user.id)
        await callback.answer(
            f"💰 当前余额: {balance['available']} LGW33\n"
            f"🔒 冻结: {balance['frozen']} LGW33",
            show_alert=True
        )
    except Exception as e:
        await callback.answer(f"❌ 查询失败: {str(e)}", show_alert=True)

@dp.callback_query(F.data.startswith("join:"))
async def on_join(callback: CallbackQuery):
    invite_token = callback.data.split("join:", 1)[1].strip()
    user = callback.from_user
    username = user.username or (user.full_name if user.full_name else None)

    try:
        # 调用API加入房间
        res = await join_room_as_user(invite_token, user.id, username)
        room_id = res['room_id']

        await callback.answer("加入成功 ✅", show_alert=False)

        # 生成带房间参数的MiniApp链接
        miniapp_url_with_room = f"{MINIAPP_URL}?room_id={room_id}"

        # 创建带MiniApp按钮的回复
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎮 进入房间开始游戏",
                web_app=WebAppInfo(url=miniapp_url_with_room)
            )]
        ])

        await callback.message.reply(
            f"✅ @{user.username or user.full_name} 已加入挑战！\n"
            f"房间：{res['room_id']} | 押注：{res['bet_amount']} LGW33\n\n"
            f"👇 点击下方按钮直接进入房间",
            reply_markup=keyboard
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
