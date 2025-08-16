import os
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands
from web.server import make_app
from utils.constants import PORT

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="$", intents=intents)

# -------- Load Cogs --------
async def load_cogs():
    await bot.load_extension("cogs.tickets")
    await bot.load_extension("cogs.transcripts")
    await bot.load_extension("cogs.tags")
    await bot.load_extension("cogs.sticky")
    await bot.load_extension("cogs.servers")
    await bot.load_extension("cogs.moderation")
    await bot.load_extension("cogs.ticket_commands")
    await bot.load_extension("cogs.help")  # ✅ aligned correctly
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

async def run_web():
    import aiohttp.web
    app = make_app()
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on :{PORT}")

async def main():
    await load_cogs()
    await asyncio.gather(
        bot.start(os.getenv("TOKEN")),
        run_web()
    )

if __name__ == "__main__":
    asyncio.run(main())