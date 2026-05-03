import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
import time
import requests
import threading
from datetime import datetime

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8096884868:AAGUq_yAyi24lWs_Dme7h5jXbcj0IomtRFs"
CRYPTOBOT_TOKEN = "552018:AAmEzVekZI0E1Qcpi0ccOxbkOMk01J2Qs2n"
ADMIN_ID = 8118184388

bot = telebot.TeleBot(BOT_TOKEN)

try:
    bot.remove_webhook()
    print("✅ Вебхук удалён")
except:
    pass
time.sleep(1)

USERS_FILE = "users.json"
PRODUCTS_FILE = "products.json"
PURCHASES_FILE = "purchases.json"

user_states = {}

# Хранилище активных счетов: {invoice_id: {user_id, amount, message_id, chat_id}}
active_invoices = {}

# ========== ПРЕМИУМ ЭМОДЗИ ID ==========
EMOJI_CATALOG   = "5433658070094805716"
EMOJI_REFERRAL  = "5433698754199240073"
EMOJI_SUPPORT   = "5435879547940526151"
EMOJI_TERMS     = "5440539497383087970"
EMOJI_BALANCE   = "5433698017568549458"
EMOJI_BACK      = "5438249918978864300"
EMOJI_PAY       = "5432949633429597862"
EMOJI_CANCEL    = "5440660757194744323"
EMOJI_REF_LINK  = "5433698017568549458"
EMOJI_REF_STATS = "5434026073619227975"
EMOJI_HOME      = "5433931948782038025"
EMOJI_INVITE    = "5433658070094805716"
EMOJI_BUY       = "5440539497383087970"
EMOJI_DEPOSIT   = "5433698017568549458"
EMOJI_CUSTOM    = "5432949633429597862"
EMOJI_AGREE     = "5440539497383087970"


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
        users[str(user_id)]["balance"] = round(users[str(user_id)]["balance"] + amount, 2)
        save_users(users)


def deduct_balance(user_id, amount):
    users = load_users()
    if str(user_id) in users and users[str(user_id)]["balance"] >= amount:
        users[str(user_id)]["balance"] = round(users[str(user_id)]["balance"] - amount, 2)
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
        users[str(user_id)]["referral_earnings"] = round(
            users[str(user_id)]["referral_earnings"] + amount, 2)
        users[str(user_id)]["balance"] = round(
            users[str(user_id)]["balance"] + amount, 2)
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
        "description": f"Пополнение баланса. User ID: {user_id}",
        "expires_in": 3600
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        if result.get("ok"):
            inv = result["result"]
            return inv["invoice_id"], inv["bot_invoice_url"]
    except Exception as e:
        print(f"Ошибка создания инвойса: {e}")
    return None, None


def check_invoice_status(invoice_id):
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {"invoice_ids": str(invoice_id)}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        result = response.json()
        if result.get("ok"):
            items = result["result"].get("items", [])
            if items:
                return items[0].get("status")
    except Exception as e:
        print(f"Ошибка проверки инвойса: {e}")
    return None


# ========== АВТО-ПРОВЕРКА ОПЛАТЫ ==========
def payment_watcher():
    while True:
        time.sleep(3)
        if not active_invoices:
            continue

        to_remove = []
        for invoice_id, info in list(active_invoices.items()):
            try:
                status = check_invoice_status(invoice_id)
                if status == "paid":
                    uid = info["user_id"]
                    amount = info["amount"]
                    chat_id = info["chat_id"]
                    msg_id = info["message_id"]

                    add_balance(uid, amount)

                    users_data = load_users()
                    referrer_id = users_data.get(str(uid), {}).get("referrer_id")
                    if referrer_id:
                        bonus = round(amount * 0.1, 2)
                        add_referral_earning(referrer_id, bonus)
                        try:
                            bot.send_message(int(referrer_id),
                                f"🎁 Ваш реферал пополнил баланс на {amount}$!\n"
                                f"💰 Вам начислено: +{bonus}$")
                        except:
                            pass

                    text = (f"✅ Оплата подтверждена!\n\n"
                            f"Пополнено: {amount}$\n"
                            f"Текущий баланс: {get_user_balance(uid)}$")
                    try:
                        bot.edit_message_text(text, chat_id=chat_id,
                                              message_id=msg_id, reply_markup=None)
                    except:
                        try:
                            bot.send_message(chat_id, text)
                        except:
                            pass

                    to_remove.append(invoice_id)

                elif status in ("expired", None):
                    if status == "expired":
                        try:
                            bot.edit_message_text(
                                "⏰ Счёт истёк. Создайте новый через меню баланса.",
                                chat_id=info["chat_id"],
                                message_id=info["message_id"],
                                reply_markup=None
                            )
                        except:
                            pass
                        to_remove.append(invoice_id)
            except Exception as e:
                print(f"Ошибка watcher для инвойса {invoice_id}: {e}")

        for inv_id in to_remove:
            active_invoices.pop(inv_id, None)


