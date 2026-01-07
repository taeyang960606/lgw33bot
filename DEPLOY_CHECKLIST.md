# 🚀 部署检查清单

## ✅ 已完成的准备工作

- [x] Procfile 已创建
- [x] .gitignore 已创建
- [x] API地址自动检测（本地/生产环境）
- [x] Telegram WebApp SDK 已集成
- [x] requirements.txt 已准备
- [x] .env.example 示例文件

## 📋 部署前需要的信息

请准备好以下信息：

1. **BOT_TOKEN**: `8505912875:AAHp36kZaRtz6c5puNKeZKkRugr8FwArusg`
2. **INTERNAL_API_KEY**: 建议改成更安全的，例如：`lgw33_secret_key_2024_render`
3. **DEFAULT_BALANCE**: `1000`
4. **DEFAULT_CHAT_ID**: `-5237867840`

## 🎯 部署步骤（Render.com）

### 步骤1: 推送代码到GitHub ✅
```bash
git init
git add .
git commit -m "Ready for deployment"
git branch -M main
git remote add origin https://github.com/taeyang960606/lgw33bot.git
git push -u origin main
```

### 步骤2: 在Render创建Web Service
1. 访问 https://render.com
2. 注册/登录账号
3. 点击 "New +" → "Web Service"
4. 连接GitHub仓库 `lgw33bot`
5. 配置如下：
   - **Name**: `lgw33-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`

### 步骤3: 添加环境变量
在 Render 的 Environment 标签页添加：
```
BOT_TOKEN=8505912875:AAHp36kZaRtz6c5puNKeZKkRugr8FwArusg
INTERNAL_API_KEY=lgw33_secret_key_2024_render
DEFAULT_BALANCE=1000
DEFAULT_CHAT_ID=-5237867840
```

### 步骤4: 部署
点击 "Create Web Service"，等待部署完成（约3-5分钟）

### 步骤5: 获取URL
部署成功后，会得到一个URL，例如：
```
https://lgw33-api.onrender.com
```

### 步骤6: 配置Telegram Bot
1. 与 @BotFather 对话
2. 发送 `/mybots`
3. 选择你的Bot
4. 选择 "Bot Settings" → "Menu Button"
5. 设置 Web App URL: `https://lgw33-api.onrender.com`

### 步骤7: 部署Bot服务（可选）
如果需要Bot自动运行：
1. 在Render创建 "Background Worker"
2. 使用相同的GitHub仓库
3. Start Command: `python -m bot.main`
4. 添加环境变量：
   ```
   BOT_TOKEN=8505912875:AAHp36kZaRtz6c5puNKeZKkRugr8FwArusg
   API_URL=https://lgw33-api.onrender.com
   INTERNAL_API_KEY=lgw33_secret_key_2024_render
   ```

## 🧪 测试

部署完成后：
1. 访问 `https://你的域名.onrender.com/api/health`
   - 应该返回 `{"ok": true}`
2. 在Telegram中打开Bot
3. 点击菜单按钮打开游戏
4. 测试创建房间、邀请好友、开始游戏

## ⚠️ 注意事项

1. **Render免费版限制**：
   - 15分钟不活动会休眠
   - 首次访问可能需要等待30秒唤醒
   - 每月750小时免费时长

2. **数据库**：
   - SQLite数据库在服务重启后会丢失
   - 建议后续升级到PostgreSQL

3. **Bot服务**：
   - 可以先不部署Bot Worker
   - 在本地运行Bot也可以（只要API在线）

## 🎉 完成！

部署成功后，您就可以在Telegram中使用真实的用户ID测试游戏了！

