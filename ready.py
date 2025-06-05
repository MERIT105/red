import random
import time
import json
import asyncio
import nest_asyncio
nest_asyncio.apply()
import re
import httpx
from threading import Timer
from telegram import Update, ChatMember
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ChatMemberHandler,
    ContextTypes, filters, InlineQueryHandler, CallbackQueryHandler
)

BOT_TOKEN = '8051926711:AAHxClEFEC6bkkUGStZ4Q_a1x5QqzRpWVCc'
ALLOWED_CHAT_ID = -1002693558851  # Your group chat ID here
ADMIN_ID = 5712886230             # Your Telegram user ID here
bin_cache = {}

USER_DATA_FILE = "user_data.json"

# BIN Database example
BIN_DATABASE = {
    "555536": {
        "info": "MASTERCARD - DEBIT - UNKNOWN",
        "bank": "JOINT STOCK COMPANY \"ASAKABANK\"",
        "country": "UZBEKISTAN - 🇺🇿"
    },
    "379186": {
        "info": "AMERICAN EXPRESS - CREDIT - PERSONAL GOLD REVOLVE",
        "bank": "AMERICAN EXPRESS",
        "country": "MALAYSIA - 🇲🇾"
    },
    "436388": {
        "info": "MASTERCARD - CREDIT - UNKNOWN",
        "bank": "GLOBAL BANK",
        "country": "USA - 🇺🇸"
    },
    "455445": {
        "info": "VISA - CREDIT - GOLD",
        "bank": "STANDARD CHARTERED BANK",
        "country": "BANGLADESH - 🇧🇩"
    }
}


async def schedule_delete_message(bot, chat_id, message_id, delay=300):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass


async def bin_lookup(bin_number: str):
    if bin_number in bin_cache:
        return bin_cache[bin_number]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                r = await client.get(f"https://bins.su/lookup/{bin_number}")
                if r.status_code == 200:
                    d = r.json()
                    result = {
                        "info": f"{d.get('vendor', 'N/A').upper()} - {d.get('type', 'N/A').upper()} - {d.get('level', 'N/A')}",
                        "bank": d.get("bank", "Unknown Bank"),
                        "country": f"{d.get('country', 'Unknown Country')} - [{d.get('countryInfo', {}).get('emoji', '🏳️')}]"
                    }
                    bin_cache[bin_number] = result
                    return result
            except: pass

            try:
                r = await client.get(f"https://lookup.binlist.net/{bin_number}")
                if r.status_code == 200:
                    d = r.json()
                    result = {
                        "info": f"{d.get('scheme', 'N/A').upper()} - {d.get('type', 'N/A').upper()} - {d.get('brand', 'N/A')}",
                        "bank": d.get("bank", {}).get("name", "Unknown Bank"),
                        "country": f"{d.get('country', {}).get('name', 'Unknown Country')} - [{d.get('country', {}).get('emoji', '🏳️')}]"
                    }
                    bin_cache[bin_number] = result
                    return result
            except: pass
    except: pass

    result = {
        "info": "Unknown - Unknown - Unknown",
        "bank": "Unknown Bank",
        "country": "Unknown Country - [🏳️]"
    }
    bin_cache[bin_number] = result
    return result

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)

user_data = load_user_data()

def get_credits(user_id: int):
    return user_data.get(str(user_id), {}).get("credits", 0)

def change_credits(user_id: int, amount: int):
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = {"credits": 0, "last_daily": 0}
    user_data[uid]["credits"] = max(0, user_data[uid].get("credits", 0) + amount)
    save_user_data(user_data)

async def schedule_delete_message(bot, chat_id, message_id, delay=300):
    def delete_message():
        try:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            pass
    Timer(delay, delete_message).start()

def format_output(card_info, card_type, gateway, status, response, bin_data, checked_by):
    return (
        f"💳 Card: {card_info}\n"
        f"🏷 Card Type: {card_type}\n"
        f"🛠 Gateway: {gateway}\n"
        f"📊 Status: {status}\n"
        f"📣 Response: {response}\n"
        f"🏦 Bank: {bin_data.get('bank', 'N/A')}\n"
        f"🌐 Country: {bin_data.get('country', 'N/A')}\n"
        f"🔢 BIN Info: {bin_data.get('info', 'N/A')}\n"
        f"✅ Checked By: @{checked_by}\n"
        f"━━━━━━━━━━━━━"
    )
    