# ========== КЛАВИАТУРЫ С ПРЕМИУМ ЭМОДЗИ ==========

def main_menu_keyboard(user_id=None):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📦 Каталог",     callback_data="catalog",  icon_custom_emoji_id=EMOJI_CATALOG),
        InlineKeyboardButton("💸 Реф. баланс", callback_data="referral", icon_custom_emoji_id=EMOJI_REFERRAL),
        InlineKeyboardButton("🆘 Поддержка",   callback_data="support",  icon_custom_emoji_id=EMOJI_SUPPORT),
        InlineKeyboardButton("📜 Оферта",      callback_data="terms",    icon_custom_emoji_id=EMOJI_TERMS),
        InlineKeyboardButton("💰 Баланс",      callback_data="balance",  icon_custom_emoji_id=EMOJI_BALANCE),
    )
    return keyboard


def catalog_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    products = load_products()
    for key, product in products.items():
        keyboard.add(InlineKeyboardButton(
            f"{product['emoji']} {product['name']} — {product['price']}$",
            callback_data=f"buy_{key}",
            icon_custom_emoji_id=EMOJI_CATALOG
        ))
    keyboard.add(InlineKeyboardButton(
        "◀️ Назад",
        callback_data="back_to_menu",
        icon_custom_emoji_id=EMOJI_BACK
    ))
    return keyboard


def admin_keyboard():
    # Админ панель — без премиум эмодзи
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📦 Товары",            callback_data="admin_products"),
        InlineKeyboardButton("👥 Пользователи",      callback_data="admin_users"),
        InlineKeyboardButton("💰 Пополнения",        callback_data="admin_deposits"),
        InlineKeyboardButton("📢 Рассылка",          callback_data="admin_mailing"),
        InlineKeyboardButton("📊 Статистика",        callback_data="admin_stats"),
        InlineKeyboardButton("⚠️ Бан пользователя", callback_data="admin_ban"),
        InlineKeyboardButton("🔙 Выход",             callback_data="back_to_menu")
    )
    return keyboard


def admin_products_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("➕ Добавить товар", callback_data="add_product"),
        InlineKeyboardButton("✏️ Изменить товар", callback_data="edit_product"),
        InlineKeyboardButton("❌ Удалить товар",  callback_data="delete_product"),
        InlineKeyboardButton("◀️ Назад",          callback_data="admin_panel")
    )
    return keyboard


def admin_users_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📋 Список пользователей", callback_data="admin_user_list"),
        InlineKeyboardButton("🔍 Найти пользователя",   callback_data="admin_find_user"),
        InlineKeyboardButton("◀️ Назад",                callback_data="admin_panel")
    )
    return keyboard


def admin_deposits_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💰 Ручное зачисление", callback_data="admin_manual_deposit"),
        InlineKeyboardButton("◀️ Назад",             callback_data="admin_panel")
    )
    return keyboard


def referral_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔗 Моя ссылка",   callback_data="copy_ref_link", icon_custom_emoji_id=EMOJI_REF_LINK),
        InlineKeyboardButton("📊 Мои рефералы", callback_data="my_referrals",  icon_custom_emoji_id=EMOJI_REF_STATS),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu",  icon_custom_emoji_id=EMOJI_HOME),
    )
    return keyboard


def my_referrals_keyboard(has_referrals=False):
    keyboard = InlineKeyboardMarkup(row_width=2)
    if not has_referrals:
        keyboard.add(
            InlineKeyboardButton("🔗 Моя ссылка",   callback_data="copy_ref_link", icon_custom_emoji_id=EMOJI_REF_LINK),
            InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu",  icon_custom_emoji_id=EMOJI_HOME),
        )
    else:
        keyboard.add(
            InlineKeyboardButton("🎁 Пригласить ещё", callback_data="referral",     icon_custom_emoji_id=EMOJI_INVITE),
            InlineKeyboardButton("🏠 Главное меню",   callback_data="back_to_menu", icon_custom_emoji_id=EMOJI_HOME),
        )
    return keyboard


def support_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        "◀️ Назад",
        callback_data="back_to_menu",
        icon_custom_emoji_id=EMOJI_BACK
    ))
    return keyboard


def terms_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Согласен", callback_data="back_to_menu", icon_custom_emoji_id=EMOJI_AGREE),
        InlineKeyboardButton("◀️ Назад",   callback_data="back_to_menu", icon_custom_emoji_id=EMOJI_BACK),
    )
    return keyboard


