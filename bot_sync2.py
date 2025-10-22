import os, json, html, time, threading, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import telebot

# === CONFIG ===
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://medicina.unicz.it/avvisi"
STATE = "last_seen.json"
USERS = "users.json"

bot = telebot.TeleBot(TOKEN)
lock = threading.Lock()

# === FUNZIONI BASE ===

def fetch_notices():
    """Estrae gli avvisi più recenti dal sito UMG Medicina."""
    try:
        r = requests.get(URL, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for li in soup.select(".avviso-item, li"):
            title = li.get_text(strip=True)
            link = li.find("a")["href"] if li.find("a") else URL
            date = li.find("time").get_text(strip=True) if li.find("time") else ""
            if title:
                items.append({"title": title, "link": link, "date": date})
        return items[:10]
    except Exception as e:
        print("❌ Errore fetch_notices:", e)
        return []

def load_seen():
    if os.path.exists(STATE):
        try:
            with open(STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_seen(ids):
    try:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(ids, f, indent=2)
    except Exception as e:
        print("❌ Errore salvataggio:", e)

def load_users():
    if os.path.exists(USERS):
        try:
            with open(USERS, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_users(users):
    try:
        with open(USERS, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print("❌ Errore salvataggio utenti:", e)

# === CONTROLLO AVVISI ===

def check_new(startup=False):
    with lock:
        notices = fetch_notices()
        seen = load_seen()
        new = [n for n in notices if n["link"] not in seen]

        if new:
            for n in new:
                msg = (
                    f"🆕 <b>{html.escape(n['title'])}</b>\n"
                    f"📅 {html.escape(n['date'])}\n"
                    f"🔗 <a href=\"{html.escape(n['link'])}\">Apri avviso</a>"
                )
                bot.send_message(CHAT_ID, msg, parse_mode="HTML", disable_web_page_preview=True)
            save_seen([n["link"] for n in notices])
        elif startup:
            msg = (
                "✅ Nessun nuovo avviso al momento.\n"
                f"🔎 <a href=\"{URL}\">Controlla manualmente la pagina</a>"
            )
            bot.send_message(CHAT_ID, msg, parse_mode="HTML")

# === GESTIONE UTENTI ===

@bot.message_handler(commands=["start"])
def start(m):
    users = load_users()
    if m.from_user.id not in users:
        users.append(m.from_user.id)
        save_users(users)
        bot.send_message(CHAT_ID, f"📩 Nuovo utente registrato: @{m.from_user.username} ({m.from_user.id})")
    bot.reply_to(
        m,
        f"🎓 Bot avviato con successo.\n"
        f"✅ Nessun nuovo avviso al momento.\n"
        f"🔎 <a href=\"{URL}\">Controlla manualmente la pagina</a>",
        parse_mode="HTML"
    )

@bot.message_handler(commands=["refresh"])
def refresh(m):
    bot.reply_to(m, "🔄 Controllo manuale in corso...", parse_mode="HTML")
    check_new()

# === LOOP ORARIO ===

def schedule_loop():
    """Controllo automatico ogni 5 minuti"""
    while True:
        check_new()
        time.sleep(300)

threading.Thread(target=schedule_loop, daemon=True).start()

# === AVVIO ===

bot.send_message(CHAT_ID, "🤖 Bot avviato correttamente.\nControllo in corso...", parse_mode="HTML")
check_new(startup=True)
print("✅ Bot in esecuzione su Render...")

bot.infinity_polling(timeout=60, long_polling_timeout=60)

# Mantiene il processo attivo su Render
while True:
    time.sleep(3600)