def simulate_card_auth(card_number: str):
    prefixes = {
        "4": "VISA",
        "5": "MASTERCARD",
        "37": "AMERICAN EXPRESS",
        "6": "DISCOVER"
    }
    card_type = "UNKNOWN"
    for pfx, ctype in prefixes.items():
        if card_number.startswith(pfx):
            card_type = ctype
            break

    outcomes = [
        {"status": "Approved ✅", "response": "Payment method added.", "gateway": "Stripe Auth"},
        {"status": "Decline ❌", "response": "Card was declined", "gateway": "Stripe Auth"},
        {"status": "Approved ❎", "response": "OTP_REQUIRED", "gateway": "Shopify Normal $9.89"},
        {"status": "Decline ❌", "response": "Insufficient funds", "gateway": "PayPal"},
        {"status": "Decline ❌", "response": "Card expired", "gateway": "Authorize.Net"},
        {"status": "Approved ✅", "response": "Transaction approved", "gateway": "CyberSource"},
    ]
    weights = [0.3, 0.4, 0.1, 0.1, 0.05, 0.05]
    choice = random.choices(outcomes, weights)[0]

    return card_type, choice["gateway"], choice["status"], choice["response"]

def format_time():
    return round(random.uniform(15, 25), 2)

def simulate_card_auth(card_number: str):
    stripe_gateways = [
        "Stripe Auth",
        "Stripe 3DS",
        "Stripe Instant",
        "Stripe Proxy EU",
        "Stripe Secure",
        "Stripe API v2"
    ]

    outcomes = [
        {"status": "𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅", "response": "Payment method added."},
        {"status": "𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅", "response": "Transaction approved."},
        {"status": "𝗗𝗲𝗰𝗹𝗶𝗻𝗲 ❌", "response": "Card was declined"},
        {"status": "𝗗𝗲𝗰𝗹𝗶𝗻𝗲 ❌", "response": "Do Not Honor"},
        {"status": "𝗗𝗲𝗰𝗹𝗶𝗻𝗲 ❌", "response": "Insufficient Funds"},
        {"status": "𝗗𝗲𝗰𝗹𝗶𝗻𝗲 ❌", "response": "Expired Card"},
        {"status": "𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅", "response": "3DS Authentication Passed"},
        {"status": "𝗗𝗲𝗰𝗹𝗶𝗻𝗲 ❌", "response": "Incorrect CVV"}
    ]

    gateway = random.choice(stripe_gateways)
    outcome = random.choice(outcomes)

    # Detect brand + emoji
    if card_number.startswith("4"):
        card_type = "VISA 💳"
    elif card_number.startswith("5"):
        card_type = "MASTERCARD 🟥"
    elif card_number.startswith("3"):
        card_type = "AMEX 🟦"
    elif card_number.startswith("6"):
        card_type = "DISCOVER 🟨"
    else:
        card_type = "UNKNOWN 🏳️"

    return card_type, gateway, outcome["status"], outcome["response"]

# old static BIN database removedbin_number):
    dummy_data = {
        "445542": {
            "info": "VISA - CREDIT - BUSINESS",
            "bank": "ABU DHABI ISLAMIC BANK",
            "country": "UNITED ARAB EMIRATES - [🇦🇪]"
        },
        "421234": {
            "info": "Visa - Credit - Platinum",
            "bank": "HDFC Bank",
            "country": "India - [🇮🇳]"
        }
    }
    return dummy_data.get(bin_number, {
        "info": "Unknown - Unknown - Unknown",
        "bank": "Unknown Bank",
        "country": "Unknown Country - [🏳️]"
    })

def generate_card(bin_number):
    card_num = bin_number
    while len(card_num) < 16:
        card_num += str(random.randint(0, 9))
    return card_num
    
async def send_timed_reply(update: Update, text: str):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    sent_msg = await update.message.reply_text(text, parse_mode=None)
    await schedule_delete_message(update.get_bot(), sent_msg.chat_id, sent_msg.message_id)

def insufficient_credits_message():
    return (
        "Insufficient Credits ⚠️\n"
        "Error : You Have Insufficient Credits to Use Me.\n"
        "Recharge Credit For Using Me.\n"
        "━━━━━━━━━━━━━\n"
        "Dm : @Sanjai10_oct_2k03"
    )

# Commands