def balance_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    for amount in [5, 10, 25, 50]:
        keyboard.add(InlineKeyboardButton(
            f"💰 {amount}$",
            callback_data=f"deposit_{amount}",
            icon_custom_emoji_id=EMOJI_DEPOSIT
        ))
    keyboard.add(InlineKeyboardButton(
        "🔢 Другая сумма",
        callback_data="deposit_custom",
        icon_custom_emoji_id=EMOJI_CUSTOM
    ))
    keyboard.add(InlineKeyboardButton(
        "◀️ Назад",
        callback_data="back_to_menu",
        icon_custom_emoji_id=EMOJI_BACK
    ))
    return keyboard


def payment_keyboard(invoice_url):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить", url=invoice_url,               icon_custom_emoji_id=EMOJI_PAY),
        InlineKeyboardButton("❌ Отмена",   callback_data="cancel_payment", icon_custom_emoji_id=EMOJI_CANCEL),
    )
    return keyboard


def buy_product_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        "◀️ В каталог",
        callback_data="catalog",
        icon_custom_emoji_id=EMOJI_BACK
    ))
    return keyboard


def confirm_buy_keyboard(product_key, quantity, insufficient=False):
    keyboard = InlineKeyboardMarkup(row_width=2)
    if insufficient:
        keyboard.add(
            InlineKeyboardButton("💰 Пополнить баланс", callback_data="balance", icon_custom_emoji_id=EMOJI_BALANCE),
            InlineKeyboardButton("◀️ Каталог",          callback_data="catalog", icon_custom_emoji_id=EMOJI_BACK),
        )
    else:
        keyboard.add(
            InlineKeyboardButton("✅ Купить", callback_data=f"confirm_buy_{product_key}_{quantity}", icon_custom_emoji_id=EMOJI_BUY),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_buy",                            icon_custom_emoji_id=EMOJI_CANCEL),
        )
    return keyboard


def after_buy_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🆘 Поддержка",   callback_data="support",     icon_custom_emoji_id=EMOJI_SUPPORT),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu", icon_custom_emoji_id=EMOJI_HOME),
    )
    return keyboard


def cancel_buy_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📦 Каталог",      callback_data="catalog",     icon_custom_emoji_id=EMOJI_CATALOG),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu", icon_custom_emoji_id=EMOJI_HOME),
    )
    return keyboard


def cancel_payment_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💰 Баланс",       callback_data="balance",     icon_custom_emoji_id=EMOJI_BALANCE),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu", icon_custom_emoji_id=EMOJI_HOME),
    )
    return keyboard


def back_to_admin_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_panel"))
    return keyboard


def back_to_admin_users_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_users"))
    return keyboard


# ========== УТИЛИТЫ ==========
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
    text += f"1 — Каталог\n2 — Реф. баланс\n3 — Поддержка\n4 — Оферта\n5 — Баланс"
    return text


def send_main_menu(message):
    user_id = message.from_user.id
    username = message.from_user.username
    text = get_profile_text(user_id, username)
    try:
        if os.path.exists('welcome.jpg'):
            with open('welcome.jpg', 'rb') as photo:
                bot.send_photo(user_id, photo, caption=text,
                               reply_markup=main_menu_keyboard(user_id))
        else:
            bot.send_message(user_id, text, reply_markup=main_menu_keyboard(user_id))
    except Exception:
        bot.send_message(user_id, text, reply_markup=main_menu_keyboard(user_id))


