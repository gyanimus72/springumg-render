import os, json, html, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://medicina.unicz.it/avvisi"
STATE_FILE = "state.json"

def send_message(text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    })

def fetch_notices():
    try:
        r = requests.get(URL, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        # Cerca solo i blocchi di avviso reali
        for div in soup.select(".avviso-item"):
            title_tag = div.find("a")
            title = title_tag.get_text(strip=True) if title_tag else None
            link = title_tag["href"] if title_tag and title_tag.has_attr("href") else URL
            date = div.find("time").get_text(strip=True) if div.find("time") else ""
            if title:
                items.append({"title": title, "link": link, "date": date})
        return items
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

def check_new():
    notices = fetch_notices()
    seen = load_seen()
    new = [n for n in notices if n["link"] not in seen]

    if new:
        for n in new:
            msg = f"🆕 <b>{html.escape(n['title'])}</b>\n📅 {html.escape(n['date'])}\n🔗 <a href=\"{html.escape(n['link'])}\">Apri avviso</a>"
            send_message(msg)
        save_seen([n["link"] for n in notices])
    else:
        send_message("✅ Nessun nuovo avviso trovato.")

if __name__ == "__main__":
    send_message("🤖 Bot avviato correttamente.\nControllo in corso...")
    check_new()
