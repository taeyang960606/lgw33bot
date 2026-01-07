"""
数据库迁移脚本 - 添加游戏相关字段
运行此脚本以更新现有数据库，添加Ready和游戏数据字段
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "lgw33.db"

def migrate():
    print("=" * 70)
    print("开始数据库迁移...")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 检查数据库是否存在
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'")
    if not cur.fetchone():
        print("❌ 数据库表不存在，请先运行API服务以初始化数据库")
        conn.close()
        return
    
    # 获取现有列
    cur.execute("PRAGMA table_info(rooms)")
    existing_columns = {row[1] for row in cur.fetchall()}
    
    # 需要添加的列
    new_columns = {
        'host_ready': 'INTEGER NOT NULL DEFAULT 0',
        'guest_ready': 'INTEGER NOT NULL DEFAULT 0',
        'host_clicks': 'INTEGER NOT NULL DEFAULT 0',
        'guest_clicks': 'INTEGER NOT NULL DEFAULT 0',
        'game_start_time': 'TEXT',
        'game_end_time': 'TEXT',
        'winner_id': 'INTEGER'
    }
    
    # 添加缺失的列
    added_count = 0
    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            try:
                cur.execute(f"ALTER TABLE rooms ADD COLUMN {col_name} {col_type}")
                print(f"✅ 添加列: {col_name}")
                added_count += 1
            except sqlite3.OperationalError as e:
                print(f"⚠️  列 {col_name} 可能已存在: {e}")
    
    # 更新status字段的注释（SQLite不支持修改注释，仅提示）
    print("\n📝 注意: rooms.status 现在支持以下状态:")
    print("   - OPEN: 等待玩家加入")
    print("   - FULL: 双方已加入，等待Ready")
    print("   - PLAYING: 游戏进行中")
    print("   - FINISHED: 游戏已结束")
    print("   - CANCELLED: 已取消")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 70)
    if added_count > 0:
        print(f"✅ 迁移完成！成功添加 {added_count} 个字段")
    else:
        print("✅ 数据库已是最新版本，无需迁移")
    print("=" * 70)

if __name__ == "__main__":
    migrate()

