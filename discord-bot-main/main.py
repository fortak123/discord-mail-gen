import os
import time
import asyncio
from typing import Optional
from dotenv import load_dotenv

import discord
from discord.ext import commands

# ==== ZÁKLADNÍ NASTAVENÍ ====
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Role & cooldowny
NORMAL_ROLE = "normal"
PREMIUM_ROLE = "premium"

COOLDOWN_NORMAL = 10 * 60   # 10 minut
COOLDOWN_PREMIUM = 1 * 60  # 1 minuta

# ==== AUTOMATICKÉ NAČTENÍ SLUŽEB Z DATA SLOŽKY ====
BASE_DIR = "data"
SERVICES = {}
for file in os.listdir(BASE_DIR):
    if file.endswith(".txt"):
        service_name = os.path.splitext(file)[0]  # název souboru bez .txt
        SERVICES[service_name] = os.path.join(BASE_DIR, file)

last_used = {}
locks = {name: asyncio.Lock() for name in SERVICES.keys()}


def has_role(member: discord.Member, role_name: str) -> bool:
    return any(r.name.lower() == role_name.lower() for r in member.roles)


def get_cooldown_for(member: discord.Member) -> int:
    return COOLDOWN_PREMIUM if has_role(member, PREMIUM_ROLE) else COOLDOWN_NORMAL


async def pop_first_line(path: str) -> Optional[str]:
    try:
        with open(path, "r+", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                return None
            first = lines[0].strip()
            f.seek(0)
            f.writelines(lines[1:])
            f.truncate()
            return first
    except FileNotFoundError:
        return None


def count_lines(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!gen | !stock"))
    print(f"✅ Přihlášen jako {bot.user}")


@bot.command()
async def services(ctx):
    if SERVICES:
        await ctx.send("🔧 Dostupné služby: " + ", ".join(SERVICES.keys()))
    else:
        await ctx.send("⚠️ Žádné služby nebyly nalezeny.")


@bot.command()
async def stock(ctx):
    msg = "**📦 Zásoby:**\n"
    for service, path in SERVICES.items():
        msg += f"{service}: {count_lines(path)}\n"
    await ctx.send(msg)


@bot.command()
async def gen(ctx, service: str = None):
    if not service or service.lower() not in SERVICES:
        await ctx.send("❌ Neznámá služba. Použij `!services`.")
        return

    cooldown = get_cooldown_for(ctx.author)
    now = time.monotonic()
    if ctx.author.id in last_used and now - last_used[ctx.author.id] < cooldown:
        wait = int(cooldown - (now - last_used[ctx.author.id]))
        await ctx.send(f"⏳ Počkej {wait} sekund.")
        return

    path = SERVICES[service.lower()]
    async with locks[service.lower()]:
        code = await pop_first_line(path)

    if not code:
        await ctx.send("⚠️ Žádné údaje nezbyly.")
        return

    try:
        await ctx.author.send(f"🎁 Tvoje údaje pro {service}: `{code}`")
        await ctx.send("✅ Kód ti byl poslán do DM.")
        last_used[ctx.author.id] = now
    except discord.Forbidden:
        await ctx.send("⚠️ Nemohl jsem poslat DM. Zapni si zprávy od členů serveru.")


# ==== Keep alive pro Replit / 24/7 ====
if os.getenv("KEEP_ALIVE") == "1":
    from keep_alive import keep_alive
    keep_alive()

bot.run(TOKEN)
