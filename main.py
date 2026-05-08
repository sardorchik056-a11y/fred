import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import os
import time
import requests
import threading
from datetime import datetime

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8647713741:AAHTMRqQImX8cRMAU8oxHBvpMBbHGudGR5s"
CRYPTOBOT_TOKEN = "562214:AABJIaVpSkcIR7FvY7B8Oh3TszuqCUgi0Tk"
ADMIN_IDS = [8118184388, 8276697984, 8115654734]

bot = telebot.TeleBot(BOT_TOKEN)

try:
    bot.remove_webhook()
    print("✅ Вебхук удалён")
except:
    pass
time.sleep(1)

DB_FILE = "bot.db"

user_states = {}
active_invoices = {}
user_stock_cap = {}  # {user_id: True} — показывать склад < 25 после пополнения

# ========== ПРЕМИУМ ЭМОДЗИ ID ==========
EMOJI_CATALOG   = "5445221832074483553"
EMOJI_REFERRAL  = "5332724926216428039"
EMOJI_SUPPORT   = "5201691993775818138"
EMOJI_TERMS     = "5444856076954520455"
EMOJI_BALANCE   = "5312123810638483121"
EMOJI_BACK      = "6039539366177541657"
EMOJI_PAY       = "6030776052345737530"
EMOJI_CANCEL    = "6039539366177541657"
EMOJI_REF_LINK  = "5260730055880876557"
EMOJI_REF_STATS = "5258330865674494479"
EMOJI_HOME      = "5260399854500191689"
EMOJI_INVITE    = "5258513401784573443"
EMOJI_BUY       = "5258185631355378853"
EMOJI_DEPOSIT   = "6039496266180726678"
EMOJI_CUSTOM    = "6039496266180726678"
EMOJI_AGREE     = "6041720006973067267"


# ========== БАЗА ДАННЫХ SQLite ==========
_db_lock = threading.Lock()
_conn: sqlite3.Connection = None


def _open_connection():
    global _conn
    _conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=15)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA synchronous=NORMAL")
    _conn.execute("PRAGMA foreign_keys=ON")
    _conn.execute("PRAGMA cache_size=-8000")
    _conn.commit()


def db_exec(query: str, params=(), fetchone=False, fetchall=False):
    with _db_lock:
        cur = _conn.execute(query, params)
        _conn.commit()
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        return cur