async def cmd_chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user_id = update.effective_user.id
    checked_by = update.effective_user.username or update.effective_user.first_name or "user"

    if len(context.args) != 1:
        await send_timed_reply(update, "Usage: .chk <card|mm|yy|cvv>")
        return

    try:
        card_number, exp_month, exp_year, cvv = context.args[0].split('|')
    except:
        await send_timed_reply(update, "Invalid format. Use: 5123456789012345|12|25|123")
        return

    if get_credits(user_id) < 1:
        await send_timed_reply(update, "❌ Not enough credits. Use .daily to claim free credits.")
        return

    bin_data = await bin_lookup(card_number[:6])
    card_type, gateway, status, response = simulate_card_auth(card_number)
    card_info = f"{card_number}|{exp_month}|{exp_year}|{cvv}"
    output = "🧾 𝗖𝗖 𝗖𝗛𝗘𝗖𝗞𝗘𝗥:\n" + format_output(card_info, card_type, gateway, status, response, bin_data, checked_by)
    
    await send_timed_reply(update, output)
    change_credits(user_id, -1)

async def cmd_vbv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    uid = str(update.effective_user.id)
    role = user_data.get(uid, {}).get("role", "free")
    if role != "premium" and update.effective_user.id != ADMIN_ID:
        await send_timed_reply(update, "❌ This is a premium command. .\nContact admin to get premium access.")
        return

    if len(context.args) != 1:
        await send_timed_reply(update, "Usage: .vbv <card_number>")
        return
    card_number = context.args[0]
    vbv_status = random.choice(["VBV Enabled ✅", "VBV Not Enabled ❌"])
    bin_data = await bin_lookup(card_number[:6])
    await send_timed_reply(update,
        f"Card: {card_number}\nVBV: {vbv_status}\nBank: {bin_data['bank']}\nCountry: {bin_data['country']}")

async def cmd_slf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    uid = str(update.effective_user.id)
    role = user_data.get(uid, {}).get("role", "free")
    if role != "premium" and update.effective_user.id != ADMIN_ID:
        await send_timed_reply(update, "❌ This is a premium command. \nContact admin to get premium access.")
        return

    credits = get_credits(update.effective_user.id)
    await send_timed_reply(update, f"Hello {update.effective_user.first_name}, you have {credits} credits.")

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    change_credits(update.effective_user.id, 10)
    await send_timed_reply(update, "Admin recharge: 10 credits added.")


    uid = str(update.effective_user.id)
    role = user_data.get(uid, {}).get("role", "free")
    if role != "premium" and update.effective_user.id != ADMIN_ID:
        await send_timed_reply(update, "❌ This is a premium command. \nContact admin to get premium access.")
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "Unknown_User"
    if len(context.args) != 4:
        await send_timed_reply(update, "Usage:  <card_number> <mm> <yy> <cvv>")
        return
    card_number, exp_month, exp_year, cvv = context.args
    bin_number = card_number[:6]
    bin_data = await bin_lookup(bin_number)
    await send_timed_reply(update, f"💳 Processing payment for card ending in {card_number[-4:]}...")
    await asyncio.sleep(2.5)
    change_credits(user_id, 10)
    response = (
        f"✅ Payment Authorized!\n"
        f"━━━━━━━━━━━━━\n"
        f"[💳] Card: {card_number}\n"
        f"[🏦] Bank: {bin_data['bank']}\n"
        f"[🌐] Country: {bin_data['country']}\n"
        f"[🔢] BIN Info: {bin_data['info']}\n"
        f"[💰] Amount Charged: $10.00 USD\n"
        f"[📦] Credits Added: 10\n"
        f"[👤] User: @{username}\n"
        f"[📅] Status: Approved ✅\n"
        f"━━━━━━━━━━━━━\n"
        f"Thank you for your purchase!"
    )
    await send_timed_reply(update, response)

