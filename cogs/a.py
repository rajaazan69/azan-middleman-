import discord
from discord.ext import commands
import aiohttp
from datetime import datetime, timezone
from utils.db import collections

class ApplyCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- Format Helpers ----------
    def format_date(self, date_string: str) -> str:
        date = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return date.strftime('%Y-%m-%d %H:%M:%S UTC')

    def time_ago(self, date_string: str) -> str:
        date = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)  # make timezone-aware
        seconds = (now - date).total_seconds()

        minutes = int(seconds // 60)
        hours = int(minutes // 60)
        days = int(hours // 24)
        if days > 0: return f"{days}d ago"
        if hours > 0: return f"{hours}h ago"
        if minutes > 0: return f"{minutes}m ago"
        return f"{int(seconds)}s ago"

    # ---------- $a command ----------
    @commands.command(name="a", aliases=["apply"], help="Show the saved Roblox user info for someone.")
    async def apply(self, ctx, member: discord.Member = None):
                # Permission check: Admin OR role ID 1373029428409405500
        admin_role_id = 1373029428409405500
        if not (ctx.author.guild_permissions.administrator or discord.utils.get(ctx.author.roles, id=admin_role_id)):
            return await ctx.reply("❌ You don't have permission to use this command.")

        colls = await collections()
        loading_msg = await ctx.reply(f"🔎 Checking Roblox user `{roblox_user}`...")

        try:
            user_data = await self.get_roblox_user(roblox_user)
            if not user_data:
                return await loading_msg.edit(content=f"❌ Could not find Roblox user `{roblox_user}`.")
        target = member or ctx.author

        colls = await collections()
        saved = await colls["tags"].find_one({"_id": str(target.id)})

        if not saved:
            return await ctx.reply(f"{target.mention} has not saved a Roblox user yet. Use `$s <robloxUser>`")

        query = saved["robloxUser"]
        user_id = None
        user_data = None
        user_thumbnail_url = "https://www.roblox.com/images/logo/roblox_logo_300x300.png"

        loading_msg = await ctx.reply(f"Fetching Roblox info for **{query}**...")

        try:
            async with aiohttp.ClientSession() as session:
                # Username → ID
                if not query.isdigit():
                    async with session.post(
                        "https://users.roblox.com/v1/usernames/users",
                        json={"usernames": [query], "excludeBannedUsers": False}
                    ) as resp:
                        data = await resp.json()
                        if data.get("data") and len(data["data"]) > 0:
                            user_id = data["data"][0]["id"]
                        else:
                            return await loading_msg.edit(content=f"Could not find Roblox user `{query}`.")
                else:
                    user_id = int(query)

                # Fetch user details
                async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
                    user_data = await resp.json()

                # Fetch thumbnail
                async with session.get(
                    f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"
                ) as resp:
                    thumb_data = await resp.json()
                    if thumb_data.get("data") and len(thumb_data["data"]) > 0:
                        user_thumbnail_url = thumb_data["data"][0]["imageUrl"]

            # Profile link
            profile_link = f"https://www.roblox.com/users/{user_id}/profile"

            embed = discord.Embed(
                color=0xFF0000 if user_data.get("isBanned") else 0x000000
            )
            embed.set_author(name=user_data["name"], url=profile_link, icon_url=user_thumbnail_url)
            embed.set_thumbnail(url=user_thumbnail_url)
            embed.add_field(name="Display Name", value=f"`{user_data['displayName']}`", inline=True)
            embed.add_field(name="ID", value=f"`{user_data['id']}`", inline=True)
            embed.add_field(
                name="Created",
                value=f"{self.format_date(user_data['created'])}\n{self.time_ago(user_data['created'])}",
                inline=False
            )

            if user_data.get("description"):
                embed.add_field(name="Description", value=user_data["description"][:1020], inline=False)

            if user_data.get("isBanned"):
                embed.add_field(name="Status", value="BANNED", inline=False)

            embed.set_footer(text=f"Saved for {target}", icon_url=target.display_avatar.url)
            embed.timestamp = datetime.now(timezone.utc)

            # Add profile link button
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Profile Link", url=profile_link))

            await loading_msg.edit(content=None, embed=embed, view=view)

        except Exception as e:
            print(f"[ApplyCmd] Error: {e}")
            await loading_msg.edit(content="❌ Failed to fetch Roblox info. Try again later.")

async def setup(bot):
    await bot.add_cog(ApplyCommand(bot))