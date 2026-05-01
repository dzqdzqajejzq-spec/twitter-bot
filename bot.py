import asyncio
import feedparser
import httpx
import json
from datetime import datetime

# ===================== CONFIG =====================
ACCOUNTS_TO_WATCH = ["mrboogie33", "deadlovesgrave", "fortnite7561798"]  # comptes à surveiller
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1499542369744322694/6v3ceuE1-DbXD4uABdzWhIfCXZHkB1GSPUTyZap5jA4YtHsBwz9heVTOgCwnUrfkmrM-"
CHECK_INTERVAL = 20  # secondes entre chaque vérification
# ==================================================

SEEN_FILE = "seen.json"

NITTER_INSTANCES = [
    "https://nitter.net",
]

def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

async def send_discord(entry, username):
    import re
    image_url = None
    if hasattr(entry, 'media_content') and entry.media_content:
        image_url = entry.media_content[0].get('url')
    elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        image_url = entry.media_thumbnail[0].get('url')

    text = re.sub(r'<[^>]+>', '', entry.summary) if hasattr(entry, 'summary') else entry.title
    text = text.strip()

    tweet_url = entry.link
    tweet_id = tweet_url.split("/")[-1]

    embed = {
        "embeds": [{
            "author": {
                "name": f"@{username}",
                "url": f"https://twitter.com/{username}",
                "icon_url": f"https://unavatar.io/twitter/{username}"
            },
            "description": text[:2000],
            "url": tweet_url,
            "color": 0x1DA1F2,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "🔗 Lien original",
                    "value": f"[Voir le tweet](https://twitter.com/{username}/status/{tweet_id})",
                    "inline": True
                },
                {
                    "name": "📁 Archive",
                    "value": f"[Voir sur Nitter]({tweet_url})",
                    "inline": True
                }
            ],
            "footer": {
                "text": "🔒 Archivé • Visible même après suppression",
                "icon_url": "https://abs.twimg.com/favicons/twitter.3.ico"
            }
        }]
    }

    if image_url:
        embed["embeds"][0]["image"] = {"url": image_url}

    async with httpx.AsyncClient() as http:
        resp = await http.post(DISCORD_WEBHOOK, json=embed)
        if resp.status_code == 204:
            print(f"✅ Envoyé sur Discord : {tweet_url}")
        else:
            print(f"❌ Erreur Discord : {resp.status_code} — {resp.text}")

async def check_account(username, seen_ids):
    for instance in NITTER_INSTANCES:
        try:
            url = f"{instance}/{username}/rss"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(timeout=10, headers=headers) as http:
                r = await http.get(url)
            feed = feedparser.parse(r.text)

            if not feed.entries:
                print(f"⚠️ Pas d'entrées sur {instance}, essai suivant...")
                continue

            for entry in feed.entries[:5]:
                tweet_id = entry.link.split("/")[-1]
                if tweet_id not in seen_ids:
                    print(f"🆕 Nouveau tweet de @{username} : {tweet_id}")
                    await send_discord(entry, username)
                    seen_ids.add(tweet_id)
            return

        except Exception as e:
            print(f"⚠️ Instance {instance} KO : {e}")
            continue

    print(f"❌ Toutes les instances Nitter sont down pour @{username}")

async def main():
    seen_ids = load_seen()
    print(f"🚀 Bot démarré — surveillance de : {ACCOUNTS_TO_WATCH}")
    while True:
        for account in ACCOUNTS_TO_WATCH:
            await check_account(account, seen_ids)
            save_seen(seen_ids)
            await asyncio.sleep(3)
        print(f"⏳ Prochain check dans {CHECK_INTERVAL}s...")
        await asyncio.sleep(CHECK_INTERVAL)

asyncio.run(main())