async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    user_id = update.effective_user.id
    uid = str(user_id)
    now = int(time.time())
    user_entry = user_data.get(uid, {"credits": 0, "last_daily": 0})
    if now - user_entry.get("last_daily", 0) < 86400:
        await send_timed_reply(update, "You have already claimed your daily credits. Come back later.")
        return
    change_credits(user_id, 5)
    user_data[uid]["last_daily"] = now
    save_user_data(user_data)
    await send_timed_reply(update, "Daily credits claimed! You received 5 credits.")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID: return

    help_text = """
╭━━━━━━━━━━━━━━━⪧
┃ ⚙️ 𝘾𝙊𝙈𝙈𝘼𝙉𝘿 𝙈𝙀𝙉𝙐
┣━━━━━━━━━━━━━━━⪧

🆓 𝙁𝙍𝙀𝙀 𝘾𝙊𝙈𝙈𝘼𝙉𝘿𝙎
┣ .chk <card|mm|yy|cvv>
┣ .daily
┣ .info
┣ .plans
┣ .help

💎 𝙋𝙍𝙀𝙈𝙄𝙐𝙈 𝘾𝙊𝙈𝙈𝘼𝙉𝘿𝙎
┣ .vbv <card>
┣ .mass <card|mm|yy|cvv> ...
┣ .gen <bin>
┣ .bin <bin>
┣ .all <card|mm|yy|cvv>
┣ .slf

👑 𝘼𝘿𝙈𝙄𝙉 𝘾𝙊𝙈𝙈𝘼𝙉𝘿𝙎
┣ .cr <user_id> <credits>
┣ .setrole <user_id> <free/premium>
╰━━━━━━━━━━━━━━━⪧
"""
    await send_timed_reply(update, help_text.strip())
    
async def cmd_cr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 2:
        await send_timed_reply(update, "Usage: .cr <user_id> <credits>")
        return
    try:
        user_id = int(context.args[0])
        credits = int(context.args[1])
        change_credits(user_id, credits)
        await send_timed_reply(update, f"✅ Credits updated successfully! ??")
    except Exception as e:
        await send_timed_reply(update, f"Error: {str(e)}")


async def cmd_mass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    uid = str(update.effective_user.id)
    role = user_data.get(uid, {}).get("role", "free")
    if role != "premium" and update.effective_user.id != ADMIN_ID:
        await send_timed_reply(update, "❌ This is a premium command.\nContact admin to get premium access.")
        return

    user_id = update.effective_user.id
    checked_by = update.effective_user.username or update.effective_user.first_name or "Unknown_User"
    cards = context.args
    if not cards:
        await send_timed_reply(update, "Usage: .mass <card|mm|yy|cvv> ...")
        return
    if len(cards) > 20:
        cards = cards[:20]
        await send_timed_reply(update, "Only 20 cards allowed per check.")
    if get_credits(user_id) < len(cards):
        await send_timed_reply(update, insufficient_credits_message())
        return

    results = []
    for card in cards:
        parts = card.split('|')
        if len(parts) != 4:
            results.append(f"Invalid format: {card}")
            continue
        card_number, mm, yy, cvv = parts
        full_card = f"{card_number}|{mm}|{yy}|{cvv}"
        _, _, status, response = simulate_card_auth(card_number)
        results.append(f"Card: {full_card}\nStatus: 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌\nResult: {response}\n━━━━━━━━━━━━━")
        change_credits(user_id, -1)

    footer = f"[ϟ] T/t: 0.m 26sec P/x: [Live ⛅]\n[ϟ] Checked By: @{checked_by} [ Premium]\n[⌥] Dev: 𝕊𝕒𝕟𝕛𝕦 - 🍀"
    chunks = [results[i:i+10] for i in range(0, len(results), 10)]
    for chunk in chunks:
        await send_timed_reply(update, "\n".join(chunk) + "\n" + footer)

async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    uid = str(update.effective_user.id)
    role = user_data.get(uid, {}).get("role", "free")
    if role != "premium" and update.effective_user.id != ADMIN_ID:
        await send_timed_reply(update, "❌ This is a premium command.\nContact admin to get premium access.")
        return

    user_id = update.effective_user.id
    checked_by = update.effective_user.username or update.effective_user.first_name or "Unknown_User"

    # Properly parse the card input
    if len(context.args) != 1:
        await send_timed_reply(update, "Usage: .all <card|mm|yy|cvv>")
        return

    try:
        card_number, mm, yy, cvv = context.args[0].split('|')
    except:
        await send_timed_reply(update, "Usage: .all <card|mm|yy|cvv>")
        return

    # Support 4-digit year format like 2029
    if len(yy) == 4:
        yy = yy[2:]

    if get_credits(user_id) < 6:
        await send_timed_reply(update, insufficient_credits_message())
        return

    bin_data = await bin_lookup(card_number[:6])
    card_info = f"{card_number}|{mm}|{yy}|{cvv}"
    outputs = []

    all_auths = [
        {"gateway": "Stripe Auth", "status": "Approved ✅", "response": "Payment method added."},
        {"gateway": "Stripe Auth", "status": "Decline ❌", "response": "Card was declined"},
        {"gateway": "Shopify Normal", "status": "OTP_REQUIRED ❎", "response": "OTP Required"},
        {"gateway": "PayPal", "status": "Decline ❌", "response": "Insufficient funds"},
        {"gateway": "Authorize.Net", "status": "Decline ❌", "response": "Card expired"},
        {"gateway": "CyberSource", "status": "Approved ✅", "response": "Transaction approved"},
    ]

    for auth in all_auths:
        output = format_output(
            card_info=card_info,
            card_type="UNKNOWN",
            gateway=auth["gateway"],
            status=auth["status"],
            response=auth["response"],
            bin_data=bin_data,
            checked_by=checked_by
        )
        outputs.append(output)
        change_credits(user_id, -1)

    for chunk in [outputs[i:i+2] for i in range(0, len(outputs), 2)]:
        await send_timed_reply(update, "\n\n".join(chunk))

