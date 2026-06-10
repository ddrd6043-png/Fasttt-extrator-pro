import os
import json
import random
import asyncio
import threading
import aiohttp
from http.server import HTTPServer, BaseHTTPRequestHandler
import time

BOT_TOKEN = "8535220223:AAF9OAlQpNISXFTq4NoKvVAbWECrxAuRKkg"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

channels = [
    {"name": "Main Channel",        "id": "@legend99loots",     "url": "https://t.me/legend99loots"},
    {"name": "Backup Channel",      "id": "-1003866614306",     "url": "https://t.me/+oAZlJUvq2C9iMzE1"},
    {"name": "Legend99 Chats",      "id": "@legend99chats",     "url": "https://t.me/legend99chats"},
    {"name": "Legend99 Tracking",   "id": "@legend99tracking",  "url": "https://t.me/legend99tracking"},
    {"name": "TG Legend99",         "id": "@tglegend99",        "url": "https://t.me/tglegend99"},
]

indian_ips = [
    '115.113.165.98', '1.7.81.168', '202.88.149.10', '49.44.129.106',
    '202.88.149.230', '14.142.18.82', '202.88.156.198', '122.184.140.153',
    '38.10.0.40', '116.119.109.244', '49.44.183.1', '182.77.55.10', '14.139.85.10'
]

# ── Health Server (Turant Start) ──────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot Running!")
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"✅ Health server LIVE on port {port}")
    server.serve_forever()

# ── Bot Functions ──────────────────────────────────────────
async def send_message(session, chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        await session.post(f"{API_URL}sendMessage", json=payload, timeout=aiohttp.ClientTimeout(total=10))
    except Exception as e:
        print(f"Send error: {e}")

async def is_user_member(session, user_id, channel_id):
    try:
        async with session.get(
            f"{API_URL}getChatMember?chat_id={channel_id}&user_id={user_id}",
            timeout=aiohttp.ClientTimeout(total=10)
        ) as r:
            data = await r.json()
            if data.get("ok"):
                status = data["result"].get("status", "left").lower()
                return status in ["member", "administrator", "creator", "restricted"]
    except:
        pass
    return False

async def check_all_channels(session, user_id):
    tasks = [is_user_member(session, user_id, ch["id"]) for ch in channels]
    results = await asyncio.gather(*tasks)
    return all(results)

async def send_force_join_message(session, chat_id):
    text = (
        "🚫 <b>Access Denied!</b>\n\n"
        "⛔ You are <b>not allowed</b> to use this bot.\n\n"
        "📢 To unlock the bot, you must join <b>all 5 channels</b> below:\n\n"
        "👇 Click each button to join, then press <b>✅ Verify Now</b>."
    )
    keyboard = {"inline_keyboard": []}
    for ch in channels:
        keyboard["inline_keyboard"].append([{"text": f"🔗 Join {ch['name']}", "url": ch["url"]}])
    keyboard["inline_keyboard"].append([{"text": "✅ Verify Now", "callback_data": "verify_join"}])
    await send_message(session, chat_id, text, keyboard)

async def extract_redirects(session, url):
    chain = []
    current_url = url
    for _ in range(15):
        random_ip = random.choice(indian_ips)
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36",
            "X-Forwarded-For": random_ip,
            "Client-IP": random_ip,
            "X-Real-IP": random_ip
        }
        try:
            async with session.get(
                current_url,
                headers=headers,
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                chain.append(current_url)
                if r.status in (301, 302, 303, 307, 308) and "Location" in r.headers:
                    current_url = r.headers["Location"]
                    continue
                break
        except:
            break
    return chain

async def handle_update(session, update):
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        user_id = cb["from"]["id"]
        cb_id = cb["id"]

        await session.get(f"{API_URL}answerCallbackQuery?callback_query_id={cb_id}&text=⏳ Checking membership...")

        if cb.get("data") == "verify_join":
            if await check_all_channels(session, user_id):
                await send_message(session, chat_id, (
                    "🌟 <b>Welcome to LEGEND 99 Extractor Bot!</b>\n\n"
                    "✅ <b>Verification Successful!</b>\n\n"
                    "⚡ Now paste any short link or redirect link to extract it!"
                ))
            else:
                await send_force_join_message(session, chat_id)
        return

    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "").strip()

    if message["chat"]["type"] != "private":
        return

    if text in ["/start", "/help"]:
        if await check_all_channels(session, user_id):
            await send_message(session, chat_id, (
                "🌟 <b>Welcome to LEGEND 99 Extractor Bot!</b>\n\n"
                "🔗 Paste any short or redirect link to get started. ⚡"
            ))
        else:
            await send_force_join_message(session, chat_id)
        return

    if not await check_all_channels(session, user_id):
        await send_force_join_message(session, chat_id)
        return

    if text.startswith("http://") or text.startswith("https://"):
        await send_message(session, chat_id, "⏳ <b>Processing your link...</b>\n🔄 Extracting redirect chain, please wait...")

        chain = await extract_redirects(session, text)

        if len(chain) > 1:
            reply = "✅ <b>Redirect Chain Extracted Successfully!</b>\n\n🔗 <b>Your Link Analysis:</b>\n\n"
            for i, link in enumerate(chain, 1):
                reply += f"🔵 <b>Step {i}:</b> <code>{link}</code>\n\n"
            reply += "✨ <b>All Done!</b> ✨"
        else:
            reply = (
                "⚠️ <b>No Redirect Found</b>\n\n"
                "This link does not redirect or is not a short link.\n\n"
                f"🔗 <b>Link:</b> <code>{text}</code>"
            )
        await send_message(session, chat_id, reply)
    else:
        await send_message(session, chat_id, (
            "❌ <b>Invalid Link</b>\n\n"
            "Please paste a valid URL only.\n"
            "Example: <code>https://shortlink.com/abc</code>"
        ))

# ── Main ───────────────────────────────────────────────────
async def main():
    print("🚀 Bot starting...")
    
    # PEHLE Health server start karo (turant port bind)
    t = threading.Thread(target=run_health_server)
    t.daemon = True
    t.start()
    
    # Thoda wait karo taaki port bind ho jaye
    time.sleep(2)
    print("✅ Health server thread started")
    
    offset = None
    async with aiohttp.ClientSession() as session:
        print("✅ Bot polling started...")
        while True:
            try:
                url = f"{API_URL}getUpdates?timeout=10"
                if offset:
                    url += f"&offset={offset}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    data = await r.json()
                    if data.get("ok"):
                        updates = data["result"]
                        if updates:
                            await asyncio.gather(*[handle_update(session, u) for u in updates])
                            offset = updates[-1]["update_id"] + 1
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())