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
# ---------- TICKET MODAL ----------
class TicketModal(Modal):
    def __init__(self):
        super().__init__(title="Create a Ticket")
        self.add_item(TextInput(label="What is Your Side of the Trade?", custom_id="q2"))
        self.add_item(TextInput(label="What is Other Side of the Trade?", custom_id="q3"))
        self.add_item(TextInput(label="Paste The Other Trader's Full User ID", custom_id="q4"))

    async def callback(self, interaction: discord.Interaction):
        # Check if user already has a ticket
        existing = None
        for c in interaction.guild.channels:
            if getattr(c, "category_id", None) == TICKET_CATEGORY:
                perms = c.permissions_for(interaction.user)
                if perms.view_channel:
                    existing = c
                    break
        if existing:
            await interaction.response.send_message(f"❌ You already have an open ticket: {existing.mention}", ephemeral=True)
            return

        q2 = self.children[0].value
        q3 = self.children[1].value
        q4 = self.children[2].value
        isValidId = re.fullmatch(r"\d{17,19}", q4)
        targetMention = f"<@{q4}>" if isValidId else "Unknown User"

        # Permissions
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            OWNER_ID: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            MIDDLEMAN_ROLE: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        if isValidId:
            member = interaction.guild.get_member(int(q4))
            if member:
                overwrites[member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        ticket_channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=discord.utils.get(interaction.guild.categories, id=TICKET_CATEGORY),
            overwrites=overwrites
        )

        await ticketsCollection.insert_one({
            "channelId": ticket_channel.id,
            "user1": interaction.user.id,
            "user2": int(q4) if isValidId else None
        })

        embed = Embed(title="Middleman Request", color=0xFFFFFF)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="**User 1**", value=f"<@{interaction.user.id}>", inline=True)
        embed.add_field(name="**User 2**", value=targetMention, inline=True)
        embed.add_field(name="\u200B", value="\u200B")
        embed.add_field(name="**Trade Details**", value=f"> {q2}")
        embed.add_field(name="**User 1 is giving**", value=f"> {q2}")
        embed.add_field(name="**User 2 is giving**", value=f"> {q3}")
        embed.set_footer(text=f"Ticket by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        embed.timestamp = datetime.utcnow()

        infoEmbed = Embed(color=0xFFFFFF)
        infoEmbed.description = (
            f"Please wait for our **Middleman Team** to assist you.\n"
            f"Make sure to abide by all the rules and **vouch when the trade is over**."
        )

        await ticket_channel.send(content=f"{interaction.user.mention} made a ticket with {targetMention}. Please wait until <@{OWNER_ID}> assists you.", embeds=[infoEmbed, embed])
        await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)

# Command to open modal
@bot.command()
async def ticket(ctx):
    await ctx.send_modal(TicketModal())

# ---------- SERVER SELECTION BUTTONS ----------
class ServerSelectView(View):
    def __init__(self, game_key: str):
        super().__init__(timeout=None)
        game = gameData[game_key]
        self.add_item(Button(label="Join Public Server", style=ButtonStyle.primary, custom_id=f"public_{game_key}"))
        self.add_item(Button(label="Join Private Server", style=ButtonStyle.secondary, custom_id=f"private_{game_key}"))

