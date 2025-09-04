import discord
from discord.ext import commands
import aiohttp
import datetime

class Apply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_date(self, date_string: str):
        dt = datetime.datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def time_ago(self, date_string: str):
        dt = datetime.datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        diff = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - dt
        seconds = diff.total_seconds()
        minutes = seconds // 60
        hours = minutes // 60
        days = hours // 24

        if days > 0:
            return f"{int(days)}d ago"
        if hours > 0:
            return f"{int(hours)}h ago"
        if minutes > 0:
            return f"{int(minutes)}m ago"
        return f"{int(seconds)}s ago"

    @commands.command(name="a", aliases=["apply"])
    async def apply(self, ctx, member: discord.User = None):
        member = member or ctx.author

        # DB check (assuming self.bot.db is a dict like in your JS)
        if not hasattr(self.bot, "db") or "savedRobloxUsers" not in self.bot.db or member.id not in self.bot.db["savedRobloxUsers"]:
            return await ctx.reply(f"{member.mention} has not saved a Roblox user yet. Use `{self.bot.prefix}s <robloxUser>`")

        query = self.bot.db["savedRobloxUsers"][member.id]
        user_id = None
        user_data = None
        user_thumbnail_url = "https://www.roblox.com/images/logo/roblox_logo_300x300.png"

        loading_message = await ctx.reply(f"Fetching Roblox info for **{query}**...")

        try:
            async with aiohttp.ClientSession() as session:
                # if query is username
                if not str(query).isdigit():
                    async with session.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [query], "excludeBannedUsers": False}) as resp:
                        data = await resp.json()
                        if data.get("data"):
                            user_id = data["data"][0]["id"]
                        else:
                            return await loading_message.edit(content=f'Could not find Roblox user "{query}".')
                else:
                    user_id = int(query)

                # fetch user details
                async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
                    user_data = await resp.json()

                # fetch avatar
                async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false") as resp:
                    thumb_data = await resp.json()
                    if thumb_data.get("data"):
                        user_thumbnail_url = thumb_data["data"][0]["imageUrl"]

            profile_link = f"https://www.roblox.com/users/{user_id}/profile"

            embed = discord.Embed(
                color=discord.Color.red() if user_data.get("isBanned") else discord.Color.black(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_author(name=user_data.get("name"), icon_url=user_thumbnail_url, url=profile_link)
            embed.set_thumbnail(url=user_thumbnail_url)
            embed.add_field(name="Display Name", value=f"`{user_data.get('displayName')}`", inline=False)
            embed.add_field(name="ID", value=f"`{user_data.get('id')}`", inline=False)
            embed.add_field(
                name="Created",
                value=f"{self.format_date(user_data.get('created'))}\n{self.time_ago(user_data.get('created'))}",
                inline=False
            )
            if user_data.get("description"):
                embed.add_field(name="Description", value=user_data["description"][:1020], inline=False)
            if user_data.get("isBanned"):
                embed.add_field(name="Status", value="BANNED", inline=False)

            embed.set_footer(text=f"Saved for {member}", icon_url=member.display_avatar.url)

            # Button
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Profile Link", url=profile_link))

            await loading_message.edit(content=None, embed=embed, view=view)

        except Exception as e:
            print(f"[ApplyCmd] Error: {e}")
            await loading_message.edit(content="❌ Failed to fetch Roblox info. Try again later.")


async def setup(bot):
    await bot.add_cog(Apply(bot))