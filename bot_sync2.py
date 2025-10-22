import telebot, requests, os, json, html, threading, time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://medicina.unicz.it/avvisi"
STATE_FILE = "state.json"

bot = telebot.TeleBot(TOKEN)
lock = threading.Lock()

def fetch_notices():
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
        print("Errore fetch_notices:", e)
        return []

def load_seen():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_seen(ids):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(ids, f, indent=2)
    except Exception as e:
        print("Errore salvataggio:", e)

def check_new(startup=False):
    with lock:
        notices = fetch_notices()
        seen = load_seen()
        new = [n for n in notices if n["link"] not in seen]

        if new:
            for n in new:
                msg = f"🆕 <b>{html.escape(n['title'])}</b>\n📅 {html.escape(n['date'])}\n🔗 <a href='{html.escape(n['link'])}'>Apri avviso</a>"
                bot.send_message(CHAT_ID, msg, parse_mode="HTML", disable_web_page_preview=True)
            save_seen([n["link"] for n in notices])
        else:
            if startup:
                msg = f"🎓 Bot avviato con successo.\n✅ Nessun nuovo avviso al momento.\n🔎 <a href='{URL}'>Controlla manualmente la pagina</a>"
                bot.send_message(CHAT_ID, msg, parse_mode="HTML")
            print("Nessun nuovo avviso.")

@bot.message_handler(commands=["start"])
def start(m):
    bot.reply_to(m, "🎓 Bot avviato con successo.\nUsa /refresh per controllare nuovi avvisi.", parse_mode="HTML")

@bot.message_handler(commands=["refresh"])
def refresh(m):
    bot.reply_to(m, "🔄 Controllo manuale in corso...", parse_mode="HTML")
    threading.Thread(target=check_new).start()

def background_loop():
    while True:
        time.sleep(300)  # ogni 5 minuti
        check_new()

threading.Thread(target=background_loop, daemon=True).start()

bot.send_message(CHAT_ID, "🤖 Bot avviato correttamente. Controllo in corso...", parse_mode="HTML")
check_new(startup=True)
bot.infinity_polling(timeout=60, long_polling_timeout=60)
