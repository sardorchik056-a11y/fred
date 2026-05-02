import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
import time
import requests
from datetime import datetime

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8096884868:AAGUq_yAyi24lWs_Dme7h5jXbcj0IomtRFs"  # Замени на свой токен
CRYPTOBOT_TOKEN = "552018:AAmEzVekZI0E1Qcpi0ccOxbkOMk01J2Qs2n"  # Токен от CryptoBot
ADMIN_ID = 8118184388  # Замени на свой Telegram ID

bot = telebot.TeleBot(BOT_TOKEN)

# Удаляем вебхук перед запуском
try:
    bot.remove_webhook()
    print("✅ Вебхук удалён")
except:
    pass
time.sleep(1)

# Файлы для хранения данных
USERS_FILE = "users.json"
PRODUCTS_FILE = "products.json"
PURCHASES_FILE = "purchases.json"

# Словарь для хранения состояний пользователей
user_states = {}

# ========== ИНИЦИАЛИЗАЦИЯ БАЗ ДАННЫХ ==========
def init_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    
    if not os.path.exists(PRODUCTS_FILE):
        default_products = {
            "web_token": {
                "name": "Web Token",
                "emoji": "🔑",
                "price": 2.50,
                "stock": 5,
                "description": "Токен доступа, готов к использованию"
            },
            "json": {
                "name": "JSON",
                "emoji": "📄",
                "price": 3.00,
                "stock": 4,
                "description": "Полные данные в JSON формате"
            },
            "autoreg": {
                "name": "Авторег",
                "emoji": "🤖",
                "price": 1.80,
                "stock": 3,
                "description": "Аккаунт зарегистрированный на SIM"
            }
        }
        with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_products, f, indent=4, ensure_ascii=False)
    
    if not os.path.exists(PURCHASES_FILE):
        with open(PURCHASES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def load_products():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=4, ensure_ascii=False)

def load_purchases():
    with open(PURCHASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_purchases(purchases):
    with open(PURCHASES_FILE, "w", encoding="utf-8") as f:
        json.dump(purchases, f, indent=4, ensure_ascii=False)

def register_user(user_id, username=None):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            "user_id": user_id,
            "username": username,
            "balance": 0.0,
            "total_bought": 0,
            "referrer_id": None,
            "referrals": [],
            "referral_earnings": 0.0,
            "is_banned": False,
            "registered_at": str(datetime.now())
        }
        save_users(users)

def add_balance(user_id, amount):
    users = load_users()
    if str(user_id) in users:
        users[str(user_id)]["balance"] += amount
        save_users(users)

def deduct_balance(user_id, amount):
    users = load_users()
    if str(user_id) in users and users[str(user_id)]["balance"] >= amount:
        users[str(user_id)]["balance"] -= amount
        save_users(users)
        return True
    return False

def get_user_balance(user_id):
    users = load_users()
    return users.get(str(user_id), {}).get("balance", 0)

# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========
def add_referral(user_id, referrer_id):
    users = load_users()
    referrer_id = str(referrer_id)
    user_id = str(user_id)
    
    if referrer_id in users and user_id not in users[referrer_id].get("referrals", []):
        users[referrer_id]["referrals"].append(user_id)
        save_users(users)

def add_referral_earning(user_id, amount):
    users = load_users()
    if str(user_id) in users:
        users[str(user_id)]["referral_earnings"] += amount
        users[str(user_id)]["balance"] += amount
        save_users(users)

# ========== КРИПТОПЛАТЕЖИ (CRYPTOBOT) ==========
def create_invoice(amount, user_id):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "asset": "USDT",
        "amount": str(amount),
        "description": f"Пополнение баланса бота. User ID: {user_id}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        if result.get("ok"):
            return result["result"]["bot_invoice_url"]
    except Exception as e:
        print(f"Ошибка создания инвойса: {e}")
    return None

# ========== КЛАВИАТУРЫ ==========
def main_menu_keyboard(user_id=None):
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("📦 Каталог", callback_data="catalog")
    btn2 = InlineKeyboardButton("💸 Реф. баланс", callback_data="referral")
    btn3 = InlineKeyboardButton("🆘 Поддержка", callback_data="support")
    btn4 = InlineKeyboardButton("📜 Оферта", callback_data="terms")
    btn5 = InlineKeyboardButton("💰 Баланс", callback_data="balance")
    keyboard.add(btn1, btn2, btn3, btn4, btn5)
    
    if user_id and str(user_id) == str(ADMIN_ID):
        btn_admin = InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")
        keyboard.add(btn_admin)
    
    return keyboard