async def dot_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    if not update.message.text.startswith('.'):
        return
    parts = update.message.text[1:].split()
    command, context.args = parts[0], parts[1:]
    commands = {
        "mass": cmd_mass,
        "all": cmd_all,
        "chk": cmd_chk,
                "vbv": cmd_vbv,
        "slf": cmd_slf,
                "daily": cmd_daily,
        "info": cmd_info,
        "plans": cmd_plans,
        "help": cmd_help,
        "cr": cmd_cr,
        "gen": cmd_gen,
        "bin": cmd_bin,
                "setrole": cmd_setrole
    }
    handler = commands.get(command.lower())
    if handler:
        await handler(update, context)

# Welcome message on user join

async def on_user_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        # Give 5 free credits on join
        uid = str(member.id)
        if uid not in user_data:
            user_data[uid] = {"credits": 5, "last_daily": 0}
            save_user_data(user_data)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Welcome {member.full_name}! You have been awarded 5 free credits to start."
        )

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if result.new_chat_member.status == ChatMember.MEMBER and result.chat.id == ALLOWED_CHAT_ID:
        await context.bot.send_message(
            chat_id=result.chat.id,
            text=f"Welcome {result.new_chat_member.user.full_name} to the group!"
        )
    elif result.old_chat_member.status == ChatMember.MEMBER and result.new_chat_member.status in ['left', 'kicked']:
        await context.bot.send_message(
            chat_id=result.chat.id,
            text=f"Goodbye {result.old_chat_member.user.full_name}."
        )

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # For simplicity, no inline implementation now
    pass
    
    async def send_timed_reply(update: Update, text: str):
         await update.message.reply_text(text, parse_mode=None)

async def cmd_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    uid = str(update.effective_user.id)
    role = user_data.get(uid, {}).get("role", "free")
    if role != "premium" and update.effective_user.id != ADMIN_ID:
        await send_timed_reply(update, "❌ This is a premium command. \nContact admin to get premium access.")
        return

    if len(context.args) != 1:
        await send_timed_reply(update, "Usage: .gen <bin>")
        return
    bin_number = context.args[0]
    if len(bin_number) != 6 or not bin_number.isdigit():
        await send_timed_reply(update, "Invalid BIN. Must be 6 digits.")
        return

    user = update.effective_user
    username = user.username or user.first_name or "Unknown_User"

    bin_data = await bin_lookup(bin_number)
    info = bin_data.get("info", "N/A")
    bank = bin_data.get("bank", "N/A")
    country = bin_data.get("country", "N/A")

    count = 10
    cards = []
    for _ in range(count):
        card = generate_card(bin_number)
        mm = str(random.randint(1, 12)).zfill(2)
        yy = str(random.randint(23, 30))
        cvv = str(random.randint(100, 999))
        cards.append(f"{card}|{mm}|20{yy}|{cvv}")

    t_time = round(random.uniform(1, 3), 2)

    text = (
        f"Bin : {bin_number}\n"
        f"VBV : True\n"
        f"Amount : 10\n\n"
        + "\n".join(cards) + "\n\n"
        f"Info : {info}\n"
        f"Bank : {bank}\n"
        f"Country : {country}\n"
        f"━━━━━━━━━━━━━\n"
        f"Time : {t_time} sec\n"
        f"Req By : users @{username}"
    )
    await send_timed_reply(update, text)

