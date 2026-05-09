# Инструкция: Загрузка на GitHub и развёртывание на Railway

## Часть 1: Загрузка проекта на GitHub

### 1.1 Создание репозитория на GitHub
1. Зайдите на [github.com](https://github.com) и нажмите **New repository**
2. Название: `telegram-shop-bot` (или любое)
3. Выберите **Public** (или Private, но тогда Railway нужно дать доступ)
4. НЕ СТАВЬТЕ галочку "Initialize this repository with a README"
5. Нажмите **Create repository**

### 1.2 Подготовка локальных файлов (на вашем ПК)
Откройте PowerShell в папке проекта:
```powershell
cd C:\Users\123\Desktop\telegram-shop-bot
```

Инициализируйте Git и сделайте первый коммит:
```powershell
git init
git add .
git commit -m "Initial commit: Telegram shop bot"
```

### 1.3 Загрузка на GitHub
Скопируйте URL вашего репозитория (например: `https://github.com/ваш-юзер/telegram-shop-bot.git`)

```powershell
git remote add origin https://github.com/ваш-юзер/telegram-shop-bot.git
git branch -M main
git push -u origin main
```

**Важно:** файл `.env` (если есть) и `config.py` с токеном бота НЕ грузятся (благодаря `.gitignore`). Токен будет указан в Railway.

---

## Часть 2: Развёртывание на Railway

### 2.1 Регистрация в Railway
1. Зайдите на [railway.app](https://railway.app)
2. Нажмите **Start a New Project**
3. Выберите **Login with GitHub**
4. Авторизуйте Railway в GitHub

### 2.2 Создание проекта
1. Выберите **Deploy from GitHub repo**
2. Выберите ваш репозиторий `telegram-shop-bot`
3. Railway автоматически определит, что это Python-проект

### 2.3 Настройка переменных окружения
В Railway перейдите в **Variables** и добавьте:

| Ключ | Значение |
|------|-----------|
| `BOT_Token` | `ваш_токен_бота` |
| `SUPPORT_ADMIN_ID` | `ваш_telegram_id` |
| `FREE_BUILD_TEXT` | `Выберите категорию сливов ниже.` |
| `WELCOME_TEXT` | `Добро пожаловать в бота DisSquad. Выберите нужный вам товар или слив:` |

*(Если в config.py есть другие переменные — добавьте их тоже)*

### 2.4 Настройка запуска
Railway обычно сам определяет команду запуска. Если нет:
1. Перейдите в **Settings** → **Deploy**
2. В **Custom Start Command** укажите:
   ```
   python3 bot.py
   ```
   *(Или `python bot.py`, зависит от настроек Railway)*

### 2.5 Проверка
1. Railway начнёт автоматическую сборку и запуск
2. В логах ( **Deployments** → **View Logs**) вы должны видеть:
   ```
   INFO:root:Starting polling...
   ```
3. Напишите `/start` вашему боту — он должен ответить!

---

## Полезные советы

### Бесплатный тариф Railway:
- **$5 бесплатно** при регистрации (можно использовать ~ 500 часов/месяц)
- После исчерпания лимита бот "засыпает", но просыпается при запросе
- Для 24/7 нужен платный тариф (от $5/месяц)

### Если нужны файлы (assets/, free/):
Railway имеет ограничения на размер файлов. Если файлы большие:
1. Используйте **Cloudflare R2** или **AWS S3** для хранения
2. В боте меняйте пути к файлам на URL хранилища

### Обновление бота:
После изменений на локальном ПК:
```powershell
git add .
git commit -m "Update bot"
git push origin main
```
Railway **автоматически** пересоберёт и перезапустит бота!

---

## Проблемы?
1. **Бот не запускается** → проверьте логи в Railway
2. **Ошибка токена** → проверьте переменную `BOT_Token` в Railway
3. **Файлы не находятся** → проверьте, что они загружены в GitHub (не в `.gitignore`)

**Удачи!** 🚂
