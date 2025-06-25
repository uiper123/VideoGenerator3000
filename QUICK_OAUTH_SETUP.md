# 🚀 Быстрая настройка OAuth для решения проблемы с местом

**Проблема:** Сервисный аккаунт Google Drive переполнен (15GB квота исчерпана)  
**Решение:** Переключить бот на ваш личный Google Drive с OAuth 2.0

---

## ⚡ Быстрые шаги (5 минут)

### 1. Создайте OAuth credentials

1. Идите на https://console.cloud.google.com/
2. Выберите ваш проект для бота
3. "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
4. Application type: **Web application**
5. Authorized redirect URIs: `http://localhost:8080/callback`
6. Скопируйте **Client ID** и **Client Secret**

### 2. Добавьте переменные в Railway

```bash
GOOGLE_OAUTH_CLIENT_ID=ваш_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=ваш_client_secret
```

### 3. Запустите локальную авторизацию

```bash
# Установите переменные локально
export GOOGLE_OAUTH_CLIENT_ID="ваш_client_id.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="ваш_client_secret"

# Запустите скрипт авторизации
python setup_oauth.py
```

### 4. Загрузите токен на Railway

После успешной авторизации:
- У вас появится файл `token.pickle`
- Загрузите его на Railway (через Railway CLI или вручную)

### 5. Проверьте работу

```bash
python setup_oauth.py check
```

Должно показать: `✅ Используется OAuth 2.0 (ваш личный Google Drive)`

---

## 🎉 Готово!

Теперь бот будет сохранять видео на **ваш личный Google Drive** в папки вида `VideoSlicerBot_taskID`.

**Место:** Неограниченно (по квоте вашего аккаунта)  
**Контроль:** Полный доступ к файлам  
**Проблема решена:** ✅

---

📖 **Подробная инструкция:** [GOOGLE_DRIVE_OAUTH_SETUP.md](GOOGLE_DRIVE_OAUTH_SETUP.md) 