async def cmd_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    uid = str(update.effective_user.id)
    role = user_data.get(uid, {}).get("role", "free")
    if role != "premium" and update.effective_user.id != ADMIN_ID:
        await send_timed_reply(update, "❌ This is a premium command. \nContact admin to get premium access.")
        return

    if len(context.args) != 1:
        await send_timed_reply(update, "Usage: .bin <bin>")
        return
    bin_number = context.args[0]
    if len(bin_number) != 6 or not bin_number.isdigit():
        await send_timed_reply(update, "Invalid BIN. Must be 6 digits.")
        return

    user = update.effective_user
    username = user.username or user.first_name or "Unknown_User"

    bin_data = await bin_lookup(bin_number)
    info = bin_data.get("info", "N/A").upper()
    bank = bin_data.get("bank", "N/A")
    country_full = bin_data.get("country", "N/A")

    parts = info.split(" - ")
    brand = parts[0] if len(parts) > 0 else "N/A"
    ctype = parts[1] if len(parts) > 1 else "N/A"
    level = parts[2] if len(parts) > 2 else "N/A"

    emoji_match = re.search(r"\[([^\]]+)\]", country_full)
    emoji = emoji_match.group(1) if emoji_match else ""
    country_name = country_full.split(" - ")[0] if " - " in country_full else country_full

    text = (
        "╔══════════ BIN INFO ══════════╗\n"
        f"║ BIN     : {bin_number.ljust(18)}║\n"
        f"║ Brand   : {brand.ljust(18)}║\n"
        f"║ Type    : {ctype.ljust(18)}║\n"
        f"║ Level   : {level.ljust(18)}║\n"
        f"║ Bank    : {bank.ljust(18)}║\n"
        f"║ Country : {emoji} {country_name.ljust(14)}║\n"
        "╚═════════════════════════════╝\n"
        f"👤 User: @{username}"
    )
    await send_timed_reply(update, text)


from telegram import InlineKeyboardMarkup, InlineKeyboardButton

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "N/A"
    credits = get_credits(user_id)
    uid = str(user_id)
    role = user_data.get(uid, {}).get("role", "free").upper()

    info_text = f"""OxEnv | {user_id} Info
━━━━━━━━━━━━━━
[ϟ] First Name : {user.first_name}
[ϟ] ID : {user_id}
[ϟ] Username : @{username}
[ϟ] Profile Link : tg://user?id={user_id}
[ϟ] TG Restrictions : False
[ϟ] TG Scamtag : False
[ϟ] TG Premium : False
[ϟ] Status : {role}
[ϟ] Credit : {credits}
[ϟ] Plan : {'N/A' if role == 'FREE' else 'Premium'}
"""

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 View Plans", callback_data="show_plans")]
    ])
    await update.message.reply_text(info_text, reply_markup=buttons)

async def cmd_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    await show_plans(update, context)

async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plans_text = """
💎 PREMIUM ACCESS PLANS 💳
━━━━━━━━━━━━━━
• ₹20   → 100 credits
• ₹50   → 250 credits
• ₹100  → 1000 credits
• ₹200  → Unlimited credits
━━━━━━━━━━━━━━
🔗 Contact: @Sanjai10_oct_2k03 to upgrade your plan.
"""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(plans_text)
    else:
        await send_timed_reply(update, plans_text)

async def cmd_setrole(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 2:
        await send_timed_reply(update, "Usage: .setrole <user_id> <role> (user or admin)")
        return
    user_id, role = context.args
    if role not in ['free', 'premium']:
        await send_timed_reply(update, "Role must be 'user' or 'admin'.")
        return
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = {"credits": 0, "last_daily": 0}
    user_data[uid]["role"] = role
    save_user_data(user_data)
    await send_timed_reply(update, f"✅ Role for user {user_id} set to {role}.")

    print("Bot started...")
    await app.run_polling()

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS & filters.Chat(ALLOWED_CHAT_ID), on_user_join))
    app.add_handler(MessageHandler(filters.TEXT & filters.Chat(ALLOWED_CHAT_ID), dot_commands))
    app.add_handler(CommandHandler("cr", cmd_buy))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("start", cmd_help))
    app.add_handler(CommandHandler("gen", cmd_gen))
    app.add_handler(CommandHandler("bin", cmd_bin))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("plans", cmd_plans))
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^show_plans$"))
    app.add_handler(InlineQueryHandler(inline_query_handler))

    print("Bot started...")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()

    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        pass










