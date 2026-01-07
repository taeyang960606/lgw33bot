import sqlite3

conn = sqlite3.connect('lgw33.db')
cur = conn.cursor()

print("=" * 70)
print("数据库状态")
print("=" * 70)

print("\n=== 用户 ===")
cur.execute('SELECT user_id, username, available, frozen FROM users')
users = cur.fetchall()
if users:
    for row in users:
        print(f"  user_id={row[0]}, username={row[1]}, available={row[2]}, frozen={row[3]}")
else:
    print("  (无用户)")

print("\n=== 房间 ===")
cur.execute('SELECT room_id, host_id, host_username, guest_id, guest_username, bet_amount, status FROM rooms')
rooms = cur.fetchall()
if rooms:
    for row in rooms:
        print(f"  room_id={row[0]}")
        print(f"    房主: {row[1]} ({row[2]})")
        print(f"    客人: {row[3]} ({row[4]})")
        print(f"    押注: {row[5]}, 状态: {row[6]}")
        print()
else:
    print("  (无房间)")

print("=== 账本 ===")
cur.execute('SELECT user_id, type, amount, ref FROM ledger ORDER BY created_at')
ledger = cur.fetchall()
if ledger:
    for row in ledger:
        print(f"  user_id={row[0]}, {row[1]}: {row[2]} ({row[3]})")
else:
    print("  (无记录)")

conn.close()
print("\n" + "=" * 70)

