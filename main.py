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
    btn_exit = InlineKeyboardButton("🔙 Выход", callback_data="back_to_menu")
    keyboard.add(btn1, btn2, btn3, btn4, btn5)
    keyboard.add(btn_exit)
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
    
    # Пытаемся отправить с фото, если есть
    try:
        if os.path.exists('welcome.jpg'):
            with open('welcome.jpg', 'rb') as photo:
                bot.send_photo(user_id, photo, caption=text, reply_markup=main_menu_keyboard(user_id))
        else:
            bot.send_message(user_id, text, reply_markup=main_menu_keyboard(user_id))
    except Exception as e:
        bot.send_message(user_id, text, reply_markup=main_menu_keyboard(user_id))

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Безопасное редактирование сообщения"""
    try:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
    except Exception as e:
        # Если не можем отредактировать, отправляем новое
        bot.send_message(chat_id, text, reply_markup=reply_markup)

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    register_user(user_id, username)
    
    # Обработка реферальной ссылки
    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]
        if referrer_id.isdigit() and int(referrer_id) != user_id:
            users = load_users()
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
    
    # Главное меню
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
        users = load_users()
        user_data = users.get(str(user_id), {})
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
        users = load_users()
        user_data = users.get(str(user_id), {})
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
                # Получаем username реферала
                ref_user = users.get(str(ref_id), {})
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

2️⃣ Запрещено использовать аккаунты для мошенничества

3️⃣ За нарушение правил аккаунт могут заблокировать

4️⃣ Замена авторегов в течение 5 часов

5️⃣ Возврат денег НЕ предусмотрен

6️⃣ Ответственность на покупателе

7️⃣ Продолжая использовать бота, вы соглашаетесь с правилами"""
        
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
    
    # Покупка товаров
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
        
        # Сохраняем состояние
        user_states[user_id] = {"product_key": product_key, "product": product}
    
    # Пополнение баланса
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
    
    # Админ панель
    elif call.data == "admin_panel":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        
        text = "👑 АДМИН ПАНЕЛЬ | MAX\n\nВыберите раздел:\n\n"
        text += "━━━━━━━━━━━━━━━\n\n"
        text += "📦 Товары - управление\n"
        text += "👥 Пользователи - просмотр\n"
        text += "💰 Пополнения - выдача\n"
        text += "📢 Рассылка - сообщения\n"
        text += "📊 Статистика - отчёт"
        
        edit_message(chat_id, message_id, text, admin_keyboard())
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_products":
        text = "📦 Управление товарами\n\nЗдесь можно добавлять/редактировать товары"
        edit_message(chat_id, message_id, text, admin_products_keyboard())
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_stats":
        users = load_users()
        purchases = load_purchases()
        total_users = len(users)
        total_purchases = sum(len(p) for p in purchases.values())
        total_income = sum(p.get("amount", 0) for p_list in purchases.values() for p in p_list)
        
        text = f"📊 СТАТИСТИКА\n\n"
        text += f"👥 Всего пользователей: {total_users}\n"
        text += f"📦 Всего покупок: {total_purchases}\n"
        text += f"💰 Общий доход: {total_income}$"
        
        keyboard = InlineKeyboardMarkup()
        btn_back = InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
        keyboard.add(btn_back)
        
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)

def admin_products_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn1 = InlineKeyboardButton("➕ Добавить товар", callback_data="add_product")
    btn2 = InlineKeyboardButton("✏️ Изменить товар", callback_data="edit_product")
    btn3 = InlineKeyboardButton("❌ Удалить товар", callback_data="delete_product")
    btn_back = InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")
    keyboard.add(btn1, btn2, btn3, btn_back)
    return keyboard

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    
    # Проверяем, ждём ли мы количество для покупки
    if user_id in user_states and "product_key" in user_states[user_id]:
        state = user_states.pop(user_id)
        product_key = state["product_key"]
        product = state["product"]
        process_amount(message, product_key, product)
        return
    
    # Проверяем, ждём ли мы сумму для пополнения
    if user_id in user_states and user_states[user_id].get("awaiting_custom_deposit"):
        user_states.pop(user_id)
        process_custom_deposit(message)
        return
    
    # Если ничего не ждём, отправляем в главное меню
    send_main_menu(message)

