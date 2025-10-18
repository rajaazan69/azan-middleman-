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

# -------- Load Cogs Recursively --------
async def load_cogs():
    cog_folder = "cogs"
    for root, _, files in os.walk(cog_folder):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                # Convert file path to module path
                path = os.path.join(root, file)
                module = path.replace(os.sep, ".").replace(".py", "")
                try:
                    await bot.load_extension(module)
                    print(f"[✅] Loaded cog: {module}")
                except Exception as e:
                    print(f"[❌] Failed to load {module}: {e}")

# -------- Startup Event --------
@bot.event
async def on_ready():
    if getattr(bot, "startup_done", False):
        return  # Avoid running multiple times on reconnects
    bot.startup_done = True

    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

    # ---- Send weekly quota if none exists ----
    quota_cog = bot.get_cog("Quota")
    if quota_cog:
        await quota_cog.send_quota_on_startup()

    # ---- Send/update middleman leaderboard ----
    mm_lb_cog = bot.get_cog("MiddlemanLeaderboard")
    if mm_lb_cog:
        for guild in bot.guilds:  # Loop through all guilds the bot is in
            await mm_lb_cog.update_or_create_lb(guild)

# -------- Web server --------
async def run_web():
    import aiohttp.web
    app = make_app()
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on :{PORT}")

# -------- Main --------
async def main():
    await load_cogs()
    await asyncio.gather(
        bot.start(os.getenv("TOKEN")),
        run_web()
    )

if __name__ == "__main__":
    asyncio.run(main())