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
bot.remove_command("help")

# -------- Load Cogs --------
async def load_cogs():
    await bot.load_extension("cogs.tickets")
    print("[✅] Loaded cog: cogs.tickets")

    await bot.load_extension("cogs.transcripts")
    print("[✅] Loaded cog: cogs.transcripts")

    await bot.load_extension("cogs.tags")
    print("[✅] Loaded cog: cogs.tags")

    await bot.load_extension("cogs.sticky")
    print("[✅] Loaded cog: cogs.sticky")

    await bot.load_extension("cogs.servers")
    print("[✅] Loaded cog: cogs.servers")

    await bot.load_extension("cogs.moderation")
    print("[✅] Loaded cog: cogs.moderation")

    await bot.load_extension("cogs.ticket_commands")
    print("[✅] Loaded cog: cogs.ticket_commands")

    await bot.load_extension("cogs.roblox")
    print("[✅] Loaded cog: cogs.roblox")

    await bot.load_extension("cogs.Ticketpoints")
    print("[✅] Loaded cog: cogs.Ticketpoints")

    await bot.load_extension("cogs.welcome")
    print("[✅] Loaded cog: cogs.welcome")
    
    await bot.load_extension("cogs.s")
    print("[✅] Loaded cog: cogs.s")
    
    await bot.load_extension("cogs.a")
    print("[✅] Loaded cog: cogs.a")
    
    await bot.load_extension("cogs.vouch")
    print("[✅] Loaded cog: cogs.vouch")
    
    await bot.load_extension("cogs.help")
    print("[✅] Loaded cog: cogs.vouch")
    
    await bot.load_extension("cogs.crypto")
    print("[✅] Loaded cog: cogs.crypto")
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