def process_amount(message, product_key, product):
    user_id = message.from_user.id
    
    try:
        quantity = int(message.text.strip())
        if quantity <= 0 or quantity > 100:
            raise ValueError
    except:
        bot.send_message(user_id, "❌ Введите корректное число (от 1 до 100)")
        return
    
    if quantity > product["stock"]:
        bot.send_message(user_id, f"❌ В наличии только {product['stock']} шт")
        return
    
    total_price = quantity * product["price"]
    balance = get_user_balance(user_id)
    
    if balance < total_price:
        text = f"❌ Недостаточно средств\n\n"
        text += f"Вы запросили: {quantity} шт\n"
        text += f"Сумма: {total_price}$\n"
        text += f"Ваш баланс: {balance}$\n\n"
        text += f"Не хватает: {total_price - balance}$"
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        btn_pay = InlineKeyboardButton("💰 Пополнить", callback_data="balance")
        btn_back = InlineKeyboardButton("📦 Каталог", callback_data="catalog")
        keyboard.add(btn_pay, btn_back)
        
        bot.send_message(user_id, text, reply_markup=keyboard)
        return
    
    # Генерация данных (в реальном проекте здесь API для получения токенов)
    data_list = []
    for i in range(quantity):
        fake_data = f"{product['name']}_TOKEN_{user_id}_{int(time.time())}_{i+1}"
        data_list.append(fake_data)
    
    # Списываем баланс
    deduct_balance(user_id, total_price)
    
    # Добавляем бонус рефереру (10%)
    users = load_users()
    user_data = users.get(str(user_id), {})
    referrer_id = user_data.get("referrer_id")
    if referrer_id:
        bonus = total_price * 0.1
        add_referral_earning(referrer_id, bonus)
        bot.send_message(referrer_id, f"🎉 Ваш реферал совершил покупку!\n➕ Получено: {bonus}$")
    
    # Обновляем статистику покупок
    purchases = load_purchases()
    if str(user_id) not in purchases:
        purchases[str(user_id)] = []
    
    for data in data_list:
        purchases[str(user_id)].append({
            "product": product["name"],
            "quantity": 1,
            "amount": product["price"],
            "data": data,
            "time": str(datetime.now())
        })
    save_purchases(purchases)
    
    # Обновляем количество купленных аккаунтов
    users[str(user_id)]["total_bought"] = users[str(user_id)].get("total_bought", 0) + quantity
    save_users(users)
    
    # Уменьшаем остаток товара
    products = load_products()
    products[product_key]["stock"] -= quantity
    save_products(products)
    
    # Отправляем данные пользователю
    text = f"✅ Покупка успешна!\n\n"
    text += f"Товар: {product['emoji']} {product['name']}\n"
    text += f"Количество: {quantity} шт\n"
    text += f"Сумма: {total_price}$\n\n"
    text += f"━━━━━━━━━━━━━━━\n\n"
    text += f"📦 Ваши данные:\n"
    
    for i, data in enumerate(data_list, 1):
        text += f"{i}. {data}\n"
    
    text += f"\n━━━━━━━━━━━━━━━\n\n"
    text += "⚠️ Сохраните данные! Они не хранятся на сервере."
    
    bot.send_message(user_id, text)
    
    # Возвращаем в главное меню
    send_main_menu(message)

def process_payment(chat_id, user_id, amount):
    invoice_url = create_invoice(amount, user_id)
    
    if not invoice_url:
        bot.send_message(user_id, "❌ Ошибка создания платежа. Попробуйте позже.")
        return
    
    text = f"💰 ПОПОЛНЕНИЕ БАЛАНСА\n\n"
    text += f"Сумма: {amount}$\n"
    text += f"Оплатите по ссылке:\n{invoice_url}\n\n"
    text += "После оплаты напишите /start и нажмите 'Проверить оплату'"
    
    keyboard = InlineKeyboardMarkup()
    btn_check = InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_payment_{amount}")
    btn_back = InlineKeyboardButton("◀️ Назад", callback_data="balance")
    keyboard.add(btn_check, btn_back)
    
    bot.send_message(user_id, text, reply_markup=keyboard)

def process_custom_deposit(message):
    user_id = message.from_user.id
    
    try:
        amount = float(message.text.strip())
        if amount < 5 or amount > 5000:
            raise ValueError
    except:
        bot.send_message(user_id, "❌ Введите сумму от 5$ до 5000$")
        return
    
    process_payment(message.chat.id, user_id, amount)

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_payment_"))
def check_payment_callback(call):
    user_id = call.from_user.id
    amount = float(call.data.split("_")[2])
    
    # Добавляем баланс (в реальном проекте проверяем платеж через API)
    add_balance(user_id, amount)
    
    text = f"✅ Баланс пополнен на {amount}$!\n\nТекущий баланс: {get_user_balance(user_id)}$"
    
    try:
        bot.edit_message_text(text, chat_id=user_id, message_id=call.message.message_id, reply_markup=None)
    except:
        bot.send_message(user_id, text)
    
    # Отправляем главное меню
    fake_message = type('obj', (object,), {'from_user': call.from_user, 'chat': call.message.chat})()
    send_main_menu(fake_message)
    
    bot.answer_callback_query(call.id, "Баланс пополнен!", show_alert=True)

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
