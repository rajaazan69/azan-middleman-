import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, TextInput, Modal
from discord import Embed, ButtonStyle, TextStyle, ChannelType, Permissions
import pymongo
import requests
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import re

# Load env
load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID"))
MIDDLEMAN_ROLE = int(os.getenv("MIDDLEMAN_ROLE"))
TICKET_CATEGORY = int(os.getenv("TICKET_CATEGORY"))
TRANSCRIPT_CHANNEL = int(os.getenv("TRANSCRIPT_CHANNEL"))
LEADERBOARD_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID"))
LEADERBOARD_MESSAGE_ID = int(os.getenv("LEADERBOARD_MESSAGE_ID"))
BASE_URL = os.getenv("BASE_URL")

# MongoDB
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client.get_database("discordBotDB")
ticketsCollection = db.get_collection("tickets")
transcriptsCollection = db.get_collection("transcripts")
clientPointsCollection = db.get_collection("clientPoints")

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="$", intents=intents)
stickyMap = {}  # Sticky messages

# ---------- Roblox Game Data ----------
gameData = {
    "gag": {
        "name": "GAG",
        "publicLink": "https://www.roblox.com/games/126884695634066/Grow-a-Garden?sortFilter=3",
        "privateLink": "https://www.roblox.com/share?code=2daaf72e32f63840b588d65a5cff53a7&type=Server",
        "thumbnail": "https://cdn.discordapp.com/attachments/1373070247795495116/1396644967665111142/IMG_6743.jpg"
    },
    "mm2": {
        "name": "MM2",
        "publicLink": "https://www.roblox.com/games/66654135/Murder-Mystery-2?sortFilter=3",
        "privateLink": "https://www.roblox.com/share?code=c1ac8abd3c27354e9db3979aad38b842&type=Server",
        "thumbnail": "https://cdn.discordapp.com/attachments/1373070247795495116/1396644976829661194/IMG_6744.jpg"
    },
    "sab": {
        "name": "SAB (Steal a Brainrot)",
        "publicLink": "https://www.roblox.com/games/109983668079237/Steal-a-Brainrot?sortFilter=3",
        "privateLink": "https://www.roblox.com/share?code=d99e8e73482e8342a3aa30fb59973322&type=Server",
        "thumbnail": "https://cdn.discordapp.com/attachments/1373070247795495116/1396644973134348288/IMG_6745.jpg"
    }
}

# ---------- EVENTS ----------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # Preload thumbnails
    for game in gameData.values():
        requests.get(game["thumbnail"])
        print(f"Preloaded: {game['name']} thumbnail")

# Sticky message handler
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.type != ChannelType.text:
        return
    sticky = stickyMap.get(message.channel.id)
    if sticky:
        old = None
        try:
            old = await message.channel.fetch_message(sticky["messageId"])
            await old.delete()
        except:
            pass
        new_msg = await message.channel.send(sticky["message"])
        stickyMap[message.channel.id]["messageId"] = new_msg.id
    await bot.process_commands(message)

# Welcome message
@bot.event
async def on_member_join(member):
    welcomeChannelId = 1373078546422960148
    vouchesChannelId = 1373027974827212923
    proofsChannelId = 1373027988391596202
    channel = member.guild.get_channel(welcomeChannelId)
    if not channel:
        return
    embed = Embed(color=0x000000)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.description = (
        f"Welcome to **Azan’s Middleman Services** {member.mention}!\n\n"
        f"To view vouches: <#{vouchesChannelId}>\n"
        f"To view proofs: <#{proofsChannelId}>\n\n"
        f"We hope you enjoy your stay here!"
    )
    embed.set_footer(text=f"User ID: {member.id}")
    embed.timestamp = datetime.utcnow()
    await channel.send(embed=embed)

# ---------- COMMANDS ----------

# Moderation Commands
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided."):
    await member.ban(reason=reason)
    embed = Embed(title="User Banned", color=0x000000)
    embed.add_field(name="**User**", value=f"{member} (<@{member.id}>)", inline=True)
    embed.add_field(name="**Reason**", value=reason)
    embed.set_footer(text=f"Moderator: {ctx.author}")
    embed.timestamp = datetime.utcnow()
    await ctx.send(embed=embed)

# Kick
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided."):
    await member.kick(reason=reason)
    embed = Embed(title="User Kicked", color=0x000000)
    embed.add_field(name="**User**", value=f"{member} (<@{member.id}>)", inline=True)
    embed.add_field(name="**Reason**", value=reason)
    embed.set_footer(text=f"Moderator: {ctx.author}")
    embed.timestamp = datetime.utcnow()
    await ctx.send(embed=embed)

# Timeout (mute)
@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, duration: str, *, reason="No reason provided."):
    import re, asyncio
    units = {"s":1, "m":60, "h":3600, "d":86400}
    match = re.match(r"(\d+)([smhd])", duration)
    if not match:
        await ctx.send("❌ Invalid duration format. Example: 10m, 1h")
        return
    t, u = match.groups()
    seconds = int(t) * units[u]
    await member.timeout(discord.utils.utcnow() + discord.timedelta(seconds=seconds), reason=reason)
    embed = Embed(title="User Timed Out", color=0x000000)
    embed.description = f"**User:** {member} ({member})\n**Duration:** {duration}\n**Reason:** {reason}\n**Moderator:** {ctx.author}"
    embed.timestamp = datetime.utcnow()
    await ctx.send(embed=embed)

# Unlock / Lock / Warn / etc. - you can continue the same pattern with @bot.command()

# Sticky Message Command
@bot.command()
async def setsticky(ctx, *, message):
    stickyMap[ctx.channel.id] = {"message": message, "messageId": None}
    sent = await ctx.send(message)
    stickyMap[ctx.channel.id]["messageId"] = sent.id
    await ctx.send(f"✅ Sticky message set in {ctx.channel.mention}")

# Roblox info command
@bot.command()
async def i(ctx, username):
    try:
        res = requests.post("https://users.roblox.com/v1/usernames/users", json={"usernames":[username], "excludeBannedUsers": False}).json()
        user = res["data"][0]
        uid = user["id"]
        profile = requests.get(f"https://users.roblox.com/v1/users/{uid}").json()
        followers = requests.get(f"https://friends.roblox.com/v1/users/{uid}/followers/count").json()
        following = requests.get(f"https://friends.roblox.com/v1/users/{uid}/followings/count").json()
        avatar = requests.get(f"https://thumbnails.roblox.com/v1/users/avatar?userIds={uid}&size=720x720&format=Png&isCircular=false").json()
        embed = Embed(title="Roblox User Information", color=0x000000)
        embed.set_thumbnail(url=f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=150x150&format=Png&isCircular=true")
        embed.add_field(name="Display Name", value=profile["displayName"])
        embed.add_field(name="Username", value=profile["name"])
        embed.add_field(name="User ID", value=str(uid))
        embed.add_field(name="Account Created", value=profile["created"])
        embed.add_field(name="Followers", value=str(followers.get("count","N/A")))
        embed.add_field(name="Following", value=str(following.get("count","N/A")))
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send("❌ Failed to fetch user info.")
        print(e)

# TODO: You can continue adding all ticket buttons, modals, leaderboard, server selection, transcript generation following the same structure using discord.py 2.x UI and commands.

bot.run(TOKEN)
