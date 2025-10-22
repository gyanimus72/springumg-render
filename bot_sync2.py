cd ~/springumg-actions
cat <<'PY' > check_and_notify.py
import os, json, html, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://medicina.unicz.it/avvisi"
STATE_FILE = "state.json"
USERS_FILE = "users.json"

def send(chat_id, text):
    api = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        requests.post(api, data=data, timeout=15)
    except Exception as e:
        print("Errore Telegram:", e)

def fetch():
    r = requests.get(URL, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []

    # prende solo i veri avvisi con classe specifica
    for avviso in soup.select(".views-row, .avviso-item"):
        title_tag = avviso.select_one("a")
        if not title_tag:
            continue
        title = title_tag.get_text(" ", strip=True)
        href = title_tag.get("href", "").strip()
        if not href.startswith("http"):
            href = "https://medicina.unicz.it" + href
        date_tag = avviso.select_one("time, .date-display-single")
        date = date_tag.get_text(strip=True) if date_tag else ""
        if title:
            items.append({"title": title, "link": href, "date": date})

    return items[:10]

def load_json(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path, "r", encoding="utf-8"))
        except:
            pass
    return default

def save_json(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def notify_new(items, users):
    for n in items:
        msg = f"🆕 <b>{html.escape(n['title'])}</b>"
        if n.get("date"):
            msg += f"\n📅 {html.escape(n['date'])}"
        msg += f"\n🔗 <a href=\"{html.escape(n['link'])}\">Leggi avviso completo</a>"
        for uid in users:
            send(uid, msg)

def main():
    state = load_json(STATE_FILE, {"seen": [], "last_event_ts": None})
    users = load_json(USERS_FILE, [CHAT_ID])

    # registra nuovi utenti
    updates = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates").json()
    for u in updates.get("result", []):
        msg = u.get("message")
        if not msg:
            continue
        chat_id = msg["chat"]["id"]
        username = msg["chat"].get("username", "utente")
        if chat_id not in users:
            users.append(chat_id)
            send(chat_id, f"👋 Benvenuto @{username}!\n🎓 <b>Bot avviato con successo.</b>")
            send(CHAT_ID, f"📩 Nuovo utente registrato: @{username} ({chat_id})")

    save_json(USERS_FILE, users)

    # controlla nuovi avvisi
    notices = fetch()
    seen = set(state["seen"])
    new_items = [n for n in notices if n["link"] not in seen]
    now = datetime.utcnow()

    # messaggio iniziale pulito
    if not state["last_event_ts"]:
        if new_items:
            notify_new(new_items, users)
        else:
            for uid in users:
                send(uid, "🎓 <b>Bot avviato con successo.</b>\n✅ Nessun nuovo avviso al momento.\n🔎 Controlla manualmente la pagina:\nhttps://medicina.unicz.it/avvisi")
        state["last_event_ts"] = now.isoformat()

    elif new_items:
        notify_new(new_items, users)
        state["last_event_ts"] = now.isoformat()
    else:
        last_event = datetime.fromisoformat(state["last_event_ts"]) if state["last_event_ts"] else now
        if (now - last_event) >= timedelta(hours=1):
            for uid in users:
                send(uid, "✅ Nessun nuovo avviso nell’ultima ora.\n📡 Bot attivo e in ascolto.")

    state["seen"] = [n["link"] for n in notices]
    save_json(STATE_FILE, state)

if __name__ == "__main__":
    main()
PY