@bot.command()
async def servers(ctx, game: str):
    game = game.lower()
    if game not in gameData:
        await ctx.send("❌ Invalid game key!")
        return
    g = gameData[game]
    embed = Embed(title=f"Server Options for {g['name']}", description="**Please Choose Which Server You Would Be The Most Comfortable For The Trade In. Confirm The Middleman Which Server To Join**", color=0x000000)
    embed.set_image(url=g["thumbnail"])
    await ctx.send(embed=embed, view=ServerSelectView(game))

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if not interaction.type == discord.InteractionType.component:
        return
    custom_id = interaction.data["custom_id"]
    if custom_id.startswith("public_") or custom_id.startswith("private_"):
        typ, game = custom_id.split("_")
        g = gameData.get(game)
        if not g:
            await interaction.response.send_message("❌ Unknown game!", ephemeral=True)
            return
        isPublic = typ == "public"
        embed = Embed(title="Server Chosen", color=0x000000)
        embed.description = f"**{interaction.user} has chosen to trade in the {'Public' if isPublic else 'Private'} Server.**"
        embed.add_field(name="🔗 Click to Join:", value=f"[{'Public' if isPublic else 'Private'} Server Link]({g['publicLink'] if isPublic else g['privateLink']})")
        embed.set_image(url=g["thumbnail"])
        embed.timestamp = datetime.utcnow()
        await interaction.response.edit_message(embed=embed, view=None)

# ---------- TRANSCRIPT HANDLER ----------
async def handle_transcript(ctx_channel, interaction_user):
    from discord_html_transcripts import create_transcript
    import os
    import pathlib

    messages = [m async for m in ctx_channel.history(limit=None)]
    messages.sort(key=lambda x: x.created_at)
    participants = {m.author.id: messages.count(m) for m in messages if not m.author.bot}

    transcript_folder = pathlib.Path("transcripts")
    transcript_folder.mkdir(exist_ok=True)
    transcript_file = transcript_folder / f"{ctx_channel.id}.html"

    transcript = await create_transcript(ctx_channel, limit=-1, return_type="file", file_name=transcript_file.name, save_images=True)
    transcript_file.write_bytes(transcript.fp.read())

    await interaction_user.send(f"Transcript for {ctx_channel.name} ready!", file=discord.File(transcript_file))

@bot.command()
async def transcript(ctx):
    if ctx.channel.category_id != TICKET_CATEGORY:
        await ctx.send("❌ You can only use this inside ticket channels.")
        return
    await handle_transcript(ctx.channel, ctx.author)
    await ctx.send("✅ Transcript sent to your DMs.")
    # ---------- LEADERBOARD POINTS ----------
@bot.command()
async def logpoints(ctx, user: discord.User):
    """Logs 1 point for the given user and updates leaderboard"""
    try:
        # Fetch current leaderboard from DB
        leaderboard = await leaderboardCollection.find_one({"guild_id": ctx.guild.id})
        if not leaderboard:
            leaderboard = {"guild_id": ctx.guild.id, "points": {}}

        points = leaderboard["points"]
        user_id = str(user.id)
        points[user_id] = points.get(user_id, 0) + 1

        # Update DB
        await leaderboardCollection.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"points": points}},
            upsert=True
        )

        # Sort leaderboard
        sorted_lb = sorted(points.items(), key=lambda x: x[1], reverse=True)
        description = "\n".join([f"<@{uid}> — `{pts}` points" for uid, pts in sorted_lb[:10]])

        embed = Embed(title="🏆 Leaderboard", color=0x00FF00, description=description)
        embed.timestamp = datetime.utcnow()

        await ctx.send(f"✅ Logged 1 point for {user.mention}", embed=embed)

    except Exception as e:
        print(f"❌ Error logging points: {e}")
        await ctx.send("❌ Something went wrong while logging points.")

# Command to view leaderboard
@bot.command()
async def leaderboard(ctx):
    leaderboard = await leaderboardCollection.find_one({"guild_id": ctx.guild.id})
    if not leaderboard or not leaderboard.get("points"):
        await ctx.send("📊 No points logged yet.")
        return

    points = leaderboard["points"]
    sorted_lb = sorted(points.items(), key=lambda x: x[1], reverse=True)
    description = "\n".join([f"<@{uid}> — `{pts}` points" for uid, pts in sorted_lb[:10]])

    embed = Embed(title="🏆 Leaderboard", color=0x00FF00, description=description)
    embed.timestamp = datetime.utcnow()
    await ctx.send(embed=embed)
bot.run(TOKEN)