def init_db():
    with _db_lock:
        _conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id           INTEGER PRIMARY KEY,
                username          TEXT,
                balance           REAL    NOT NULL DEFAULT 0.0,
                total_bought      INTEGER NOT NULL DEFAULT 0,
                referrer_id       INTEGER,
                referral_earnings REAL    NOT NULL DEFAULT 0.0,
                is_banned         INTEGER NOT NULL DEFAULT 0,
                registered_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS referrals (
                referrer_id INTEGER NOT NULL,
                referral_id INTEGER NOT NULL,
                PRIMARY KEY (referrer_id, referral_id)
            );

            CREATE TABLE IF NOT EXISTS products (
                product_key TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                emoji       TEXT NOT NULL DEFAULT '📦',
                price       REAL NOT NULL,
                stock       INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS purchases (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                product_key  TEXT    NOT NULL,
                quantity     INTEGER NOT NULL,
                amount       REAL    NOT NULL,
                purchased_at TEXT
            );
        """)
        _conn.commit()

        count = _conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            _conn.executemany(
                "INSERT INTO products(product_key,name,emoji,price,stock,description) VALUES(?,?,?,?,?,?)",
                [
                    ("web_token", "Web Token", "🔑", 2.50, 5,
                     "Токен доступа, готов к использованию"),
                    ("json",      "JSON",       "📄", 3.00, 4,
                     "Полные данные в JSON формате"),
                    ("autoreg",   "Авторег",    "🤖", 1.80, 3,
                     "Аккаунт зарегистрированный на SIM"),
                ]
            )
            _conn.commit()


# ========== ПОЛЬЗОВАТЕЛИ ==========

def register_user(user_id: int, username: str = None):
    db_exec(
        """INSERT OR IGNORE INTO users
           (user_id, username, balance, total_bought, referral_earnings, is_banned, registered_at)
           VALUES (?, ?, 0.0, 0, 0.0, 0, ?)""",
        (user_id, username, str(datetime.now()))
    )


def get_user(user_id: int):
    return db_exec("SELECT * FROM users WHERE user_id=?", (user_id,), fetchone=True)


def get_all_users():
    return db_exec("SELECT * FROM users", fetchall=True)


def get_user_balance(user_id: int) -> float:
    row = db_exec("SELECT balance FROM users WHERE user_id=?", (user_id,), fetchone=True)
    return round(row["balance"], 2) if row else 0.0


def add_balance(user_id: int, amount: float):
    db_exec(
        "UPDATE users SET balance=ROUND(balance+?,2) WHERE user_id=?",
        (amount, user_id)
    )


def deduct_balance(user_id: int, amount: float) -> bool:
    with _db_lock:
        row = _conn.execute(
            "SELECT balance FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if row and row["balance"] >= amount:
            _conn.execute(
                "UPDATE users SET balance=ROUND(balance-?,2) WHERE user_id=?",
                (amount, user_id)
            )
            _conn.commit()
            return True
    return False


def set_banned(user_id: int, banned: bool):
    db_exec("UPDATE users SET is_banned=? WHERE user_id=?", (1 if banned else 0, user_id))


# ========== РЕФЕРАЛЫ ==========

def add_referral(referrer_id: int, referral_id: int):
    db_exec(
        "INSERT OR IGNORE INTO referrals(referrer_id,referral_id) VALUES(?,?)",
        (referrer_id, referral_id)
    )
    db_exec(
        "UPDATE users SET referrer_id=? WHERE user_id=? AND referrer_id IS NULL",
        (referrer_id, referral_id)
    )


def get_referrals(referrer_id: int):
    return db_exec(
        "SELECT referral_id FROM referrals WHERE referrer_id=?",
        (referrer_id,), fetchall=True
    )


def add_referral_earning(referrer_id: int, amount: float):
    db_exec(
        """UPDATE users
           SET balance=ROUND(balance+?,2),
               referral_earnings=ROUND(referral_earnings+?,2)
           WHERE user_id=?""",
        (amount, amount, referrer_id)
    )


# ========== ТОВАРЫ ==========

def get_all_products() -> dict:
    rows = db_exec("SELECT * FROM products", fetchall=True)
    return {r["product_key"]: dict(r) for r in rows}


def get_product(product_key: str):
    row = db_exec(
        "SELECT * FROM products WHERE product_key=?", (product_key,), fetchone=True
    )
    return dict(row) if row else None


def upsert_product(product_key, name, emoji, price, stock, description):
    db_exec(
        """INSERT INTO products(product_key,name,emoji,price,stock,description)
           VALUES(?,?,?,?,?,?)
           ON CONFLICT(product_key) DO UPDATE SET
             name=excluded.name, emoji=excluded.emoji,
             price=excluded.price, stock=excluded.stock,
             description=excluded.description""",
        (product_key, name, emoji, price, stock, description)
    )


def update_product_field(product_key: str, field: str, value):
    allowed = {"name", "emoji", "price", "stock", "description"}
    if field not in allowed:
        return
    db_exec(f"UPDATE products SET {field}=? WHERE product_key=?", (value, product_key))


def add_stock(product_key: str, amount: int):
    db_exec(
        "UPDATE products SET stock=stock+? WHERE product_key=?",
        (amount, product_key)
    )


def delete_product(product_key: str):
    db_exec("DELETE FROM products WHERE product_key=?", (product_key,))


# ========== ПОКУПКИ ==========

def add_purchase(user_id: int, product_key: str, quantity: int, amount: float):
    db_exec(
        """INSERT INTO purchases(user_id,product_key,quantity,amount,purchased_at)
           VALUES(?,?,?,?,?)""",
        (user_id, product_key, quantity, amount, str(datetime.now()))
    )
    db_exec(
        "UPDATE users SET total_bought=total_bought+? WHERE user_id=?",
        (quantity, user_id)
    )


def get_user_purchases(user_id: int):
    return db_exec(
        "SELECT * FROM purchases WHERE user_id=?", (user_id,), fetchall=True
    )


def get_all_purchases():
    return db_exec("SELECT * FROM purchases", fetchall=True)


# ========== КРИПТОПЛАТЕЖИ ==========

def create_invoice(amount: float, user_id: int):
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
        r = requests.post(url, headers=headers, json=data, timeout=10)
        result = r.json()
        if result.get("ok"):
            inv = result["result"]
            return inv["invoice_id"], inv["bot_invoice_url"]
    except Exception as e:
        print(f"Ошибка создания инвойса: {e}")
    return None, None


def check_invoice_status(invoice_id):
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    try:
        r = requests.get(url, headers=headers,
                         params={"invoice_ids": str(invoice_id)}, timeout=10)
        result = r.json()
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
                    uid      = info["user_id"]
                    amount   = info["amount"]
                    chat_id  = info["chat_id"]
                    msg_id   = info["message_id"]

                    add_balance(uid, amount)

                    # После пополнения — включаем визуальный кап склада < 25 для этого пользователя
                    user_stock_cap[uid] = True

                    user = get_user(uid)
                    referrer_id = user["referrer_id"] if user else None
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

                elif status == "expired":
                    try:
                        bot.edit_message_text(
                            "⏰ Счёт истёк. Создайте новый.",
                            chat_id=info["chat_id"],
                            message_id=info["message_id"],
                            reply_markup=None
                        )
                    except:
                        pass
                    to_remove.append(invoice_id)
            except Exception as e:
                print(f"Ошибка watcher: {e}")
        for inv_id in to_remove:
            active_invoices.pop(inv_id, None)


# ========== КЛАВИАТУРЫ ==========

def main_menu_keyboard(user_id=None):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(" Каталог",     callback_data="catalog",
                             icon_custom_emoji_id=EMOJI_CATALOG),
        InlineKeyboardButton(" Реф. баланс", callback_data="referral",
                             icon_custom_emoji_id=EMOJI_REFERRAL),
        InlineKeyboardButton(" Поддержка",   callback_data="support",
                             icon_custom_emoji_id=EMOJI_SUPPORT),
        InlineKeyboardButton(" Оферта",      callback_data="terms",
                             icon_custom_emoji_id=EMOJI_TERMS),
        InlineKeyboardButton(" Баланс",      callback_data="balance",
                             icon_custom_emoji_id=EMOJI_BALANCE),
    )
    return kb


def catalog_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for key, p in get_all_products().items():
        kb.add(InlineKeyboardButton(
            f"{p['emoji']} {p['name']} — {p['price']}$",
            callback_data=f"buy_{key}"
        ))
    kb.add(InlineKeyboardButton(" Назад", callback_data="back_to_menu",
                                icon_custom_emoji_id=EMOJI_BACK))
    return kb


def admin_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 Товары",            callback_data="admin_products"),
        InlineKeyboardButton("👥 Пользователи",      callback_data="admin_users"),
        InlineKeyboardButton("💰 Пополнения",        callback_data="admin_deposits"),
        InlineKeyboardButton("📢 Рассылка",          callback_data="admin_mailing"),
        InlineKeyboardButton("📊 Статистика",        callback_data="admin_stats"),
        InlineKeyboardButton("⚠️ Бан пользователя", callback_data="admin_ban"),
        InlineKeyboardButton("🔙 Выход",             callback_data="back_to_menu"),
    )
    return kb


def admin_products_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("➕ Добавить товар",      callback_data="add_product"),
        InlineKeyboardButton("✏️ Управление товаром",  callback_data="manage_product_list"),
        InlineKeyboardButton("❌ Удалить товар",       callback_data="delete_product"),
        InlineKeyboardButton("◀️ Назад",               callback_data="admin_panel"),
    )
    return kb


def manage_product_list_keyboard(action_prefix: str):
    kb = InlineKeyboardMarkup(row_width=1)
    for key, p in get_all_products().items():
        kb.add(InlineKeyboardButton(
            f"{p['emoji']} {p['name']} | {p['price']}$ | 📦{p['stock']}шт",
            callback_data=f"{action_prefix}{key}"
        ))
    kb.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_products"))
    return kb


def product_manage_keyboard(product_key: str):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Добавить остаток",    callback_data=f"prod_addstock_{product_key}"),
        InlineKeyboardButton("📦 Установить остаток",  callback_data=f"prod_setstock_{product_key}"),
        InlineKeyboardButton("💰 Изменить цену",       callback_data=f"prod_setprice_{product_key}"),
        InlineKeyboardButton("✏️ Изменить название",   callback_data=f"prod_setname_{product_key}"),
        InlineKeyboardButton("📝 Изменить описание",   callback_data=f"prod_setdesc_{product_key}"),
        InlineKeyboardButton("🎭 Изменить эмодзи",    callback_data=f"prod_setemoji_{product_key}"),
        InlineKeyboardButton("📋 Полное редактирование", callback_data=f"prod_full_{product_key}"),
        InlineKeyboardButton("◀️ Назад",               callback_data="manage_product_list"),
    )
    return kb


def admin_users_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📋 Список пользователей", callback_data="admin_user_list"),
        InlineKeyboardButton("🔍 Найти пользователя",   callback_data="admin_find_user"),
        InlineKeyboardButton("◀️ Назад",                callback_data="admin_panel"),
    )
    return kb


def admin_deposits_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💰 Ручное зачисление", callback_data="admin_manual_deposit"),
        InlineKeyboardButton("◀️ Назад",             callback_data="admin_panel"),
    )
    return kb


def referral_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(" Моя ссылка",   callback_data="copy_ref_link",
                             icon_custom_emoji_id=EMOJI_REF_LINK),
        InlineKeyboardButton(" Мои рефералы", callback_data="my_referrals",
                             icon_custom_emoji_id=EMOJI_REF_STATS),
        InlineKeyboardButton(" Главное меню", callback_data="back_to_menu",
                             icon_custom_emoji_id=EMOJI_HOME),
    )
    return kb


def my_referrals_keyboard(has_referrals=False):
    kb = InlineKeyboardMarkup(row_width=2)
    if not has_referrals:
        kb.add(
            InlineKeyboardButton(" Моя ссылка",   callback_data="copy_ref_link",
                                 icon_custom_emoji_id=EMOJI_REF_LINK),
            InlineKeyboardButton(" Главное меню", callback_data="back_to_menu",
                                 icon_custom_emoji_id=EMOJI_HOME),
        )
    else:
        kb.add(
            InlineKeyboardButton(" Пригласить ещё", callback_data="referral",
                                 icon_custom_emoji_id=EMOJI_INVITE),
            InlineKeyboardButton(" Главное меню",   callback_data="back_to_menu",
                                 icon_custom_emoji_id=EMOJI_HOME),
        )
    return kb


def support_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(" Назад", callback_data="back_to_menu",
                                icon_custom_emoji_id=EMOJI_BACK))
    return kb


def terms_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(" Согласен", callback_data="back_to_menu",
                             icon_custom_emoji_id=EMOJI_AGREE),
        InlineKeyboardButton(" Назад",    callback_data="back_to_menu",
                             icon_custom_emoji_id=EMOJI_BACK),
    )
    return kb


def balance_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    for amount in [5, 10, 25, 50]:
        kb.add(InlineKeyboardButton(
            f" {amount}$", callback_data=f"deposit_{amount}",
            icon_custom_emoji_id=EMOJI_DEPOSIT
        ))
    kb.add(InlineKeyboardButton(" Другая сумма", callback_data="deposit_custom",
                                icon_custom_emoji_id=EMOJI_CUSTOM))
    kb.add(InlineKeyboardButton(" Назад", callback_data="back_to_menu",
                                icon_custom_emoji_id=EMOJI_BACK))
    return kb


def payment_keyboard(invoice_url: str):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(" Оплатить", url=invoice_url,
                             icon_custom_emoji_id=EMOJI_PAY),
        InlineKeyboardButton(" Отмена",   callback_data="cancel_payment",
                             icon_custom_emoji_id=EMOJI_CANCEL),
    )
    return kb


def buy_product_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(" В каталог", callback_data="catalog",
                                icon_custom_emoji_id=EMOJI_BACK))
    return kb


def confirm_buy_keyboard(product_key: str, quantity: int, insufficient=False):
    kb = InlineKeyboardMarkup(row_width=2)
    if insufficient:
        kb.add(
            InlineKeyboardButton(" Пополнить баланс", callback_data="balance",
                                 icon_custom_emoji_id=EMOJI_BALANCE),
            InlineKeyboardButton(" Каталог",          callback_data="catalog",
                                 icon_custom_emoji_id=EMOJI_BACK),
        )
    else:
        kb.add(
            InlineKeyboardButton(" Купить", callback_data=f"confirm_buy_{product_key}_{quantity}",
                                 icon_custom_emoji_id=EMOJI_BUY),
            InlineKeyboardButton(" Отмена", callback_data="cancel_buy",
                                 icon_custom_emoji_id=EMOJI_CANCEL),
        )
    return kb


def after_buy_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(" Поддержка",    callback_data="support",
                             icon_custom_emoji_id=EMOJI_SUPPORT),
        InlineKeyboardButton(" Главное меню", callback_data="back_to_menu",
                             icon_custom_emoji_id=EMOJI_HOME),
    )
    return kb


def cancel_buy_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(" Каталог",      callback_data="catalog",
                             icon_custom_emoji_id=EMOJI_CATALOG),
        InlineKeyboardButton(" Главное меню", callback_data="back_to_menu",
                             icon_custom_emoji_id=EMOJI_HOME),
    )
    return kb


def cancel_payment_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(" Баланс",       callback_data="balance",
                             icon_custom_emoji_id=EMOJI_BALANCE),
        InlineKeyboardButton(" Главное меню", callback_data="back_to_menu",
                             icon_custom_emoji_id=EMOJI_HOME),
    )
    return kb


def back_to_admin_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_panel"))
    return kb


def back_to_admin_users_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("◀️ Назад", callback_data="admin_users"))
    return kb


# ========== УТИЛИТЫ ==========

def get_display_stock(user_id: int, real_stock: int) -> int:
    """Возвращает визуальный остаток для пользователя.
    Если у пользователя активен кап — показываем min(real, 24).
    """
    if user_stock_cap.get(user_id, False):
        return min(real_stock, 24)
    return real_stock


def get_profile_text(user_id: int, username: str = None) -> str:
    user = get_user(user_id)
    balance      = round(user["balance"], 2)  if user else 0.0
    total_bought = user["total_bought"]        if user else 0
    text  = f"Добро пожаловать, @{username or 'Пользователь'}!\n\n"
    text += "╭─────────────────\n"
    text += f'├ <tg-emoji emoji-id="6032693626394382504">🎟</tg-emoji> ID: {user_id}\n'
    text += f'├ <tg-emoji emoji-id="5904462880941545555">🎟</tg-emoji> Куплено: {total_bought} акков\n'
    text += f'├ <tg-emoji emoji-id="5258204546391351475">🎟</tg-emoji> Баланс: {balance}$\n'
    text += "╰─────────────────\n\n"
    text += " MAX | Главное меню\n"
    return text


def send_main_menu(message):
    user_id  = message.from_user.id
    username = message.from_user.username
    text     = get_profile_text(user_id, username)
    try:
        if os.path.exists("welcome.jpg"):
            with open("welcome.jpg", "rb") as photo:
                bot.send_photo(user_id, photo, caption=text, parse_mode="HTML",
                               reply_markup=main_menu_keyboard(user_id))
            return
    except:
        pass
    bot.send_message(user_id, text, parse_mode="HTML",
                     reply_markup=main_menu_keyboard(user_id))


def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    try:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id,
                              reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        try:
            bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        except:
            pass


def product_info_text(product_key: str, product: dict) -> str:
    return (
        f"📦 ТОВАР: {product['emoji']} {product['name']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔑 ID: {product_key}\n"
        f"💰 Цена: {product['price']}$\n"
        f"📦 Остаток: {product['stock']} шт\n"
        f"📝 Описание: {product['description']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Выберите что изменить:"
    )


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ========== КОМАНДЫ ==========

@bot.message_handler(commands=["start"])
def start_command(message):
    user_id  = message.from_user.id
    username = message.from_user.username
    register_user(user_id, username)

    user = get_user(user_id)
    if user and user["is_banned"]:
        bot.send_message(user_id, "⛔ Вы заблокированы в этом боте!")
        return

    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if (referrer_id != user_id
                and get_user(referrer_id) is not None
                and user and user["referrer_id"] is None):
            add_referral(referrer_id, user_id)
            bot.send_message(user_id,
                "✅ Вы были приглашены! При покупке пригласивший получит бонус.")

    send_main_menu(message)


@bot.message_handler(commands=["admin"])
def admin_command(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, "⛔ Нет доступа!")
        return
    text = ("👑 АДМИН ПАНЕЛЬ | MAX\n\n━━━━━━━━━━━━━━━\n\n"
            "1 — 📦 Товары\n2 — 👥 Пользователи\n"
            "3 — 💰 Пополнения\n4 — 📢 Рассылка\n"
            "5 — 📊 Статистика\n6 — ⚠️ Бан\n\n━━━━━━━━━━━━━━━")
    bot.send_message(user_id, text, reply_markup=admin_keyboard())


# ========== CALLBACK HANDLER ==========

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id    = call.from_user.id
    username   = call.from_user.username
    message_id = call.message.message_id
    chat_id    = call.message.chat.id
    data       = call.data

    user = get_user(user_id)
    if user and user["is_banned"] and data != "back_to_menu":
        bot.answer_callback_query(call.id, "⛔ Вы заблокированы!", show_alert=True)
        return

    # ── Главное меню ──────────────────────────────────────────────────────────

    if data == "back_to_menu":
        user_states.pop(user_id, None)
        edit_message(chat_id, message_id,
                     get_profile_text(user_id, username),
                     main_menu_keyboard(user_id))
        bot.answer_callback_query(call.id)

    elif data == "catalog":
        products = get_all_products()
        capped   = user_stock_cap.get(user_id, False)
        text = "📦 КАТАЛОГ\n\n"
        for key, p in products.items():
            display_stock = get_display_stock(user_id, p["stock"])
            stock_text = f"{display_stock} шт" if display_stock > 0 else "❌ Нет в наличии"
            text += f"{p['emoji']} {p['name']} ({stock_text} | {p['price']}$)\n"
            text += f"   └ {p['description']}\n\n"
        text += "━━━━━━━━━━━━━━━\n\nНажмите на товар:"
        edit_message(chat_id, message_id, text, catalog_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "referral":
        u            = get_user(user_id)
        bot_username = bot.get_me().username
        ref_link     = f"https://t.me/{bot_username}?start={user_id}"
        refs         = get_referrals(user_id)
        ref_earn     = u["referral_earnings"] if u else 0
        bal          = u["balance"] if u else 0
        text  = '<tg-emoji emoji-id="5258513401784573443">🎟</tg-emoji> РЕФЕРАЛЬНАЯ ПРОГРАММА\n\n'
        text += f"Ваша реферальная ссылка:\n<code>{ref_link}</code>\n\n"
        text += "━━━━━━━━━━━━━━━\n\n"
        text += f'<tg-emoji emoji-id="5258513401784573443">🎟</tg-emoji> Приглашено: {len(refs)}\n'
        text += f'<tg-emoji emoji-id="5890848474563352982">🎟</tg-emoji> Заработано: {ref_earn}$\n'
        text += f'<tg-emoji emoji-id="5258204546391351475">🎟</tg-emoji> Баланс: {round(bal,2)}$\n\n'
        text += "━━━━━━━━━━━━━━━\n\n За каждую покупку реферала вы получаете 10%."
        edit_message(chat_id, message_id, text, referral_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "my_referrals":
        refs = get_referrals(user_id)
        if not refs:
            edit_message(chat_id, message_id,
                         " МОИ РЕФЕРАЛЫ\n\n👥 Пока никого нет\n\nПригласите друзей!",
                         my_referrals_keyboard(False))
        else:
            text = " МОИ РЕФЕРАЛЫ\n\n"
            for i, row in enumerate(refs[:10], 1):
                rid       = row["referral_id"]
                purchases = get_user_purchases(rid)
                spent     = sum(p["amount"] for p in purchases)
                bonus     = round(spent * 0.1, 2)
                ru        = get_user(rid)
                rname     = ru["username"] if ru and ru["username"] else f"ID{rid}"
                text += f"{i}. @{rname} — {len(purchases)} покупок | бонус: {bonus}$\n"
            text += f"\n━━━━━━━━━━━━━━━\n👥 Всего: {len(refs)}"
            edit_message(chat_id, message_id, text, my_referrals_keyboard(True))
        bot.answer_callback_query(call.id)

    elif data == "copy_ref_link":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        bot.answer_callback_query(call.id, f"Ссылка: {ref_link}", show_alert=True)

    elif data == "support":
        edit_message(chat_id, message_id,
                     " ПОДДЕРЖКА\n\nСвяжитесь с нами: @Qadwero",
                     support_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "terms":
        text = """📜 ПРАВИЛА И ОФЕРТА

1️⃣ Токены НЕ хранятся заранее
Берутся ТОЛЬКО в момент покупки. Сохраните их сразу.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ Запрещено использовать аккаунты для мошенничества
• Не использовать для обмана / фишинга / спама
• Не нарушать законы вашей страны

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣ Замена авторегов в течение 5 часов
Если оказался нерабочим — замена при наличии скриншота ошибки.
Web Token и JSON замене не подлежат если были рабочими.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4️⃣ Возврат денег не предусмотрен. Все товары — цифровые.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5️⃣ Конфиденциальность
Ваши данные не передаются третьим лицам.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6️⃣ Минимальный возраст: 18 лет.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7️⃣ Продолжая использовать бота вы соглашаетесь со всеми правилами."""
        edit_message(chat_id, message_id, text, terms_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "balance":
        bal  = get_user_balance(user_id)
        text = f" ВАШ БАЛАНС\n\nТекущий баланс: {bal}$\n\nВыберите сумму для пополнения:"
        edit_message(chat_id, message_id, text, balance_keyboard())
        bot.answer_callback_query(call.id)

    # ── Покупка ───────────────────────────────────────────────────────────────

    elif data.startswith("buy_"):
        product_key = data[4:]
        product = get_product(product_key)
        if not product:
            bot.answer_callback_query(call.id, "Товар не найден", show_alert=True)
            return
        display_stock = get_display_stock(user_id, product["stock"])
        if display_stock <= 0:
            bot.answer_callback_query(call.id, "❌ Товар закончился!", show_alert=True)
            return
        bal     = get_user_balance(user_id)
        max_qty = min(display_stock, 25)
        text = (f"{product['emoji']} {product['name']} | {product['price']}$ за шт\n\n"
                f"📦 В наличии: {display_stock} шт\n"
                f" Ваш баланс: {bal}$\n\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"Введите количество (1–{max_qty}):\n➡️ Например: 1")
        edit_message(chat_id, message_id, text, buy_product_keyboard())
        bot.answer_callback_query(call.id)
        user_states[user_id] = {
            "awaiting_quantity": True,
            "product_key": product_key,
            "chat_id": chat_id,
            "message_id": message_id
        }

    elif data.startswith("confirm_buy_"):
        parts       = data.split("_")
        product_key = parts[2]
        quantity    = int(parts[3])
        product     = get_product(product_key)
        if not product:
            bot.answer_callback_query(call.id, "Товар не найден", show_alert=True)
            return
        total_price = round(product["price"] * quantity, 2)
        bal         = get_user_balance(user_id)
        if bal < total_price:
            bot.answer_callback_query(call.id, "❌ Недостаточно средств!", show_alert=True)
            return
        if product["stock"] < quantity:
            bot.answer_callback_query(call.id, f"❌ В наличии только {product['stock']} шт!", show_alert=True)
            return
        if not deduct_balance(user_id, total_price):
            bot.answer_callback_query(call.id, "❌ Ошибка списания!", show_alert=True)
            return

        update_product_field(product_key, "stock", product["stock"] - quantity)
        add_purchase(user_id, product_key, quantity, total_price)

        u = get_user(user_id)
        referrer_id = u["referrer_id"] if u else None
        if referrer_id:
            bonus = round(total_price * 0.1, 2)
            add_referral_earning(referrer_id, bonus)
            try:
                bot.send_message(int(referrer_id),
                    f"🎁 Ваш реферал купил {product['name']} x{quantity}!\n💰 Начислено: +{bonus}$")
            except:
                pass

        for aid in ADMIN_IDS:
            try:
                bot.send_message(aid,
                    f"🛒 НОВАЯ ПОКУПКА!\n\n👤 ID{user_id} @{username}\n"
                    f"📦 {product['emoji']} {product['name']} x{quantity}\n💰 Сумма: {total_price}$")
            except:
                pass

        text = (f"✅ ПОКУПКА УСПЕШНА!\n\n"
                f"Товар: {product['emoji']} {product['name']}\n"
                f"Количество: {quantity} шт\nСумма: {total_price}$\n"
                f"Остаток баланса: {get_user_balance(user_id)}$\n\n"
                f"Обратитесь в поддержку для получения товара.")
        edit_message(chat_id, message_id, text, after_buy_keyboard())
        bot.answer_callback_query(call.id, "✅ Покупка успешна!", show_alert=True)

    elif data.startswith("cancel_buy"):
        user_states.pop(user_id, None)
        edit_message(chat_id, message_id, "❌ Покупка отменена.", cancel_buy_keyboard())
        bot.answer_callback_query(call.id)

    # ── Пополнение ────────────────────────────────────────────────────────────

    elif data == "deposit_custom":
        bot.send_message(user_id, " ПОПОЛНЕНИЕ БАЛАНСА\n\nВведите сумму (от 1$ до 5000$):")
        user_states[user_id] = {"awaiting_custom_deposit": True}
        bot.answer_callback_query(call.id)

    elif data.startswith("deposit_") and data != "deposit_custom":
        try:
            amount = float(data.split("_")[1])
        except (IndexError, ValueError):
            bot.answer_callback_query(call.id, "Ошибка суммы", show_alert=True)
            return
        process_payment(chat_id, user_id, amount, message_id)
        bot.answer_callback_query(call.id)

    elif data == "cancel_payment":
        to_remove = [k for k, v in active_invoices.items() if v["user_id"] == user_id]
        for k in to_remove:
            active_invoices.pop(k, None)
        edit_message(chat_id, message_id, "❌ Платёж отменён.", cancel_payment_keyboard())
        bot.answer_callback_query(call.id)

    # ── Админ панель ──────────────────────────────────────────────────────────

    elif data == "admin_panel":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        text = ("👑 АДМИН ПАНЕЛЬ | MAX\n\n━━━━━━━━━━━━━━━\n\n"
                "1 — 📦 Товары\n2 — 👥 Пользователи\n"
                "3 — 💰 Пополнения\n4 — 📢 Рассылка\n"
                "5 — 📊 Статистика\n6 — ⚠️ Бан\n\n━━━━━━━━━━━━━━━")
        edit_message(chat_id, message_id, text, admin_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "admin_products":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        products = get_all_products()
        text = "📦 УПРАВЛЕНИЕ ТОВАРАМИ\n\n"
        for key, p in products.items():
            text += f"{p['emoji']} {p['name']} | 💰{p['price']}$ | 📦{p['stock']}шт\n"
        text += "\n━━━━━━━━━━━━━━━\nВыберите действие:"
        edit_message(chat_id, message_id, text, admin_products_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "add_product":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id,
            "➕ ДОБАВЛЕНИЕ ТОВАРА\n\nФормат:\n<code>id|название|цена|кол-во|эмодзи|описание</code>\n\n"
            "Пример:\n<code>new_token|Новый Токен|5|10|⭐|Описание товара</code>",
            parse_mode="HTML")
        user_states[user_id] = {"awaiting_add_product": True}
        bot.answer_callback_query(call.id)

    elif data == "manage_product_list":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        edit_message(chat_id, message_id, "✏️ ВЫБЕРИТЕ ТОВАР ДЛЯ УПРАВЛЕНИЯ:",
                     manage_product_list_keyboard("manage_select_"))
        bot.answer_callback_query(call.id)

    elif data.startswith("manage_select_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        product_key = data[len("manage_select_"):]
        product = get_product(product_key)
        if not product:
            bot.answer_callback_query(call.id, "Товар не найден", show_alert=True)
            return
        edit_message(chat_id, message_id,
                     product_info_text(product_key, product),
                     product_manage_keyboard(product_key))
        bot.answer_callback_query(call.id)

    elif data.startswith("prod_addstock_"):
        if not is_admin(user_id): return
        product_key = data[len("prod_addstock_"):]
        p = get_product(product_key)
        bot.send_message(user_id,
            f"➕ ДОБАВИТЬ ОСТАТОК\n\nТовар: {p['emoji']} {p['name']}\n"
            f"Текущий остаток: {p['stock']} шт\n\nВведите сколько добавить:")
        user_states[user_id] = {"prod_addstock": product_key,
                                "chat_id": chat_id, "message_id": message_id}
        bot.answer_callback_query(call.id)

    elif data.startswith("prod_setstock_"):
        if not is_admin(user_id): return
        product_key = data[len("prod_setstock_"):]
        p = get_product(product_key)
        bot.send_message(user_id,
            f"📦 УСТАНОВИТЬ ОСТАТОК\n\nТовар: {p['emoji']} {p['name']}\n"
            f"Текущий остаток: {p['stock']} шт\n\nВведите новое количество:")
        user_states[user_id] = {"prod_setstock": product_key,
                                "chat_id": chat_id, "message_id": message_id}
        bot.answer_callback_query(call.id)

    elif data.startswith("prod_setprice_"):
        if not is_admin(user_id): return
        product_key = data[len("prod_setprice_"):]
        p = get_product(product_key)
        bot.send_message(user_id,
            f"💰 ИЗМЕНИТЬ ЦЕНУ\n\nТовар: {p['emoji']} {p['name']}\n"
            f"Текущая цена: {p['price']}$\n\nВведите новую цену (например: 3.50):")
        user_states[user_id] = {"prod_setprice": product_key,
                                "chat_id": chat_id, "message_id": message_id}
        bot.answer_callback_query(call.id)

    elif data.startswith("prod_setname_"):
        if not is_admin(user_id): return
        product_key = data[len("prod_setname_"):]
        p = get_product(product_key)
        bot.send_message(user_id,
            f"✏️ ИЗМЕНИТЬ НАЗВАНИЕ\n\nТовар: {p['emoji']} {p['name']}\n\nВведите новое название:")
        user_states[user_id] = {"prod_setname": product_key,
                                "chat_id": chat_id, "message_id": message_id}
        bot.answer_callback_query(call.id)

    elif data.startswith("prod_setdesc_"):
        if not is_admin(user_id): return
        product_key = data[len("prod_setdesc_"):]
        p = get_product(product_key)
        bot.send_message(user_id,
            f"📝 ИЗМЕНИТЬ ОПИСАНИЕ\n\nТовар: {p['emoji']} {p['name']}\n"
            f"Текущее: {p['description']}\n\nВведите новое описание:")
        user_states[user_id] = {"prod_setdesc": product_key,
                                "chat_id": chat_id, "message_id": message_id}
        bot.answer_callback_query(call.id)

    elif data.startswith("prod_setemoji_"):
        if not is_admin(user_id): return
        product_key = data[len("prod_setemoji_"):]
        p = get_product(product_key)
        bot.send_message(user_id,
            f"🎭 ИЗМЕНИТЬ ЭМОДЗИ\n\nТовар: {p['emoji']} {p['name']}\n\nВведите новый эмодзи:")
        user_states[user_id] = {"prod_setemoji": product_key,
                                "chat_id": chat_id, "message_id": message_id}
        bot.answer_callback_query(call.id)

    elif data.startswith("prod_full_"):
        if not is_admin(user_id): return
        product_key = data[len("prod_full_"):]
        p = get_product(product_key)
        bot.send_message(user_id,
            f"📋 ПОЛНОЕ РЕДАКТИРОВАНИЕ\n\nТовар: {p['emoji']} {p['name']}\n\n"
            f"Формат: <code>название|цена|кол-во|эмодзи|описание</code>\n\n"
            f"Пример:\n<code>Новый Токен|5.00|10|⭐|Новое описание</code>",
            parse_mode="HTML")
        user_states[user_id] = {"awaiting_edit_product": product_key,
                                "chat_id": chat_id, "message_id": message_id}
        bot.answer_callback_query(call.id)

    elif data == "delete_product":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        edit_message(chat_id, message_id, "❌ УДАЛЕНИЕ ТОВАРА\n\nВыберите товар:",
                     manage_product_list_keyboard("delete_select_"))
        bot.answer_callback_query(call.id)

    elif data.startswith("delete_select_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        product_key = data[len("delete_select_"):]
        p = get_product(product_key)
        if p:
            delete_product(product_key)
            bot.answer_callback_query(call.id, f"✅ Товар '{p['name']}' удалён!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Товар не найден!", show_alert=True)
        products = get_all_products()
        text = "📦 УПРАВЛЕНИЕ ТОВАРАМИ\n\n"
        for key, pr in products.items():
            text += f"{pr['emoji']} {pr['name']} | 💰{pr['price']}$ | 📦{pr['stock']}шт\n"
        text += "\n━━━━━━━━━━━━━━━\nВыберите действие:"
        edit_message(chat_id, message_id, text, admin_products_keyboard())

    elif data == "admin_users":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        edit_message(chat_id, message_id,
                     "👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ\n\nВыберите действие:",
                     admin_users_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "admin_user_list":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        users = get_all_users()
        text  = "📋 СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n\n"
        for i, u in enumerate(users[:20], 1):
            status = "🚫" if u["is_banned"] else "✅"
            text += (f"{i}. {status} ID:{u['user_id']} | "
                     f"@{u['username'] or 'нет'} | "
                     f"Баланс: {round(u['balance'],2)}$\n")
        text += f"\n━━━━━━━━━━━━━━━\n👥 Всего: {len(users)}"
        edit_message(chat_id, message_id, text, back_to_admin_users_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "admin_find_user":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id, "🔍 Введите ID или @username:")
        user_states[user_id] = {"awaiting_find_user": True}
        bot.answer_callback_query(call.id)

    elif data == "admin_deposits":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        edit_message(chat_id, message_id,
                     "💰 УПРАВЛЕНИЕ ПОПОЛНЕНИЯМИ\n\nВыберите действие:",
                     admin_deposits_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "admin_manual_deposit":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id,
            "💰 РУЧНОЕ ЗАЧИСЛЕНИЕ\n\nФормат:\n<code>ID|сумма</code>\n\n"
            "Пример:\n<code>123456789|10</code>",
            parse_mode="HTML")
        user_states[user_id] = {"awaiting_manual_deposit": True}
        bot.answer_callback_query(call.id)

    elif data == "admin_mailing":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id, "📢 Введите текст рассылки:\n\n(Для отмены: /cancel)")
        user_states[user_id] = {"awaiting_mailing": True}
        bot.answer_callback_query(call.id)

    elif data == "admin_stats":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        users     = get_all_users()
        purchases = get_all_purchases()
        products  = get_all_products()
        text = (f"📊 СТАТИСТИКА\n\n━━━━━━━━━━━━━━━\n"
                f"👥 Пользователей: {len(users)}\n"
                f"🚫 Заблокировано: {sum(1 for u in users if u['is_banned'])}\n"
                f"📦 Покупок: {len(purchases)}\n"
                f"💰 Доход: {round(sum(p['amount'] for p in purchases), 2)}$\n"
                f"━━━━━━━━━━━━━━━\n\n📦 ОСТАТКИ:\n")
        for key, p in products.items():
            text += f"{p['emoji']} {p['name']}: {p['stock']} шт | {p['price']}$\n"
        edit_message(chat_id, message_id, text, back_to_admin_keyboard())
        bot.answer_callback_query(call.id)

    elif data == "admin_ban":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
            return
        bot.send_message(user_id, "⚠️ БАН/РАЗБАН\n\nВведите ID пользователя:")
        user_states[user_id] = {"awaiting_ban": True}
        bot.answer_callback_query(call.id)

    else:
        bot.answer_callback_query(call.id)


# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text    = message.text.strip() if message.text else ""

    if text == "/cancel":
        user_states.pop(user_id, None)
        bot.send_message(user_id, "❌ Действие отменено")
        send_main_menu(message)
        return

    state = user_states.get(user_id, {})

    # ── Количество при покупке ────────────────────────────────────────────────
    if state.get("awaiting_quantity"):
        product_key = state["product_key"]
        chat_id     = state.get("chat_id", user_id)
        msg_id      = state.get("message_id")

        if not text.isdigit() or int(text) <= 0:
            bot.send_message(user_id, "❌ Введите целое положительное число!")
            return

        quantity = int(text)
        product  = get_product(product_key)

        # Минимум покупок: 25
        if quantity < 25:
            bot.send_message(user_id, "❌ Минимальное количество для покупки: 25 шт!")
            return

        if not product or quantity > product["stock"]:
            bot.send_message(user_id, f"❌ В наличии только {product['stock'] if product else 0} шт!")
            return

        total_price  = round(product["price"] * quantity, 2)
        bal          = get_user_balance(user_id)
        insufficient = bal < total_price

        confirm_text = (
            f" ПОДТВЕРЖДЕНИЕ ПОКУПКИ\n\n"
            f"Товар: {product['emoji']} {product['name']}\n"
            f"Количество: {quantity} шт\n"
            f"Цена за шт: {product['price']}$\n"
            f"Итого: {total_price}$\n\n"
            f"💰 Ваш баланс: {bal}$\n"
            f"💰 После покупки: {round(bal - total_price, 2)}$\n\n"
        )
        if insufficient:
            confirm_text += f"❌ Недостаточно средств! Нужно ещё {round(total_price - bal, 2)}$"
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

    # ── Произвольная сумма пополнения ─────────────────────────────────────────
    if state.get("awaiting_custom_deposit"):
        try:
            amount = float(text.replace(",", "."))
            if not (1 <= amount <= 5000):
                bot.send_message(user_id, "❌ Сумма должна быть от 1$ до 5000$")
                return
            del user_states[user_id]
            process_payment(message.chat.id, user_id, amount, None)
        except ValueError:
            bot.send_message(user_id, "❌ Введите числовую сумму (например: 15.50)")
        return

    # ── Добавить остаток ──────────────────────────────────────────────────────
    if state.get("prod_addstock"):
        product_key = state["prod_addstock"]
        s_chat_id   = state.get("chat_id", user_id)
        s_msg_id    = state.get("message_id")
        if not text.isdigit() or int(text) <= 0:
            bot.send_message(user_id, "❌ Введите целое положительное число!")
            return
        add_stock(product_key, int(text))
        p = get_product(product_key)
        bot.send_message(user_id, f"✅ Добавлено +{text} шт!\nТеперь в наличии: {p['stock']} шт")
        del user_states[user_id]
        try:
            bot.edit_message_text(product_info_text(product_key, p),
                chat_id=s_chat_id, message_id=s_msg_id,
                reply_markup=product_manage_keyboard(product_key))
        except: pass
        return

    # ── Установить остаток ────────────────────────────────────────────────────
    if state.get("prod_setstock"):
        product_key = state["prod_setstock"]
        s_chat_id   = state.get("chat_id", user_id)
        s_msg_id    = state.get("message_id")
        if not text.isdigit() or int(text) < 0:
            bot.send_message(user_id, "❌ Введите неотрицательное целое число!")
            return
        update_product_field(product_key, "stock", int(text))
        p = get_product(product_key)
        bot.send_message(user_id, f"✅ Остаток обновлён: {p['stock']} шт")
        del user_states[user_id]
        try:
            bot.edit_message_text(product_info_text(product_key, p),
                chat_id=s_chat_id, message_id=s_msg_id,
                reply_markup=product_manage_keyboard(product_key))
        except: pass
        return

    # ── Установить цену ───────────────────────────────────────────────────────
    if state.get("prod_setprice"):
        product_key = state["prod_setprice"]
        s_chat_id   = state.get("chat_id", user_id)
        s_msg_id    = state.get("message_id")
        try:
            new_price = round(float(text.replace(",", ".")), 2)
            if new_price <= 0: raise ValueError
        except ValueError:
            bot.send_message(user_id, "❌ Введите корректную цену (например: 3.50)")
            return
        update_product_field(product_key, "price", new_price)
        p = get_product(product_key)
        bot.send_message(user_id, f"✅ Цена обновлена: {p['price']}$")
        del user_states[user_id]
        try:
            bot.edit_message_text(product_info_text(product_key, p),
                chat_id=s_chat_id, message_id=s_msg_id,
                reply_markup=product_manage_keyboard(product_key))
        except: pass
        return

    # ── Установить название ───────────────────────────────────────────────────
    if state.get("prod_setname"):
        product_key = state["prod_setname"]
        s_chat_id   = state.get("chat_id", user_id)
        s_msg_id    = state.get("message_id")
        if not text:
            bot.send_message(user_id, "❌ Введите название!")
            return
        update_product_field(product_key, "name", text)
        p = get_product(product_key)
        bot.send_message(user_id, f"✅ Название обновлено: '{text}'")
        del user_states[user_id]
        try:
            bot.edit_message_text(product_info_text(product_key, p),
                chat_id=s_chat_id, message_id=s_msg_id,
                reply_markup=product_manage_keyboard(product_key))
        except: pass
        return

    # ── Установить описание ───────────────────────────────────────────────────
    if state.get("prod_setdesc"):
        product_key = state["prod_setdesc"]
        s_chat_id   = state.get("chat_id", user_id)
        s_msg_id    = state.get("message_id")
        update_product_field(product_key, "description", text)
        p = get_product(product_key)
        bot.send_message(user_id, "✅ Описание обновлено!")
        del user_states[user_id]
        try:
            bot.edit_message_text(product_info_text(product_key, p),
                chat_id=s_chat_id, message_id=s_msg_id,
                reply_markup=product_manage_keyboard(product_key))
        except: pass
        return

    # ── Установить эмодзи ─────────────────────────────────────────────────────
    if state.get("prod_setemoji"):
        product_key = state["prod_setemoji"]
        s_chat_id   = state.get("chat_id", user_id)
        s_msg_id    = state.get("message_id")
        update_product_field(product_key, "emoji", text)
        p = get_product(product_key)
        bot.send_message(user_id, f"✅ Эмодзи обновлён: {text}")
        del user_states[user_id]
        try:
            bot.edit_message_text(product_info_text(product_key, p),
                chat_id=s_chat_id, message_id=s_msg_id,
                reply_markup=product_manage_keyboard(product_key))
        except: pass
        return

    # ── Добавление нового товара ──────────────────────────────────────────────
    if state.get("awaiting_add_product"):
        try:
            parts = [d.strip() for d in text.split("|")]
            if len(parts) < 6:
                raise ValueError("Нужно 6 полей")
            pk   = parts[0].lower().replace(" ", "_")
            name, price, stock, emoji, desc = (
                parts[1], float(parts[2]), int(parts[3]), parts[4], parts[5])
            upsert_product(pk, name, emoji, price, stock, desc)
            bot.send_message(user_id,
                f"✅ Товар '{name}' добавлен!\n\n{emoji} {name} | {price}$ | {stock} шт")
        except Exception as e:
            bot.send_message(user_id,
                f"❌ Ошибка: {e}\n\nФормат: id|название|цена|кол-во|эмодзи|описание")
        del user_states[user_id]
        send_main_menu(message)
        return

    # ── Полное редактирование товара ──────────────────────────────────────────
    if "awaiting_edit_product" in state:
        product_key = state["awaiting_edit_product"]
        s_chat_id   = state.get("chat_id", user_id)
        s_msg_id    = state.get("message_id")
        try:
            parts = [d.strip() for d in text.split("|")]
            if len(parts) < 5:
                raise ValueError("Нужно 5 полей")
            name, price, stock, emoji, desc = (
                parts[0], float(parts[1]), int(parts[2]), parts[3], parts[4])
            if get_product(product_key):
                upsert_product(product_key, name, emoji, price, stock, desc)
                p = get_product(product_key)
                bot.send_message(user_id, "✅ Товар полностью обновлён!")
                try:
                    bot.edit_message_text(
                        product_info_text(product_key, p),
                        chat_id=s_chat_id, message_id=s_msg_id,
                        reply_markup=product_manage_keyboard(product_key))
                except: pass
            else:
                bot.send_message(user_id, "❌ Товар не найден!")
        except Exception as e:
            bot.send_message(user_id,
                f"❌ Ошибка: {e}\n\nФормат: название|цена|кол-во|эмодзи|описание")
        del user_states[user_id]
        return

    # ── Поиск пользователя ────────────────────────────────────────────────────
    if state.get("awaiting_find_user"):
        search = text.replace("@", "")
        if search.isdigit():
            found = get_user(int(search))
        else:
            rows  = db_exec("SELECT * FROM users WHERE username=? COLLATE NOCASE",
                            (search,), fetchall=True)
            found = rows[0] if rows else None

        if found:
            refs   = get_referrals(found["user_id"])
            result = (f"👤 ПОЛЬЗОВАТЕЛЬ НАЙДЕН\n\n"
                      f"ID: {found['user_id']}\n"
                      f"Username: @{found['username'] or 'нет'}\n"
                      f"💰 Баланс: {round(found['balance'],2)}$\n"
                      f"📦 Куплено: {found['total_bought']} акков\n"
                      f"👥 Рефералов: {len(refs)}\n"
                      f"💰 Реф. заработок: {found['referral_earnings']}$\n"
                      f"🚫 Статус: {'Заблокирован' if found['is_banned'] else 'Активен'}\n"
                      f"📅 Зарегистрирован: {found['registered_at']}")
        else:
            result = f"❌ Пользователь '{text}' не найден!"

        bot.send_message(user_id, result)
        del user_states[user_id]
        send_main_menu(message)
        return

    # ── Ручное зачисление ─────────────────────────────────────────────────────
    if state.get("awaiting_manual_deposit"):
        try:
            parts     = text.split("|")
            target_id = int(parts[0].strip())
            amount    = float(parts[1].strip())
            add_balance(target_id, amount)
            bot.send_message(user_id, f"✅ Зачислено {amount}$ пользователю ID:{target_id}")
            try:
                bot.send_message(target_id,
                    f"💰 Вам зачислено {amount}$!\n"
                    f"Текущий баланс: {get_user_balance(target_id)}$")
            except: pass
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {e}\n\nФормат: ID|сумма")
        del user_states[user_id]
        send_main_menu(message)
        return

    # ── Рассылка ──────────────────────────────────────────────────────────────
    if state.get("awaiting_mailing"):
        users   = get_all_users()
        ok = fail = 0
        bot.send_message(user_id, "📢 Рассылка начата...")
        for u in users:
            try:
                bot.send_message(u["user_id"], f"📢 РАССЫЛКА\n\n{text}")
                ok += 1
                time.sleep(0.05)
            except:
                fail += 1
        bot.send_message(user_id,
            f"✅ Рассылка завершена!\n📨 Доставлено: {ok}\n❌ Ошибок: {fail}")
        del user_states[user_id]
        send_main_menu(message)
        return

    # ── Бан/разбан ────────────────────────────────────────────────────────────
    if state.get("awaiting_ban"):
        try:
            target_id = int(text)
            target    = get_user(target_id)
            if target:
                new_status = not bool(target["is_banned"])
                set_banned(target_id, new_status)
                action = "заблокирован" if new_status else "разблокирован"
                bot.send_message(user_id, f"✅ Пользователь ID:{target_id} {action}!")
                try:
                    bot.send_message(target_id,
                        "⛔ Вы заблокированы в боте!" if new_status
                        else "✅ Вы разблокированы в боте!")
                except: pass
            else:
                bot.send_message(user_id, "❌ Пользователь не найден!")
        except:
            bot.send_message(user_id, "❌ Введите корректный ID!")
        del user_states[user_id]
        send_main_menu(message)
        return

    send_main_menu(message)


# ========== СОЗДАНИЕ ПЛАТЕЖА ==========

def process_payment(chat_id: int, user_id: int, amount: float, edit_msg_id=None):
    invoice_id, invoice_url = create_invoice(amount, user_id)
    if not invoice_url:
        bot.send_message(user_id, "❌ Ошибка создания платежа. Попробуйте позже.")
        return

    text = (f"💰 ПОПОЛНЕНИЕ БАЛАНСА\n\n"
            f"Сумма: {amount}$\nВалюта: USDT\n\n"
            f"Нажмите «Оплатить» и завершите оплату в CryptoBot.\n"
            f"Баланс пополнится автоматически в течение нескольких секунд.")
    kb = payment_keyboard(invoice_url)

    if edit_msg_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id,
                                  message_id=edit_msg_id, reply_markup=kb)
            msg_id = edit_msg_id
        except:
            sent   = bot.send_message(chat_id, text, reply_markup=kb)
            msg_id = sent.message_id
    else:
        sent   = bot.send_message(chat_id, text, reply_markup=kb)
        msg_id = sent.message_id

    if invoice_id:
        active_invoices[invoice_id] = {
            "user_id":    user_id,
            "amount":     amount,
            "chat_id":    chat_id,
            "message_id": msg_id
        }


# ========== ЗАПУСК ==========

if __name__ == "__main__":
    _open_connection()
    init_db()

    watcher = threading.Thread(target=payment_watcher, daemon=True)
    watcher.start()

    print("=" * 50)
    print(f"🤖 БОТ ЗАПУЩЕН  |  БД: {DB_FILE}")
    print("=" * 50)
    print(f"✅ Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Админы: {ADMIN_IDS}")
    print(f"🔄 Авто-проверка оплаты: каждые 3 сек")
    print("=" * 50)

    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except KeyboardInterrupt:
            print("\n🔴 Бот остановлен")
            _conn.close()
            break
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            time.sleep(5)
