# Развёртывание бота на Oracle Cloud (Бесплатно)

## 1. Регистрация в Oracle Cloud
1. Перейдите на [oracle.com/cloud/free/](https://www.oracle.com/cloud/free/)
2. Нажмите **Start for free**
3. Заполните данные (паспорт, карта не списывается, проверка личности)
4. Подтвердите почту и телофон

## 2. Создание виртуальной машины (VM)
1. Войдите в [cloud.oracle.com](https://cloud.oracle.com)
2. Меню → **Compute** → **Instances**
3. Нажмите **Create instance**
4. Настройки:
   - **Name**: `telegram-bot`
   - **Image**: Ubuntu 22.04 (или новее)
   - **Shape**: **Ampere** (ARM) — **Always Free** (4 OCPU, 24GB RAM)
   - **Networking**: Поставьте галочку **Assign a public IP address**
   - **Add SSH keys**: Нажмите **Add SSH key** → **Generate key pair** (или загрузите свой открытый ключ)
5. Нажмите **Create**

## 3. Подключение к серверу по SSH
- Linux/Mac: `ssh ubuntu@<ваш-публичный-ip>`
- Windows: используйте **PuTTY** или **Windows Terminal** с той же командой

## 4. Загрузка файлов бота

### Вариант А: Через git (если репозиторий на GitHub)
```bash
sudo apt update && sudo apt install git -y
git clone https://github.com/ваш-репозиторий.git
cd telegram-shop-bot
```

### Вариант Б: Через SCP (с вашего компьютера)
На вашем компьютере (Windows PowerShell):
```powershell
scp -r C:\Users\123\Desktop\telegram-shop-bot ubuntu@<ip>:/home/ubuntu/
```

## 5. Настройка и запуск
```bash
# Установка зависимостей
sudo apt update
sudo apt install python3-pip git screen -y
pip3 install -r requirements.txt

# Настройка config.py (впишите токен бота и ID каналов)
nano config.py
# Или отредактируйте через SFTP

# Запуск в screen (чтобы работало после выхода)
screen -S bot_session
python3 bot.py
# Нажмите Ctrl+A, затем D (чтобы выйти из screen, но оставить бота работать)

# Вернуться к боту: screen -r bot_session
```

## 6. Проверка
1. Напишите `/start` боту
2. Если всё работает — бот будет работать 24/7 бесплатно

## Полезные команды
- Посмотреть логи: `screen -r bot_session`
- Перезапустить: `Ctrl+C` в screen, затем снова `python3 bot.py`
- Выйти из screen: `Ctrl+A, D`

## Примечание
- Oracle Cloud Free Tier **не требует карты для списания** (проверка только для личности)
- Вам дадут **200GB** дискового пространства (хватит для файлов бота)
- **4 ARM CPU + 24GB RAM** — этого более чем достаточно для одного бота
