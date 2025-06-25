# 🔐 Настройка OAuth 2.0 для Google Drive

Это руководство поможет вам настроить OAuth 2.0 аутентификацию, чтобы бот сохранял видео файлы на **ваш личный Google Drive** вместо сервисного аккаунта.

## 🎯 Преимущества OAuth 2.0

- ✅ Файлы сохраняются на **ваш личный Google Drive**
- ✅ **Неограниченное место** (по квоте вашего аккаунта)
- ✅ Полный контроль над файлами
- ✅ Можете легко найти и управлять файлами
- ✅ Не нужно создавать новые сервисные аккаунты

## 📋 Пошаговая инструкция

### Шаг 1: Создание OAuth 2.0 Credentials в Google Cloud Console

1. **Перейдите в Google Cloud Console:**
   ```
   https://console.cloud.google.com/
   ```

2. **Выберите или создайте проект:**
   - Если у вас уже есть проект для бота - используйте его
   - Если нет - создайте новый проект

3. **Включите Google Drive API:**
   - Перейдите в "APIs & Services" → "Library"
   - Найдите "Google Drive API"
   - Нажмите "Enable"

4. **Настройте OAuth consent screen:**
   - Перейдите в "APIs & Services" → "OAuth consent screen"
   - Выберите "External" (если у вас нет организации)
   - Заполните обязательные поля:
     - App name: `VideoSlicerBot`
     - User support email: ваш email
     - Developer contact: ваш email
   - Добавьте scope: `../auth/drive` (Google Drive API)
   - Сохраните

5. **Создайте OAuth 2.0 Credentials:**
   - Перейдите в "APIs & Services" → "Credentials"
   - Нажмите "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: "Web application"
   - Name: `VideoSlicerBot OAuth`
   - Authorized redirect URIs: `http://localhost:8080/callback`
   - Нажмите "Create"

6. **Скопируйте Client ID и Client Secret:**
   ```
   Client ID: something.apps.googleusercontent.com
   Client Secret: something_secret
   ```

### Шаг 2: Настройка переменных окружения

Добавьте эти переменные в ваш `.env` файл или в Railway:

```bash
# OAuth 2.0 Configuration
GOOGLE_OAUTH_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
```

### Шаг 3: Запуск процесса авторизации

#### Локально:

1. **Установите зависимости (если еще не установлены):**
   ```bash
   pip install -r requirements.txt
   ```

2. **Запустите скрипт настройки:**
   ```bash
   python setup_oauth.py
   ```

3. **Следуйте инструкциям:**
   - Скрипт откроет браузер с Google авторизацией
   - Войдите в ваш Google аккаунт
   - Дайте разрешения боту
   - Скопируйте URL redirect page и вставьте в терминал

#### На Railway:

1. **Добавьте переменные окружения в Railway:**
   ```
   GOOGLE_OAUTH_CLIENT_ID=your_client_id.apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
   ```

2. **Локально запустите авторизацию:**
   ```bash
   # Установите те же переменные локально
   export GOOGLE_OAUTH_CLIENT_ID="your_client_id.apps.googleusercontent.com"
   export GOOGLE_OAUTH_CLIENT_SECRET="your_client_secret"
   
   # Запустите скрипт
   python setup_oauth.py
   ```

3. **Загрузите токен на Railway:**
   - После успешной авторизации у вас появится файл `token.pickle`
   - Загрузите его на Railway (через Railway CLI или вручную)

### Шаг 4: Проверка настройки

```bash
# Проверьте статус аутентификации
python setup_oauth.py check
```

Вы должны увидеть:
```
✅ Используется OAuth 2.0 (ваш личный Google Drive)
```

## 🔧 Технические детали

### Как это работает:

1. **Первый запуск:** Бот использует OAuth credentials для получения access token
2. **Последующие запуски:** Бот автоматически обновляет токен при необходимости
3. **Сохранение файлов:** Файлы создаются в папках `VideoSlicerBot_taskID` на вашем Drive

### Файлы токенов:

- `token.pickle` - содержит access и refresh токены
- Автоматически обновляется при истечении
- Храните в безопасности

### Fallback:

Если OAuth не настроен, бот автоматически переключится на Service Account (если настроен).

## 🚨 Устранение проблем

### "Не найден код авторизации в URL"
- Убедитесь, что скопировали полный URL
- URL должен начинаться с `http://localhost:8080/callback?code=`

### "GOOGLE_OAUTH_CLIENT_ID must be set"
- Проверьте переменные окружения
- Убедитесь, что нет лишних пробелов

### "403 Forbidden" при загрузке
- Проверьте, что Google Drive API включен
- Убедитесь, что токен не истек (запустите `python setup_oauth.py check`)

### Токен истек
```bash
# Обновите токен
python setup_oauth.py
```

## 📁 Структура файлов на вашем Drive

После настройки OAuth ваши видео будут сохраняться так:

```
📁 Мой диск
  📁 VideoSlicerBot_abc123def
    🎥 fragment_001.mp4
    🎥 fragment_002.mp4
    🎥 fragment_003.mp4
  📁 VideoSlicerBot_xyz789uvw
    🎥 fragment_001.mp4
    🎥 fragment_002.mp4
```

Каждая задача создает отдельную папку с уникальным ID.

## ✅ Готово!

После настройки OAuth 2.0:
- Бот будет сохранять файлы на ваш личный Google Drive
- У вас будет полный контроль над файлами
- Проблема с квотой решена
- Файлы легко найти и скачать

---

**💡 Совет:** Сохраните Client ID и Client Secret в безопасном месте - они понадобятся для переустановки или обновления токенов. 