def edit_message(chat_id, message_id, text, reply_markup=None):
    try:
        bot.edit_message_text(text, chat_id=chat_id,
                              message_id=message_id, reply_markup=reply_markup)
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

    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if (referrer_id.isdigit()
                and int(referrer_id) != user_id
                and referrer_id in users
                and str(user_id) not in users[referrer_id].get("referrals", [])
                and users[str(user_id)].get("referrer_id") is None):
            add_referral(user_id, referrer_id)
            users = load_users()
            users[str(user_id)]["referrer_id"] = referrer_id
            save_users(users)
            bot.send_message(user_id, "✅ Вы были приглашены! При покупке пригласивший получит бонус.")

    send_main_menu(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    username = call.from_user.username
    message_id = call.message.message_id
    chat_id = call.message.chat.id

    users = load_users()
    if users.get(str(user_id), {}).get("is_banned", False) and call.data != "back_to_menu":
        bot.answer_callback_query(call.id, "⛔ Вы заблокированы!", show_alert=True)
        return

    # ========== ГЛАВНОЕ МЕНЮ ==========
    if call.data == "back_to_menu":
        user_states.pop(user_id, None)
        text = get_profile_text(user_id, username)
        edit_message(chat_id, message_id, text, main_menu_keyboard(user_id))
        bot.answer_callback_query(call.id)

    elif call.data == "catalog":
        products = load_products()
        text = "📦 КАТАЛОГ\n\n"
        for key, product in products.items():
            stock_text = f"{product['stock']} шт" if product['stock'] > 0 else "❌ Нет в наличии"
            text += f"{product['emoji']} {product['name']} ({stock_text} | {product['price']}$)\n"
            text += f"   └ {product['description']}\n\n"
        text += "━━━━━━━━━━━━━━━\n\nНажмите на товар:"
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
        text += f"👥 Приглашено: {len(user_data.get('referrals', []))}\n"
        text += f"💰 Заработано: {user_data.get('referral_earnings', 0)}$\n"
        text += f"💎 Баланс: {user_data.get('balance', 0)}$\n\n"
        text += "━━━━━━━━━━━━━━━\n\n"
        text += "🎁 За каждую покупку реферала вы получаете 10% от суммы."

        edit_message(chat_id, message_id, text, referral_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "my_referrals":
        users_data = load_users()
        user_data = users_data.get(str(user_id), {})
        referrals = user_data.get("referrals", [])
        purchases = load_purchases()

        if not referrals:
            text = "📊 МОИ РЕФЕРАЛЫ\n\n👥 Пока никого нет\n\nПригласите друзей!"
            edit_message(chat_id, message_id, text, my_referrals_keyboard(has_referrals=False))
        else:
            text = "📊 МОИ РЕФЕРАЛЫ\n\n"
            for i, ref_id in enumerate(referrals[:10], 1):
                user_purchases = purchases.get(str(ref_id), [])
                total_spent = sum(p.get("amount", 0) for p in user_purchases)
                bonus = round(total_spent * 0.1, 2)
                ref_user = users_data.get(str(ref_id), {})
                ref_name = ref_user.get("username", f"ID{ref_id}")
                text += f"{i}. @{ref_name} — {len(user_purchases)} покупок | бонус: {bonus}$\n"
            text += f"\n━━━━━━━━━━━━━━━\n👥 Всего: {len(referrals)}"
            edit_message(chat_id, message_id, text, my_referrals_keyboard(has_referrals=True))
        bot.answer_callback_query(call.id)

    elif call.data == "copy_ref_link":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        bot.answer_callback_query(call.id, f"Ссылка: {ref_link}", show_alert=True)

    elif call.data == "support":
        text = "🆘 ПОДДЕРЖКА\n\nСвяжитесь с нами: @support_username"
        edit_message(chat_id, message_id, text, support_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "terms":
        text = """📜 ПРАВИЛА И ОФЕРТА

1️⃣ Токены НЕ хранятся заранее — берутся в момент покупки. Сохраните сразу.

━━━━━━━━━━━━━━━

2️⃣ Запрещено использовать для мошенничества, спама, фишинга.

━━━━━━━━━━━━━━━

3️⃣ За нарушение — блокировка без возврата средств.

━━━━━━━━━━━━━━━

4️⃣ Замена авторегов в течение 5 часов при наличии скриншота ошибки.

━━━━━━━━━━━━━━━

5️⃣ Возврат средств НЕ предусмотрен (цифровые товары).

━━━━━━━━━━━━━━━

6️⃣ Запрет перепродажи. Только личное использование.

━━━━━━━━━━━━━━━

7️⃣ Минимальный возраст — 18 лет.

━━━━━━━━━━━━━━━

8️⃣ Один Telegram-аккаунт — один пользователь.

━━━━━━━━━━━━━━━

Продолжая использовать бота, вы соглашаетесь с правилами."""
        edit_message(chat_id, message_id, text, terms_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "balance":
        balance = get_user_balance(user_id)
        text = f"💰 ВАШ БАЛАНС\n\nТекущий баланс: {balance}$\n\nВыберите сумму для пополнения:"
        edit_message(chat_id, message_id, text, balance_keyboard())
        bot.answer_callback_query(call.id)

    # ========== ПОКУПКА ТОВАРОВ ==========
    elif call.data.startswith("buy_"):
        product_key = call.data[4:]
        products = load_products()

        if product_key not in products:
            bot.answer_callback_query(call.id, "Товар не найден", show_alert=True)
            return

        product = products[product_key]

        if product["stock"] <= 0:
            bot.answer_callback_query(call.id, "❌ Товар закончился!", show_alert=True)
            return

        balance = get_user_balance(user_id)
        text = (f"{product['emoji']} {product['name']} | {product['price']}$ за шт\n\n"
                f"📦 В наличии: {product['stock']} шт\n"
                f"💰 Ваш баланс: {balance}$\n\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"Введите количество (1–{product['stock']}):\n➡️ Например: 1")

        edit_message(chat_id, message_id, text, buy_product_keyboard())
        bot.answer_callback_query(call.id)

        user_states[user_id] = {
            "awaiting_quantity": True,
            "product_key": product_key,
            "product": product,
            "chat_id": chat_id,
            "message_id": message_id
        }

    # ========== ПОДТВЕРЖДЕНИЕ ПОКУПКИ ==========
    elif call.data.startswith("confirm_buy_"):
        parts = call.data.split("_")
        product_key = parts[2]
        quantity = int(parts[3])
        products = load_products()

        if product_key not in products:
            bot.answer_callback_query(call.id, "Товар не найден", show_alert=True)
            return

        product = products[product_key]
        total_price = round(product["price"] * quantity, 2)
        balance = get_user_balance(user_id)

        if balance < total_price:
            bot.answer_callback_query(
                call.id,
                f"❌ Недостаточно средств! Нужно {total_price}$, у вас {balance}$",
                show_alert=True
            )
            return

        if product["stock"] < quantity:
            bot.answer_callback_query(
                call.id,
                f"❌ В наличии только {product['stock']} шт!",
                show_alert=True
            )
            return

        if not deduct_balance(user_id, total_price):
            bot.answer_callback_query(call.id, "❌ Ошибка списания средств!", show_alert=True)
            return

        products[product_key]["stock"] -= quantity
        save_products(products)

        purchases = load_purchases()
        if str(user_id) not in purchases:
            purchases[str(user_id)] = []
        purchases[str(user_id)].append({
            "product": product_key,
            "quantity": quantity,
            "amount": total_price,
            "date": str(datetime.now())
        })
        save_purchases(purchases)

        users_data = load_users()
        users_data[str(user_id)]["total_bought"] = (
            users_data[str(user_id)].get("total_bought", 0) + quantity
        )
        save_users(users_data)

        referrer_id = users_data.get(str(user_id), {}).get("referrer_id")
        if referrer_id:
            bonus = round(total_price * 0.1, 2)
            add_referral_earning(referrer_id, bonus)
            try:
                bot.send_message(int(referrer_id),
                    f"🎁 Ваш реферал купил {product['name']} x{quantity}!\n"
                    f"💰 Вам начислено: +{bonus}$")
            except:
                pass

        try:
            bot.send_message(ADMIN_ID,
                f"🛒 НОВАЯ ПОКУПКА!\n\n"
                f"👤 Пользователь: ID{user_id} @{username}\n"
                f"📦 Товар: {product['emoji']} {product['name']} x{quantity}\n"
                f"💰 Сумма: {total_price}$")
        except:
            pass

        text = (f"✅ ПОКУПКА УСПЕШНА!\n\n"
                f"Товар: {product['emoji']} {product['name']}\n"
                f"Количество: {quantity} шт\n"
                f"Сумма: {total_price}$\n"
                f"Остаток баланса: {get_user_balance(user_id)}$\n\n"
                f"Обратитесь в поддержку для получения товара.")

        edit_message(chat_id, message_id, text, after_buy_keyboard())
        bot.answer_callback_query(call.id, "✅ Покупка успешна!", show_alert=True)

    elif call.data.startswith("cancel_buy"):
        user_states.pop(user_id, None)
        edit_message(chat_id, message_id, "❌ Покупка отменена.", cancel_buy_keyboard())
        bot.answer_callback_query(call.id)

    # ========== ПОПОЛНЕНИЕ БАЛАНСА ==========
    elif call.data == "deposit_custom":
        text = "💰 ПОПОЛНЕНИЕ БАЛАНСА\n\nВведите сумму (от 1$ до 5000$):"
        bot.send_message(user_id, text)
        user_states[user_id] = {"awaiting_custom_deposit": True}
        bot.answer_callback_query(call.id)

    elif call.data.startswith("deposit_") and call.data != "deposit_custom":
        try:
            amount = float(call.data.split("_")[1])
        except (IndexError, ValueError):
            bot.answer_callback_query(call.id, "Ошибка суммы", show_alert=True)
            return
        process_payment(chat_id, user_id, amount, message_id)
        bot.answer_callback_query(call.id)

    elif call.data == "cancel_payment":
        to_remove = [inv_id for inv_id, info in active_invoices.items()
                     if info["user_id"] == user_id]
        for inv_id in to_remove:
            active_invoices.pop(inv_id, None)
        edit_message(chat_id, message_id, "❌ Платёж отменён.", cancel_payment_keyboard())
        bot.answer_callback_query(call.id)

    # ========== АДМИН ПАНЕЛЬ (без премиум эмодзи) ==========
    elif call.data == "admin_panel":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        text = ("👑 АДМИН ПАНЕЛЬ | MAX\n\n"
                "━━━━━━━━━━━━━━━\n\n"
                "1 — 📦 Товары\n2 — 👥 Пользователи\n"
                "3 — 💰 Пополнения\n4 — 📢 Рассылка\n"
                "5 — 📊 Статистика\n6 — ⚠️ Бан\n\n"
                "━━━━━━━━━━━━━━━")
        edit_message(chat_id, message_id, text, admin_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "admin_products":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        edit_message(chat_id, message_id,
                     "📦 УПРАВЛЕНИЕ ТОВАРАМИ\n\nВыберите действие:",
                     admin_products_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "add_product":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id,
            "➕ ДОБАВЛЕНИЕ ТОВАРА\n\nФормат:\n`id|название|цена|количество|эмодзи|описание`\n\n"
            "Пример:\n`new_token|Новый Токен|5|10|⭐|Описание`",
            parse_mode="Markdown")
        user_states[user_id] = {"awaiting_add_product": True}
        bot.answer_callback_query(call.id)

    elif call.data == "edit_product":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        products = load_products()
        keyboard = InlineKeyboardMarkup(row_width=1)
        text = "✏️ ИЗМЕНЕНИЕ ТОВАРА\n\nВыберите товар:\n\n"
        for key, product in products.items():
            text += f"{product['emoji']} {product['name']} (ID: {key}) — {product['stock']} шт\n"
            keyboard.add(InlineKeyboardButton(
                f"{product['emoji']} {product['name']}", callback_data=f"edit_select_{key}"))
        keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_products"))
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)

    elif call.data.startswith("edit_select_"):
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        product_key = call.data[12:]
        user_states[user_id] = {"awaiting_edit_product": product_key}
        bot.send_message(user_id,
            f"✏️ РЕДАКТИРОВАНИЕ: {product_key}\n\n"
            "Формат:\n`название|цена|количество|эмодзи|описание`\n\n"
            "Пример:\n`Новый Токен|5|10|⭐|Новое описание`",
            parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    elif call.data == "delete_product":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        products = load_products()
        keyboard = InlineKeyboardMarkup(row_width=1)
        text = "❌ УДАЛЕНИЕ ТОВАРА\n\nВыберите товар:\n\n"
        for key, product in products.items():
            text += f"{product['emoji']} {product['name']} (ID: {key})\n"
            keyboard.add(InlineKeyboardButton(
                f"❌ {product['emoji']} {product['name']}", callback_data=f"delete_select_{key}"))
        keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_products"))
        edit_message(chat_id, message_id, text, keyboard)
        bot.answer_callback_query(call.id)

    elif call.data.startswith("delete_select_"):
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        product_key = call.data[14:]
        products = load_products()
        if product_key in products:
            del products[product_key]
            save_products(products)
            bot.send_message(user_id, f"✅ Товар удалён!")
        else:
            bot.send_message(user_id, "❌ Товар не найден!")
        bot.answer_callback_query(call.id)
        edit_message(chat_id, message_id,
                     "📦 УПРАВЛЕНИЕ ТОВАРАМИ\n\nВыберите действие:",
                     admin_products_keyboard())

    elif call.data == "admin_users":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        edit_message(chat_id, message_id,
                     "👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ\n\nВыберите действие:",
                     admin_users_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "admin_user_list":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        users_data = load_users()
        text = "📋 СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n\n"
        for i, (uid, u_data) in enumerate(list(users_data.items())[:20], 1):
            status = "🚫" if u_data.get("is_banned", False) else "✅"
            text += (f"{i}. {status} ID:{uid} | "
                     f"@{u_data.get('username', 'нет')} | "
                     f"Баланс: {u_data.get('balance', 0)}$\n")
        text += f"\n━━━━━━━━━━━━━━━\n👥 Всего: {len(users_data)}"
        edit_message(chat_id, message_id, text, back_to_admin_users_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "admin_find_user":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id, "🔍 Введите ID или @username:")
        user_states[user_id] = {"awaiting_find_user": True}
        bot.answer_callback_query(call.id)

    elif call.data == "admin_deposits":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        edit_message(chat_id, message_id,
                     "💰 УПРАВЛЕНИЕ ПОПОЛНЕНИЯМИ\n\nВыберите действие:",
                     admin_deposits_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "admin_manual_deposit":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id,
            "💰 РУЧНОЕ ЗАЧИСЛЕНИЕ\n\nФормат:\n`ID|сумма`\n\nПример:\n`123456789|10`",
            parse_mode="Markdown")
        user_states[user_id] = {"awaiting_manual_deposit": True}
        bot.answer_callback_query(call.id)

    elif call.data == "admin_mailing":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id, "📢 Введите текст рассылки:\n\n(Для отмены: /cancel)")
        user_states[user_id] = {"awaiting_mailing": True}
        bot.answer_callback_query(call.id)

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

        text = (f"📊 СТАТИСТИКА\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👥 Пользователей: {total_users}\n"
                f"🚫 Заблокировано: {banned_users}\n"
                f"📦 Покупок: {total_purchases}\n"
                f"💰 Доход: {round(total_income, 2)}$\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"📦 ОСТАТКИ:\n")
        for key, product in products.items():
            text += f"{product['emoji']} {product['name']}: {product['stock']} шт\n"

        edit_message(chat_id, message_id, text, back_to_admin_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "admin_ban":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id,
            "⚠️ БАН/РАЗБАН\n\nВведите ID пользователя:\n\n(Для отмены: /cancel)")
        user_states[user_id] = {"awaiting_ban": True}
        bot.answer_callback_query(call.id)

    else:
        bot.answer_callback_query(call.id)


# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""

    if text == "/cancel":
        user_states.pop(user_id, None)
        bot.send_message(user_id, "❌ Действие отменено")
        send_main_menu(message)
        return

    state = user_states.get(user_id, {})

    # ===== Ввод количества товара при покупке =====
    if state.get("awaiting_quantity"):
        product_key = state["product_key"]
        product = state["product"]
        chat_id = state.get("chat_id", user_id)
        msg_id = state.get("message_id")

        if not text.isdigit() or int(text) <= 0:
            bot.send_message(user_id, "❌ Введите целое положительное число!")
            return

        quantity = int(text)
        products = load_products()
        product = products.get(product_key, product)

        if quantity > product["stock"]:
            bot.send_message(user_id, f"❌ В наличии только {product['stock']} шт!")
            return

        total_price = round(product["price"] * quantity, 2)
        balance = get_user_balance(user_id)

        confirm_text = (
            f"🛒 ПОДТВЕРЖДЕНИЕ ПОКУПКИ\n\n"
            f"Товар: {product['emoji']} {product['name']}\n"
            f"Количество: {quantity} шт\n"
            f"Цена за шт: {product['price']}$\n"
            f"Итого: {total_price}$\n\n"
            f"💰 Ваш баланс: {balance}$\n"
            f"💰 После покупки: {round(balance - total_price, 2)}$\n\n"
        )

        insufficient = balance < total_price
        if insufficient:
            confirm_text += f"❌ Недостаточно средств! Нужно ещё {round(total_price - balance, 2)}$"
        else:
            confirm_text += "Подтвердить покупку?"

        del user_states[user_id]

        try:
            if msg_id:
                bot.edit_message_text(confirm_text, chat_id=chat_id, message_id=msg_id,
                                      reply_markup=confirm_buy_keyboard(product_key, quantity, insufficient))
            else:
                bot.send_message(user_id, confirm_text,
                                 reply_markup=confirm_buy_keyboard(product_key, quantity, insufficient))
        except:
            bot.send_message(user_id, confirm_text,
                             reply_markup=confirm_buy_keyboard(product_key, quantity, insufficient))
        return

    # ===== Произвольная сумма пополнения =====
    if state.get("awaiting_custom_deposit"):
        try:
            amount = float(text.replace(",", "."))
            if amount < 1 or amount > 5000:
                bot.send_message(user_id, "❌ Сумма должна быть от 1$ до 5000$")
                return
            del user_states[user_id]
            process_payment(message.chat.id, user_id, amount, None)
        except ValueError:
            bot.send_message(user_id, "❌ Введите числовую сумму (например: 15.50)")
        return

    # ===== Добавление товара =====
    if state.get("awaiting_add_product"):
        try:
            data = [d.strip() for d in text.split("|")]
            if len(data) < 6:
                raise ValueError("Недостаточно полей")
            product_id = data[0].lower().replace(" ", "_")
            name, price, stock, emoji, description = (
                data[1], float(data[2]), int(data[3]), data[4], data[5])
            products = load_products()
            products[product_id] = {
                "name": name, "emoji": emoji,
                "price": price, "stock": stock, "description": description
            }
            save_products(products)
            bot.send_message(user_id, f"✅ Товар '{name}' добавлен!")
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {e}\n\nФормат: id|название|цена|кол-во|эмодзи|описание")
        del user_states[user_id]
        send_main_menu(message)
        return

    # ===== Редактирование товара =====
    if "awaiting_edit_product" in state:
        product_key = state["awaiting_edit_product"]
        try:
            data = [d.strip() for d in text.split("|")]
            if len(data) < 5:
                raise ValueError("Недостаточно полей")
            name, price, stock, emoji, description = (
                data[0], float(data[1]), int(data[2]), data[3], data[4])
            products = load_products()
            if product_key in products:
                products[product_key].update({
                    "name": name, "price": price,
                    "stock": stock, "emoji": emoji, "description": description
                })
                save_products(products)
                bot.send_message(user_id, f"✅ Товар обновлён!")
            else:
                bot.send_message(user_id, "❌ Товар не найден!")
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {e}\n\nФормат: название|цена|кол-во|эмодзи|описание")
        del user_states[user_id]
        send_main_menu(message)
        return

    # ===== Поиск пользователя =====
    if state.get("awaiting_find_user"):
        search = text.replace("@", "")
        users_data = load_users()
        found = None
        found_id = None

        if search.isdigit():
            found = users_data.get(search)
            found_id = search
        else:
            for uid, u_data in users_data.items():
                if u_data.get("username", "").lower() == search.lower():
                    found = u_data
                    found_id = uid
                    break

        if found:
            result = (f"👤 ПОЛЬЗОВАТЕЛЬ НАЙДЕН\n\n"
                      f"ID: {found.get('user_id')}\n"
                      f"Username: @{found.get('username', 'нет')}\n"
                      f"💰 Баланс: {found.get('balance', 0)}$\n"
                      f"📦 Куплено: {found.get('total_bought', 0)} акков\n"
                      f"👥 Рефералов: {len(found.get('referrals', []))}\n"
                      f"💰 Реф. заработок: {found.get('referral_earnings', 0)}$\n"
                      f"🚫 Статус: {'Заблокирован' if found.get('is_banned') else 'Активен'}\n"
                      f"📅 Зарегистрирован: {found.get('registered_at', 'неизвестно')}")
        else:
            result = f"❌ Пользователь '{text}' не найден!"

        bot.send_message(user_id, result)
        del user_states[user_id]
        send_main_menu(message)
        return

    # ===== Ручное зачисление =====
    if state.get("awaiting_manual_deposit"):
        try:
            parts = text.split("|")
            target_id = int(parts[0].strip())
            amount = float(parts[1].strip())
            add_balance(target_id, amount)
            bot.send_message(user_id, f"✅ Зачислено {amount}$ пользователю ID:{target_id}")
            try:
                bot.send_message(target_id,
                    f"💰 Вам зачислено {amount}$!\n"
                    f"Текущий баланс: {get_user_balance(target_id)}$")
            except:
                pass
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {e}\n\nФормат: ID|сумма")
        del user_states[user_id]
        send_main_menu(message)
        return

    # ===== Рассылка =====
    if state.get("awaiting_mailing"):
        users_data = load_users()
        success = fail = 0
        bot.send_message(user_id, "📢 Рассылка начата...")
        for uid in users_data.keys():
            try:
                bot.send_message(int(uid), f"📢 РАССЫЛКА\n\n{text}")
                success += 1
                time.sleep(0.05)
            except:
                fail += 1
        bot.send_message(user_id,
            f"✅ Рассылка завершена!\n📨 Доставлено: {success}\n❌ Ошибок: {fail}")
        del user_states[user_id]
        send_main_menu(message)
        return

    # ===== Бан пользователя =====
    if state.get("awaiting_ban"):
        try:
            target_id = int(text)
            users_data = load_users()
            if str(target_id) in users_data:
                current = users_data[str(target_id)].get("is_banned", False)
                users_data[str(target_id)]["is_banned"] = not current
                save_users(users_data)
                action = "заблокирован" if not current else "разблокирован"
                bot.send_message(user_id, f"✅ Пользователь ID:{target_id} {action}!")
                try:
                    bot.send_message(target_id,
                        f"⛔ Вы {action} в боте!" if not current
                        else f"✅ Вы {action} в боте!")
                except:
                    pass
            else:
                bot.send_message(user_id, "❌ Пользователь не найден!")
        except:
            bot.send_message(user_id, "❌ Введите корректный ID!")
        del user_states[user_id]
        send_main_menu(message)
        return

    send_main_menu(message)


# ========== СОЗДАНИЕ ПЛАТЕЖА ==========
def process_payment(chat_id, user_id, amount, edit_msg_id=None):
    invoice_id, invoice_url = create_invoice(amount, user_id)

    if not invoice_url:
        bot.send_message(user_id, "❌ Ошибка создания платежа. Попробуйте позже.")
        return

    text = (f"💰 ПОПОЛНЕНИЕ БАЛАНСА\n\n"
            f"Сумма: {amount}$\n"
            f"Валюта: USDT\n\n"
            f"Нажмите «Оплатить» и завершите оплату в CryptoBot.\n"
            f"Баланс пополнится автоматически в течение нескольких секунд.")

    kb = payment_keyboard(invoice_url)

    if edit_msg_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id,
                                  message_id=edit_msg_id, reply_markup=kb)
            msg_id = edit_msg_id
        except:
            sent = bot.send_message(chat_id, text, reply_markup=kb)
            msg_id = sent.message_id
    else:
        sent = bot.send_message(chat_id, text, reply_markup=kb)
        msg_id = sent.message_id

    if invoice_id:
        active_invoices[invoice_id] = {
            "user_id": user_id,
            "amount": amount,
            "chat_id": chat_id,
            "message_id": msg_id
        }


# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    init_files()

    watcher_thread = threading.Thread(target=payment_watcher, daemon=True)
    watcher_thread.start()

    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН")
    print("=" * 50)
    print(f"✅ Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"🔄 Авто-проверка оплаты: каждые 3 сек")
    print("=" * 50)

    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except KeyboardInterrupt:
            print("\n🔴 Бот остановлен")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