def catalog_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("🔑 Web Token", callback_data="buy_web_token")
    btn2 = InlineKeyboardButton("📄 JSON", callback_data="buy_json")
    btn3 = InlineKeyboardButton("🤖 Авторег", callback_data="buy_autoreg")
    btn_back = InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
    keyboard.add(btn1, btn2, btn3)
    keyboard.add(btn_back)
    return keyboard

def admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("📦 Товары", callback_data="admin_products")
    btn2 = InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")
    btn3 = InlineKeyboardButton("💰 Пополнения", callback_data="admin_deposits")
    btn4 = InlineKeyboardButton("📢 Рассылка", callback_data="admin_mailing")
    btn5 = InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    btn6 = InlineKeyboardButton("⚠️ Бан пользователя", callback_data="admin_ban")
    btn_exit = InlineKeyboardButton("🔙 Выход", callback_data="back_to_menu")
    keyboard.add(btn1, btn2, btn3, btn4, btn5, btn6)
    keyboard.add(btn_exit)
    return keyboard

def admin_products_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn1 = InlineKeyboardButton("➕ Добавить товар", callback_data="add_product")
    btn2 = InlineKeyboardButton("✏️ Изменить товар", callback_data="edit_product")
    btn3 = InlineKeyboardButton("❌ Удалить товар", callback_data="delete_product")
    btn_back = InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
    keyboard.add(btn1, btn2, btn3, btn_back)
    return keyboard

def admin_users_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_list = InlineKeyboardButton("📋 Список пользователей", callback_data="admin_user_list")
    btn_find = InlineKeyboardButton("🔍 Найти пользователя", callback_data="admin_find_user")
    btn_back = InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
    keyboard.add(btn_list, btn_find, btn_back)
    return keyboard

def admin_deposits_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn_manual = InlineKeyboardButton("💰 Ручное зачисление", callback_data="admin_manual_deposit")
    btn_back = InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
    keyboard.add(btn_manual, btn_back)
    return keyboard

def get_profile_text(user_id, username=None):
    users = load_users()
    user_data = users.get(str(user_id), {})
    balance = user_data.get("balance", 0)
    total_bought = user_data.get("total_bought", 0)
    
    text = f"Добро пожаловать, @{username if username else 'Пользователь'}!\n\n"
    text += f"╭─────────────────\n"
    text += f"├ 👤 ID: {user_id}\n"
    text += f"├ 📦 Куплено: {total_bought} акков\n"
    text += f"├ 💰 Баланс: {balance}$\n"
    text += f"╰─────────────────\n\n"
    text += f"🎮 MAX | Главное меню\n\n"
    text += f"1 — Каталог\n"
    text += f"2 — Реф. баланс\n"
    text += f"3 — Поддержка\n"
    text += f"4 — Оферта\n"
    text += f"5 — Баланс"
    return text

