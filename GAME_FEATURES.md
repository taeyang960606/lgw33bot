# LGW33 PK游戏功能说明

## 已实现的功能

### 1. 用户初始化机制 ✅
- **命令**: `/start`
- **功能**: 
  - 自动为用户创建账户
  - 分配1000 LGW33初始余额
  - 显示欢迎信息和游戏规则
- **实现位置**: 
  - `bot/main.py` - `/start`命令处理器
  - `bot/api_client.py` - `init_user()`函数
  - `api/main.py` - `/api/internal/init_user`接口

### 2. Ready机制 ✅
- **功能**:
  - 房间状态为FULL后，显示Ready按钮
  - 双方玩家需要点击Ready确认准备
  - 只有双方都Ready后，游戏才开始倒计时
  - 实时显示双方Ready状态
- **数据库字段**:
  - `rooms.host_ready` - 房主Ready状态
  - `rooms.guest_ready` - 客人Ready状态
- **实现位置**:
  - `api/db.py` - 数据库表结构
  - `api/main.py` - `/api/rooms/{room_id}/ready`接口
  - `miniapp/index.html` - Ready按钮和状态显示

### 3. PK游戏逻辑 ✅
- **游戏时长**: 30秒倒计时
- **玩法**: 双方玩家实时比赛点击次数
- **胜负判定**: 
  - 倒计时结束后，点击次数多的玩家获胜
  - 平局时双方退回押注
- **奖励分配**:
  - 获胜者获得双方押注总额
  - 失败者失去押注
  - 平局双方退回押注
- **数据库字段**:
  - `rooms.host_clicks` - 房主点击数
  - `rooms.guest_clicks` - 客人点击数
  - `rooms.game_start_time` - 游戏开始时间
  - `rooms.game_end_time` - 游戏结束时间
  - `rooms.winner_id` - 获胜者ID
- **实现位置**:
  - `api/main.py` - 点击计数、游戏结算接口
  - `miniapp/index.html` - 游戏界面、倒计时、点击按钮

### 4. 实时同步 ✅
- **功能**:
  - 每秒轮询房间状态
  - 实时更新双方点击数据
  - 自动切换游戏阶段（Ready → Playing → Finished）
- **实现位置**:
  - `miniapp/index.html` - `updateRoomStatus()`函数

### 5. 游戏结算 ✅
- **功能**:
  - 30秒后自动触发结算
  - 解冻双方押注
  - 转移资金给获胜者
  - 记录游戏结果
  - 在群聊中播报结果
- **实现位置**:
  - `api/main.py` - `/api/rooms/{room_id}/settle`接口
  - `api/tg_send.py` - `send_game_result()`函数

## 游戏流程

1. **用户注册**: 发送`/start`命令获得1000 LGW33初始余额
2. **创建房间**: 在MiniApp中创建房间并设置押注金额
3. **分享邀请**: 将房间邀请分享到群聊
4. **加入房间**: 其他玩家点击邀请按钮加入
5. **Ready阶段**: 双方在MiniApp中点击Ready按钮
6. **游戏开始**: 双方都Ready后，开始30秒倒计时
7. **疯狂点击**: 双方玩家疯狂点击按钮
8. **游戏结束**: 30秒后自动结算，显示结果
9. **结果播报**: 在群聊中播报游戏结果

## 房间状态流转

```
OPEN → FULL → PLAYING → FINISHED
  ↓      ↓       ↓         ↓
创建   加入    Ready    结算
```

## API接口列表

### 用户相关
- `POST /api/internal/init_user` - 初始化用户（Bot专用）
- `GET /api/users/{user_id}` - 获取用户信息

### 房间相关
- `POST /api/rooms` - 创建房间
- `GET /api/rooms/{room_id}` - 获取房间状态
- `POST /api/rooms/{room_id}/share` - 分享房间到群
- `POST /api/rooms/{room_id}/ready` - 玩家Ready
- `POST /api/rooms/{room_id}/click` - 记录点击
- `POST /api/rooms/{room_id}/settle` - 结算游戏
- `POST /api/internal/join` - 加入房间（Bot专用）

## 测试步骤

1. 启动API服务: `run_api.bat`
2. 启动Bot服务: `run_bot.bat`
3. 在Telegram中发送`/start`给Bot
4. 打开MiniApp: http://127.0.0.1:8000
5. 填写user_id和username
6. 创建房间并设置押注
7. 分享到群聊（需要群chat_id）
8. 另一个用户加入房间
9. 双方在MiniApp中进入房间
10. 双方点击Ready
11. 开始疯狂点击
12. 30秒后查看结果

## 注意事项

- 需要先删除旧的数据库文件`lgw33.db`以应用新的表结构
- 或者手动执行SQL添加新字段
- 确保`.env`文件中配置了正确的`BOT_TOKEN`和`INTERNAL_API_KEY`

