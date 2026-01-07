"""
游戏功能测试脚本
测试Ready机制和PK游戏逻辑
"""
import asyncio
import httpx
import time

API_URL = "http://127.0.0.1:8000"

# 测试用户
USER1 = {"user_id": 111111, "username": "player1"}
USER2 = {"user_id": 222222, "username": "player2"}

async def test_game_flow():
    print("=" * 70)
    print("开始测试游戏流程")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. 创建房间
        print("\n1️⃣ 玩家1创建房间...")
        r = await client.post(f"{API_URL}/api/rooms", json={
            "user": USER1,
            "bet_amount": 100,
            "chat_id": None
        })
        if not r.is_success:
            print(f"❌ 创建房间失败: {r.text}")
            return
        
        room_data = r.json()
        room_id = room_data["room_id"]
        invite_token = room_data["invite_token"]
        print(f"✅ 房间创建成功: {room_id}")
        print(f"   押注: {room_data['bet_amount']} LGW33")
        
        # 2. 玩家2加入房间
        print("\n2️⃣ 玩家2加入房间...")
        r = await client.post(f"{API_URL}/api/internal/join", 
            headers={"x-internal-key": "change_me"},
            json={
                "user_id": USER2["user_id"],
                "username": USER2["username"],
                "invite_token": invite_token
            }
        )
        if not r.is_success:
            print(f"❌ 加入房间失败: {r.text}")
            return
        print(f"✅ 玩家2加入成功")
        
        # 3. 检查房间状态
        print("\n3️⃣ 检查房间状态...")
        r = await client.get(f"{API_URL}/api/rooms/{room_id}")
        room = r.json()
        print(f"   状态: {room['status']}")
        print(f"   房主: @{room['host_username']}")
        print(f"   客人: @{room['guest_username']}")
        
        # 4. 玩家1 Ready
        print("\n4️⃣ 玩家1点击Ready...")
        r = await client.post(f"{API_URL}/api/rooms/{room_id}/ready", json={"user": USER1})
        if r.is_success:
            data = r.json()
            print(f"✅ 玩家1已Ready (双方都Ready: {data['both_ready']})")
        
        # 5. 玩家2 Ready
        print("\n5️⃣ 玩家2点击Ready...")
        r = await client.post(f"{API_URL}/api/rooms/{room_id}/ready", json={"user": USER2})
        if r.is_success:
            data = r.json()
            print(f"✅ 玩家2已Ready (双方都Ready: {data['both_ready']})")
            if data['both_ready']:
                print("🎮 游戏开始！")
        
        # 6. 模拟游戏过程（点击）
        print("\n6️⃣ 模拟游戏过程（5秒）...")
        start_time = time.time()
        
        # 玩家1点击10次
        for i in range(10):
            await client.post(f"{API_URL}/api/rooms/{room_id}/click", json={"user": USER1})
            await asyncio.sleep(0.1)
        
        # 玩家2点击15次
        for i in range(15):
            await client.post(f"{API_URL}/api/rooms/{room_id}/click", json={"user": USER2})
            await asyncio.sleep(0.1)
        
        # 7. 检查点击数
        print("\n7️⃣ 检查点击数...")
        r = await client.get(f"{API_URL}/api/rooms/{room_id}")
        room = r.json()
        print(f"   玩家1点击数: {room['host_clicks']}")
        print(f"   玩家2点击数: {room['guest_clicks']}")
        
        # 8. 等待游戏时间（模拟30秒，这里只等5秒用于测试）
        print("\n8️⃣ 等待游戏结束...")
        print("   (实际游戏需要等待30秒，这里为了测试快速结束)")
        
        # 手动修改游戏开始时间以便立即结算
        import sqlite3
        from datetime import datetime, timedelta
        conn = sqlite3.connect('lgw33.db')
        cur = conn.cursor()
        fake_start_time = (datetime.utcnow() - timedelta(seconds=31)).isoformat()
        cur.execute("UPDATE rooms SET game_start_time=? WHERE room_id=?", (fake_start_time, room_id))
        conn.commit()
        conn.close()
        print("   ⏰ 已模拟30秒过去")
        
        # 9. 结算游戏
        print("\n9️⃣ 结算游戏...")
        r = await client.post(f"{API_URL}/api/rooms/{room_id}/settle", json=USER1)
        if r.is_success:
            result = r.json()
            print(f"✅ 游戏结算完成")
            print(f"   结果: {result['result']}")
            print(f"   获胜者ID: {result['winner_id']}")
            print(f"   玩家1点击数: {result['host_clicks']}")
            print(f"   玩家2点击数: {result['guest_clicks']}")
        else:
            print(f"❌ 结算失败: {r.text}")
        
        # 10. 检查最终状态
        print("\n🔟 检查最终房间状态...")
        r = await client.get(f"{API_URL}/api/rooms/{room_id}")
        room = r.json()
        print(f"   状态: {room['status']}")
        print(f"   获胜者: {room['winner_id']}")
        
        # 11. 检查余额
        print("\n1️⃣1️⃣ 检查玩家余额...")
        r1 = await client.get(f"{API_URL}/api/users/{USER1['user_id']}")
        r2 = await client.get(f"{API_URL}/api/users/{USER2['user_id']}")
        
        if r1.is_success and r2.is_success:
            u1 = r1.json()
            u2 = r2.json()
            print(f"   玩家1余额: 可用={u1['available']}, 冻结={u1['frozen']}")
            print(f"   玩家2余额: 可用={u2['available']}, 冻结={u2['frozen']}")
    
    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_game_flow())

