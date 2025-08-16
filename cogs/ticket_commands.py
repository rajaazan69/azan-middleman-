import os
import discord
from discord.ext import commands
from utils.constants import TICKET_CATEGORY_ID, OWNER_ID
from utils.db import collections
from datetime import datetime

class TicketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- ADD USER ----------
    @commands.command(name="add", help="Adds a user to the current ticket channel.")
    async def add(self, ctx, member: discord.Member):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only add users in ticket channels.")
        await ch.set_permissions(member, send_messages=True, view_channel=True)
        await ctx.send(f"✅ {member.mention} added.")

    # ---------- REMOVE USER ----------
    @commands.command(name="remove", help="Removes a user from the current ticket channel.")
    async def remove(self, ctx, member: discord.Member):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only remove users in ticket channels.")
        await ch.set_permissions(member, overwrite=None)
        await ctx.send(f"✅ {member.mention} removed.")

    # ---------- RENAME TICKET ----------
    @commands.command(name="rename", help="Renames the current ticket channel.")
    async def rename(self, ctx, *, new_name: str):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only rename ticket channels.")
        await ch.edit(name=new_name)
        await ctx.send(f"✅ Renamed to `{new_name}`.")

    # ---------- ROBLOX USER INFO ----------
   from discord.ext import commands
from discord import Embed, ButtonStyle
from discord.ui import Button, View
import aiohttp
from datetime import datetime

class Roblox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="i", help="Fetches Roblox user info by username.")
    async def i(self, ctx, username: str):
        try:
            async with aiohttp.ClientSession() as session:
                # Get user ID
                async with session.post(
                    "https://users.roblox.com/v1/usernames/users",
                    json={"usernames":[username], "excludeBannedUsers":False}
                ) as r:
                    data = await r.json()
                user = data['data'][0] if data.get('data') else None
                if not user:
                    return await ctx.send("❌ User not found.")

                user_id = user['id']

                # Profile
                async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as r:
                    profile = await r.json()
                # Followers / Following
                async with session.get(f"https://friends.roblox.com/v1/users/{user_id}/followers/count") as r:
                    followers = (await r.json()).get("count", "N/A")
                async with session.get(f"https://friends.roblox.com/v1/users/{user_id}/followings/count") as r:
                    following = (await r.json()).get("count", "N/A")

            created_date = datetime.fromisoformat(profile['created'])
            age_years = round((datetime.utcnow() - created_date).days / 365, 1)

            # Embed
            embed = Embed(title="Roblox User Information", color=0x000000)
            embed.set_thumbnail(url=f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=true")
            embed.add_field(name="Display Name", value=profile['displayName'])
            embed.add_field(name="Username", value=profile['name'])
            embed.add_field(name="User ID", value=str(user_id))
            embed.add_field(name="\u200B", value="\u200B")
            embed.add_field(name="Account Created", value=f"<t:{int(created_date.timestamp())}:F>")
            embed.add_field(name="Account Age", value=f"{age_years} years")
            embed.add_field(name="\u200B", value="\u200B")
            embed.add_field(name="Followers", value=str(followers))
            embed.add_field(name="Following", value=str(following))
            embed.set_footer(text="Roblox Profile Info")
            embed.timestamp = datetime.utcnow()

            # Button
            button = Button(label="View Profile", style=ButtonStyle.link, url=f"https://www.roblox.com/users/{user_id}/profile")
            view = View()
            view.add_item(button)

            await ctx.send(embed=embed, view=view)

        except Exception as e:
            await ctx.send(f"❌ Failed to fetch user info: {e}")
    # ---------- RESET LEADERBOARD ----------
    @commands.command(name="resetlb", help="Resets the client leaderboard.")
    async def resetlb(self, ctx):
        user = ctx.author
        member = ctx.author
        is_owner = user.id == OWNER_ID
        is_admin = ctx.author.guild_permissions.administrator
        if not is_owner and not is_admin:
            return await ctx.send("❌ You do not have permission to reset the leaderboard.")

        colls = await collections()
        await colls['clientPoints'].delete_many({})

        # Update leaderboard message
        try:
            leaderboard_channel = ctx.guild.get_channel(int(os.getenv("LEADERBOARD_CHANNEL_ID")))
            leaderboard_message = await leaderboard_channel.fetch_message(int(os.getenv("LEADERBOARD_MESSAGE_ID")))
            embed = discord.Embed(title="🏆 Client Leaderboard", description="No points recorded yet!", color=0xFFD700)
            await leaderboard_message.edit(embed=embed)
        except:
            pass

        await ctx.send("✅ Leaderboard has been reset.")

    # ---------- TRANSCRIPT ----------
    @commands.command(name="transcript", help="Generates transcript of the current ticket.")
    async def transcript(self, ctx):
        if ctx.channel.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only generate transcripts in ticket channels.")
        cog = self.bot.get_cog("Transcripts")
        if cog:
            await cog.generate_transcript(ctx, ctx.channel)
        else:
            await ctx.send("❌ Transcript system not available.")


async def setup(bot):
    await bot.add_cog(TicketCommands(bot))