# ========== ОТПРАВКА СООБЩЕНИЙ ==========
def send_main_menu(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    text = get_profile_text(user_id, username)
    
    try:
        if os.path.exists('welcome.jpg'):
            with open('welcome.jpg', 'rb') as photo:
                bot.send_photo(user_id, photo, caption=text, reply_markup=main_menu_keyboard(user_id))
        else:
            bot.send_message(user_id, text, reply_markup=main_menu_keyboard(user_id))
    except Exception as e:
        bot.send_message(user_id, text, reply_markup=main_menu_keyboard(user_id))

def edit_message(chat_id, message_id, text, reply_markup=None):
    try:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
    except:
        try:
            bot.send_message(chat_id, text, reply_markup=reply_markup)
        except:
            pass

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    register_user(user_id, username)
    
    users = load_users()
    if users.get(str(user_id), {}).get("is_banned", False):
        bot.send_message(user_id, "⛔ Вы заблокированы в этом боте!")
        return
    
    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]
        if referrer_id.isdigit() and int(referrer_id) != user_id:
            if referrer_id in users and str(user_id) not in users[referrer_id].get("referrals", []):
                add_referral(user_id, referrer_id)
                bot.send_message(user_id, f"✅ Вы были приглашены пользователем! При покупке он получит бонус.")
    
    send_main_menu(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    username = call.from_user.username
    message_id = call.message.message_id
    chat_id = call.message.chat.id
    
    users = load_users()
    if users.get(str(user_id), {}).get("is_banned", False) and call.data not in ["back_to_menu"]:
        bot.answer_callback_query(call.id, "⛔ Вы заблокированы!", show_alert=True)
        return
    
    # ========== ГЛАВНОЕ МЕНЮ ==========
    if call.data == "back_to_menu":
        text = get_profile_text(user_id, username)
        edit_message(chat_id, message_id, text, main_menu_keyboard(user_id))
        bot.answer_callback_query(call.id)
    
    elif call.data == "catalog":
        products = load_products()
        text = "📦 КАТАЛОГ\n\n"
        for key, product in products.items():
            text += f"{product['emoji']} {product['name']} ({product['stock']} шт | {product['price']}$)\n"
            text += f"   └ {product['description']}\n\n"
        text += "━━━━━━━━━━━━━━━\n\n"
        text += "Нажмите на кнопку ниже:"
        edit_message(chat_id, message_id, text, catalog_keyboard())
        bot.answer_callback_query(call.id)
    
    elif call.data == "referral":
        users_data = load_users()
        user_data = users_data.get(str(user_id), {})
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        
        text = "💸 РЕФЕРАЛЬНЫЙ БАЛАНС\n\n"
        text += f"Ваша реферальная ссылка:\n{ref_link}\n\n"
        text += "━━━━━━━━━━━━━━━\n\n"
        text += f"👥 Приглашено друзей: {len(user_data.get('referrals', []))}\n"
        text += f"💰 Заработано с рефералов: {user_data.get('referral_earnings', 0)}$\n"
        text += f"💎 Текущий баланс: {user_data.get('balance', 0)}$\n\n"
        text += "━━━━━━━━━━━━━━━\n\n"
        text += "🎁 Как это работает?\n"
        text += "За каждого друга, который купит аккаунт через вашу ссылку, вы получаете 10% от суммы покупки на баланс.\n\n"
        text += "💡 Пример:\n"
        text += "Друг купил Web Token за 2.50$ → вы получаете +0.25$\n\n"
        text += "━━━━━━━━━━━━━━━"
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        btn_copy = InlineKeyboardButton("🔗 Скопировать ссылку", callback_data="copy_ref_link")
        btn_list = InlineKeyboardButton("📊 Мои рефералы", callback_data="my_referrals")
        btn_back = InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
        keyboard.add(btn_copy, btn_list, btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
    
    elif call.data == "my_referrals":
        users_data = load_users()
        user_data = users_data.get(str(user_id), {})
        referrals = user_data.get("referrals", [])
        
        if not referrals:
            text = "📊 СПИСОК ВАШИХ РЕФЕРАЛОВ\n\n"
            text += "👥 Пока никого нет\n\n"
            text += "Пригласите друзей по вашей ссылке, и они появятся здесь!"
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            btn_copy = InlineKeyboardButton("🔗 Скопировать ссылку", callback_data="copy_ref_link")
            btn_back = InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
            keyboard.add(btn_copy, btn_back)
        else:
            text = "📊 СПИСОК ВАШИХ РЕФЕРАЛОВ\n\n"
            total_earned = 0
            purchases = load_purchases()
            
            for i, ref_id in enumerate(referrals[:10], 1):
                user_purchases = purchases.get(str(ref_id), [])
                total_spent = sum(p.get("amount", 0) for p in user_purchases)
                bonus = total_spent * 0.1
                total_earned += bonus
                ref_user = users_data.get(str(ref_id), {})
                ref_name = ref_user.get("username", f"ID{ref_id}")
                text += f"{i}. @{ref_name} — куплено: {len(user_purchases)} акков | {total_spent}$ → бонус: {bonus}$\n"
            
            text += "\n━━━━━━━━━━━━━━━\n"
            text += f"👥 Всего: {len(referrals)} рефералов\n"
            text += f"💰 Всего заработано: {total_earned}$"
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            btn_copy = InlineKeyboardButton("🔗 Пригласить ещё", callback_data="referral")
            btn_back = InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
            keyboard.add(btn_copy, btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
    
    elif call.data == "copy_ref_link":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        bot.answer_callback_query(call.id, f"Ваша ссылка: {ref_link}", show_alert=True)
    
    elif call.data == "support":
        text = "🆘 ПОДДЕРЖКА\n\nСвяжитесь с нами: @support_username"
        keyboard = InlineKeyboardMarkup()
        btn_back = InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
        keyboard.add(btn_back)
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
    
    elif call.data == "terms":
        text = """📜 ПРАВИЛА И ОФЕРТА

1️⃣ Токены НЕ хранятся заранее

Токены и данные берутся ТОЛЬКО в момент покупки (под выдачу).
После выдачи данные удаляются. Сохраните их сразу.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ Запрещено использовать аккаунты для мошенничества

• Не использовать для обмана людей
• Не использовать для фишинга
• Не использовать для спама
• Не нарушать законы РФ и вашей страны

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣ За нарушение правил аккаунт могут заблокировать

• Мошенничество → блокировка сразу (навсегда)
• Спам / фишинг → предупреждение, затем блокировка
• При блокировке деньги не возвращаются

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4️⃣ Замена авторегов в течение 5 часов

Если авторег оказался не валидным (нерабочим) — замена в течение 5 часов с момента покупки.

Для замены нужно отправить скриншот ошибки в поддержку.

Другие типы товаров (Web Token, JSON) замене не подлежат, если они были рабочими в момент выдачи.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5️⃣ Возврат денег

Возврат денег НЕ предусмотрен. Все товары — цифровые.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6️⃣ Ответственность

Мы НЕ несём ответственность за:
• Блокировку аккаунтов после покупки (ваши действия)
• Потерю данных пользователем
• Действия, совершённые с купленными аккаунтами

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7️⃣ Изменение правил

Правила могут меняться. Актуальная версия всегда здесь.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

8️⃣ Конфиденциальность

• Мы не передаём ваши данные (ID, username, история покупок) третьим лицам
• Данные о покупках хранятся только для решения спорных ситуаций
• Чат с поддержкой — конфиденциален

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

9️⃣ Один аккаунт бота — один человек

• Запрещено использовать несколько Telegram-аккаунтов для одного пользователя
• Запрещено создавать мультиаккаунты для получения реферальных бонусов
• За нарушение — блокировка всех аккаунтов

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔟 Минимальный возраст

Использование бота разрешено только лицам от 18 лет.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣1️⃣ Запрет на перепродажу

• Запрещено перепродавать купленные аккаунты третьим лицам
• Аккаунты предоставлены для личного использования

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣2️⃣ Техническая поддержка

• Время ответа поддержки: до 12 часов
• По выходным — до 24 часов
• Не нужно писать несколько раз подряд — это замедляет ответ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣3️⃣ Сохраняйте данные сразу

Мы НЕ храним токены и пароли после выдачи.
Восстановить потерянные данные НЕВОЗМОЖНО.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣4️⃣ Запрещённые действия в боте

Запрещено:
• Спамить командами (флуд)
• Отправлять запрещённый контент
• Оскорблять бота или поддержку
• Пытаться взломать или обмануть систему

За нарушение — блокировка без предупреждения.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣5️⃣ Согласие с правилами

Продолжая использовать бота, вы автоматически соглашаетесь со всеми текущими и будущими изменениями правил.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        btn_back = InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
        btn_agree = InlineKeyboardButton("✅ Согласен", callback_data="back_to_menu")
        keyboard.add(btn_agree, btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
    
    elif call.data == "balance":
        balance = get_user_balance(user_id)
        text = f"💰 ВАШ БАЛАНС\n\nТекущий баланс: {balance}$\n\nВыберите сумму для пополнения:"
        
        keyboard = InlineKeyboardMarkup(row_width=3)
        for amount in [5, 10, 25, 50]:
            keyboard.add(InlineKeyboardButton(f"{amount}$", callback_data=f"deposit_{amount}"))
        keyboard.add(InlineKeyboardButton("🔢 Другая сумма", callback_data="deposit_custom"))
        btn_back = InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
        keyboard.add(btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
    
    # ========== ПОКУПКА ТОВАРОВ ==========
    elif call.data.startswith("buy_"):
        product_key = call.data.replace("buy_", "")
        products = load_products()
        
        if product_key not in products:
            bot.answer_callback_query(call.id, "Товар не найден", show_alert=True)
            return
        
        product = products[product_key]
        balance = get_user_balance(user_id)
        
        text = f"{product['emoji']} {product['name']} | {product['price']}$ за шт\n\n"
        text += f"📦 В наличии: {product['stock']} шт\n"
        text += f"💰 Ваш баланс: {balance}$\n\n"
        text += "━━━━━━━━━━━━━━━\n\n"
        text += "Напишите количество аккаунтов, которое хотите купить:\n\n"
        text += "➡️ Например: 1"
        
        keyboard = InlineKeyboardMarkup()
        btn_back = InlineKeyboardButton("◀️ В каталог", callback_data="catalog")
        keyboard.add(btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
        
        user_states[user_id] = {"product_key": product_key, "product": product}
    
    # ========== ПОПОЛНЕНИЕ БАЛАНСА ==========
    elif call.data.startswith("deposit_"):
        if call.data == "deposit_custom":
            text = "💰 ПОПОЛНЕНИЕ БАЛАНСА\n\nВведите сумму от 5$ до 5000$:"
            edit_message(chat_id, message_id, text, None)
            bot.answer_callback_query(call.id)
            user_states[user_id] = {"awaiting_custom_deposit": True}
        else:
            amount = float(call.data.split("_")[1])
            process_payment(call.message.chat.id, user_id, amount)
            bot.answer_callback_query(call.id)
    
    # ========== АДМИН ПАНЕЛЬ ==========
    elif call.data == "admin_panel":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "👑 АДМИН ПАНЕЛЬ | MAX\n\nВыберите раздел:\n\n"
        text += "━━━━━━━━━━━━━━━\n\n"
        text += "1 — 📦 Товары (добавить/удалить/изменить)\n"
        text += "2 — 👥 Пользователи (просмотр/баланс/выдача)\n"
        text += "3 — 💰 Пополнения (ручное зачисление)\n"
        text += "5 — 📢 Рассылка\n"
        text += "6 — 📊 Статистика\n"
        text += "7 — ⚙️ бан\n\n"
        text += "━━━━━━━━━━━━━━━"
        
        edit_message(chat_id, message_id, text, admin_keyboard())
        bot.answer_callback_query(call.id)
    
    # ========== УПРАВЛЕНИЕ ТОВАРАМИ ==========
    elif call.data == "admin_products":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "📦 УПРАВЛЕНИЕ ТОВАРАМИ\n\nВыберите действие:"
        edit_message(chat_id, message_id, text, admin_products_keyboard())
        bot.answer_callback_query(call.id)
    
    elif call.data == "add_product":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "➕ ДОБАВЛЕНИЕ ТОВАРА\n\nВведите данные в формате:\n`id|название|цена|количество|эмодзи|описание`\n\nПример:\n`new_token|Новый Токен|5|10|⭐|Описание товара`"
        bot.send_message(user_id, text, parse_mode="Markdown")
        user_states[user_id] = {"awaiting_add_product": True}
        bot.answer_callback_query(call.id)
    
    elif call.data == "edit_product":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        products = load_products()
        text = "✏️ ИЗМЕНЕНИЕ ТОВАРА\n\nВыберите товар для изменения:\n\n"
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        for key, product in products.items():
            text += f"{product['emoji']} {product['name']} (ID: {key})\n"
            keyboard.add(InlineKeyboardButton(f"{product['emoji']} {product['name']}", callback_data=f"edit_select_{key}"))
        
        btn_back = InlineKeyboardButton("◀️ Назад", callback_data="admin_products")
        keyboard.add(btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("edit_select_"):
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        product_key = call.data.replace("edit_select_", "")
        user_states[user_id] = {"awaiting_edit_product": product_key}
        
        text = f"✏️ РЕДАКТИРОВАНИЕ ТОВАРА\n\nВведите новые данные в формате:\n`название|цена|количество|эмодзи|описание`\n\nПример:\n`Новый Токен|5|10|⭐|Новое описание`"
        bot.send_message(user_id, text, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
    
    elif call.data == "delete_product":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        products = load_products()
        text = "❌ УДАЛЕНИЕ ТОВАРА\n\nВыберите товар для удаления:\n\n"
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        for key, product in products.items():
            text += f"{product['emoji']} {product['name']} (ID: {key})\n"
            keyboard.add(InlineKeyboardButton(f"{product['emoji']} {product['name']}", callback_data=f"delete_select_{key}"))
        
        btn_back = InlineKeyboardButton("◀️ Назад", callback_data="admin_products")
        keyboard.add(btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("delete_select_"):
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        product_key = call.data.replace("delete_select_", "")
        products = load_products()
        
        if product_key in products:
            del products[product_key]
            save_products(products)
            bot.send_message(user_id, f"✅ Товар успешно удалён!")
        else:
            bot.send_message(user_id, f"❌ Товар не найден!")
        
        bot.answer_callback_query(call.id)
        
        text = "📦 УПРАВЛЕНИЕ ТОВАРАМИ\n\nВыберите действие:"
        edit_message(chat_id, message_id, text, admin_products_keyboard())
    
    # ========== ПОЛЬЗОВАТЕЛИ ==========
    elif call.data == "admin_users":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ\n\nВыберите действие:"
        edit_message(chat_id, message_id, text, admin_users_keyboard())
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_user_list":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        users_data = load_users()
        text = "📋 СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n\n"
        
        for i, (uid, u_data) in enumerate(list(users_data.items())[:20], 1):
            status = "🚫" if u_data.get("is_banned", False) else "✅"
            text += f"{i}. {status} ID: {uid} | @{u_data.get('username', 'нет')} | Баланс: {u_data.get('balance', 0)}$\n"
        
        text += f"\n━━━━━━━━━━━━━━━\n👥 Всего: {len(users_data)} пользователей"
        
        keyboard = InlineKeyboardMarkup()
        btn_back = InlineKeyboardButton("◀️ Назад", callback_data="admin_users")
        keyboard.add(btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_find_user":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "🔍 ПОИСК ПОЛЬЗОВАТЕЛЯ\n\nВведите ID или @username пользователя:"
        bot.send_message(user_id, text)
        user_states[user_id] = {"awaiting_find_user": True}
        bot.answer_callback_query(call.id)
    
    # ========== ПОПОЛНЕНИЯ ==========
    elif call.data == "admin_deposits":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "💰 УПРАВЛЕНИЕ ПОПОЛНЕНИЯМИ\n\nВыберите действие:"
        edit_message(chat_id, message_id, text, admin_deposits_keyboard())
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_manual_deposit":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "💰 РУЧНОЕ ЗАЧИСЛЕНИЕ\n\nВведите данные в формате:\n`ID пользователя|сумма`\n\nПример:\n`123456789|10`"
        bot.send_message(user_id, text, parse_mode="Markdown")
        user_states[user_id] = {"awaiting_manual_deposit": True}
        bot.answer_callback_query(call.id)
    
    # ========== РАССЫЛКА ==========
    elif call.data == "admin_mailing":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "📢 РАССЫЛКА\n\nВведите текст сообщения для рассылки всем пользователям:\n\n(Для отмены введите /cancel)"
        bot.send_message(user_id, text)
        user_states[user_id] = {"awaiting_mailing": True}
        bot.answer_callback_query(call.id)
    
    # ========== СТАТИСТИКА ==========
    elif call.data == "admin_stats":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        users_data = load_users()
        purchases = load_purchases()
        products = load_products()
        
        total_users = len(users_data)
        banned_users = sum(1 for u in users_data.values() if u.get("is_banned", False))
        total_purchases = sum(len(p) for p in purchases.values())
        total_income = sum(p.get("amount", 0) for p_list in purchases.values() for p in p_list)
        
        text = f"📊 СТАТИСТИКА\n\n"
        text += f"━━━━━━━━━━━━━━━\n"
        text += f"👥 Всего пользователей: {total_users}\n"
        text += f"🚫 Заблокировано: {banned_users}\n"
        text += f"📦 Всего покупок: {total_purchases}\n"
        text += f"💰 Общий доход: {total_income}$\n"
        text += f"━━━━━━━━━━━━━━━\n\n"
        text += f"📦 ОСТАТКИ ТОВАРОВ:\n"
        
        for key, product in products.items():
            text += f"{product['emoji']} {product['name']}: {product['stock']} шт\n"
        
        keyboard = InlineKeyboardMarkup()
        btn_back = InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
        keyboard.add(btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)
    
    # ========== БАН ПОЛЬЗОВАТЕЛЯ ==========
    elif call.data == "admin_ban":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "⚠️ БАН ПОЛЬЗОВАТЕЛЯ\n\nВведите ID пользователя для блокировки/разблокировки:\n\n(Для отмены введите /cancel)"
        bot.send_message(user_id, text)
        user_states[user_id] = {"awaiting_ban": True}
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("check_payment_"):
        amount = float(call.data.split("_")[2])
        add_balance(user_id, amount)
        
        text = f"✅ Баланс пополнен на {amount}$!\n\nТекущий баланс: {get_user_balance(user_id)}$"
        
        try:
            bot.edit_message_text(text, chat_id=user_id, message_id=message_id, reply_markup=None)
        except:
            bot.send_message(user_id, text)
        
        fake_message = type('obj', (object,), {'from_user': call.from_user, 'chat': call.message.chat})()
        send_main_menu(fake_message)
        bot.answer_callback_query(call.id, "Баланс пополнен!", show_alert=True)

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    
    if message.text == "/cancel":
        if user_id in user_states:
            del user_states[user_id]
            bot.send_message(user_id, "❌ Действие отменено")
            send_main_menu(message)
        return
    
    # Добавление товара
    if user_id in user_states and user_states[user_id].get("awaiting_add_product"):
        try:
            data = message.text.split("|")
            if len(data) >= 6:
                product_id = data[0].strip().lower().replace(" ", "_")
                name = data[1].strip()
                price = float(data[2].strip())
                stock = int(data[3].strip())
                emoji = data[4].strip()
                description = data[5].strip()
                
                products = load_products()
                products[product_id] = {
                    "name": name,
                    "emoji": emoji,
                    "price": price,
                    "stock": stock,
                    "description": description
                }
                save_products(products)
                bot.send_message(user_id, f"✅ Товар '{name}' успешно добавлен!")
            else:
                bot.send_message(user_id, "❌ Неверный формат! Используйте: id|название|цена|количество|эмодзи|описание")
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {e}")
        
        del user_states[user_id]
        send_main_menu(message)
        return
    
    # Редактирование товара
    if user_id in user_states and "awaiting_edit_product" in user_states[user_id]:
        product_key = user_states[user_id]["awaiting_edit_product"]
        try:
            data = message.text.split("|")
            if len(data) >= 5:
                name = data[0].strip()
                price = float(data[1].strip())
                stock = int(data[2].strip())
                emoji = data[3].strip()
                description = data[4].strip()
                
                products = load_products()
                if product_key in products:
                    products[product_key]["name"] = name
                    products[product_key]["price"] = price
                    products[product_key]["stock"] = stock
                    products[product_key]["emoji"] = emoji
                    products[product_key]["description"] = description
                    save_products(products)
                    bot.send_message(user_id, f"✅ Товар успешно изменён!")
                else:
                    bot.send_message(user_id, f"❌ Товар не найден!")
            else:
                bot.send_message(user_id, "❌ Неверный формат! Используйте: название|цена|количество|эмодзи|описание")
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {e}")
        
        del user_states[user_id]
        send_main_menu(message)
        return
    
    # Поиск пользователя
    if user_id in user_states and user_states[user_id].get("awaiting_find_user"):
        search = message.text.strip()
        users_data = load_users()
        
        found = None
        if search.isdigit():
            found = users_data.get(search)
        else:
            search_clean = search.replace("@", "")
            for uid, u_data in users_data.items():
                if u_data.get("username") == search_clean:
                    found = u_data
                    break
        
        if found:
            text = f"👤 ПОЛЬЗОВАТЕЛЬ НАЙДЕН\n\n"
            text += f"ID: {found.get('user_id')}\n"
            text += f"Username: @{found.get('username', 'нет')}\n"
            text += f"💰 Баланс: {found.get('balance', 0)}$\n"
            text += f"📦 Куплено: {found.get('total_bought', 0)} акков\n"
            text += f"👥 Рефералов: {len(found.get('referrals', []))}\n"
            text += f"💰 Реф. заработок: {found.get('referral_earnings', 0)}$\n"
            text += f"🚫 Статус: {'Заблокирован' if found.get('is_banned', False) else 'Активен'}\n"
            text += f"📅 Зарегистрирован: {found.get('registered_at', 'неизвестно')}"
        else:
            text = f"❌ Пользователь '{search}' не найден!"
        
        bot.send_message(user_id, text)
        del user_states[user_id]
        send_main_menu(message)
        return
    
    # Ручное зачисление
    if user_id in user_states and user_states[user_id].get("awaiting_manual_deposit"):
        try:
            data = message.text.split("|")
            target_id = int(data[0].strip())
            amount = float(data[1].strip())
            
            add_balance(target_id, amount)
            bot.send_message(user_id, f"✅ Пользователю ID:{target_id} зачислено {amount}$")
            
            try:
                bot.send_message(target_id, f"💰 Вам зачислено {amount}$ на баланс!\nТекущий баланс: {get_user_balance(target_id)}$")
            except:
                pass
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {e}")
        
        del user_states[user_id]
        send_main_menu(message)
        return
    
    # Рассылка
    if user_id in user_states and user_states[user_id].get("awaiting_mailing"):
        msg_text = message.text
        users_data = load_users()
        
        success = 0
        fail = 0
        
        bot.send_message(user_id, "📢 Начинаю рассылку...")
        
        for uid in users_data.keys():
            try:
                bot.send_message(int(uid), f"📢 РАССЫЛКА ОТ АДМИНА\n\n{msg_text}")
                success += 1
                time.sleep(0.05)
            except:
                fail += 1
        
        bot.send_message(user_id, f"✅ Рассылка завершена!\n📨 Доставлено: {success}\n❌ Ошибок: {fail}")
        del user_states[user_id]
        send_main_menu(message)
        return
    
    # Бан пользователя
    if user_id in user_states and user_states[user_id].get("awaiting_ban"):
        try:
            target_id = int(message.text.strip())
            users_data = load_users()
            
            if str(target_id) in users_data:
                current_status = users_data[str(target_id)].get("is_banned", False)
                new_status = not current_status
                users_data[str(target_id)]["is_banned"] = new_status
                save_users(users_data)
                
                status_text = "заблокирован" if new_status else "разблокирован"
                bot.send_message(user_id, f"✅ Пользователь ID:{target_id} {status_text}!")
                
                try:
                    bot.send_message(target_id, f"⛔ Вы были {status_text} в боте!" if new_status else f"✅ Вы были разблокированы в боте!")
                except:
                    pass
            else:
                bot.send_message(user_id, f"❌ Пользователь ID:{target_id} не найден!")
        except:
            bot.send_message(user_id, "❌ Введите корректный ID пользователя!")
        
        del user_states[user_id]
        send_main_menu(message)
        return

def process_payment(chat_id, user_id, amount):
    invoice_url = create_invoice(amount, user_id)
    
    if not invoice_url:
        bot.send_message(user_id, "❌ Ошибка создания платежа. Попробуйте позже.")
        return
    
    text = f"💰 ПОПОЛНЕНИЕ БАЛАНСА\n\n"
    text += f"Сумма: {amount}$\n"
    text += f"Оплатите по ссылке:\n{invoice_url}\n\n"
    text += "После оплаты нажмите 'Проверить оплату'"
    
    keyboard = InlineKeyboardMarkup()
    btn_check = InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_payment_{amount}")
    btn_back = InlineKeyboardButton("◀️ Назад", callback_data="balance")
    keyboard.add(btn_check, btn_back)
    
    bot.send_message(user_id, text, reply_markup=keyboard)

# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    init_files()
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН")
    print("=" * 50)
    print(f"✅ Токен бота: {BOT_TOKEN[:10]}...")
    print(f"👑 ID админа: {ADMIN_ID}")
    print(f"📁 Файлы: {USERS_FILE}, {PRODUCTS_FILE}, {PURCHASES_FILE}")
    print("=" * 50)
    print("🟢 Бот готов к работе!")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except KeyboardInterrupt:
            print("\n🔴 Бот остановлен")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
