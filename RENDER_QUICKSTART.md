# 🚀 Quick Deploy to Render

## 1-Click Deploy
1. Fork this repository
2. Go to [render.com](https://render.com)
3. Click "New" → "Blueprint"
4. Connect your GitHub repo
5. Render will auto-detect `render.yaml` and create all services

## Required Environment Variables
Set these in Render Dashboard:

### Main App (videobot-app):
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_IDS=your_telegram_id_here
GOOGLE_CREDENTIALS_JSON_CONTENT=your_google_credentials_json
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
```

### Worker (videobot-worker):
```
GOOGLE_CREDENTIALS_JSON_CONTENT=your_google_credentials_json
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
```

## What Gets Created:
- ✅ PostgreSQL Database (Free)
- ✅ Redis Cache (Free) 
- ✅ Web Service - Main Bot (Free)
- ✅ Background Worker - Celery (Free)

## Health Check:
`https://your-app-name.onrender.com/health`

## Bot Commands:
- `/status` - Check system status
- `/check_drive` - Check Google Drive integration

## Free Tier Limits:
- 750 hours/month per service
- Services sleep after 15min inactivity
- 30-60s cold start time

For detailed instructions see `RENDER_DEPLOYMENT.md`