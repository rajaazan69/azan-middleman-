import aiohttp
from datetime import datetime
import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import Embed, ButtonStyle
from dateutil import parser

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

                # --------------------------
                # Get avatar headshot URL
                # --------------------------
                async with session.get(
                    f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=true"
                ) as r:
                    thumb_data = await r.json()
                    # The thumbnail API returns an array
                    image_url = thumb_data["data"][0]["imageUrl"] if thumb_data.get("data") else None

                # --------------------------
                # Parse creation date safely
                # --------------------------
                created_date = parser.isoparse(profile['created'])
                age_years = round((datetime.utcnow() - created_date.replace(tzinfo=None)).days / 365, 1)

                # Embed
                embed = Embed(title="Roblox User Information", color=0x000000)
                if image_url:
                    embed.set_thumbnail(url=image_url)
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
                button = Button(
                    label="View Profile",
                    style=ButtonStyle.link,
                    url=f"https://www.roblox.com/users/{user_id}/profile"
                )
                view = View()
                view.add_item(button)

                await ctx.send(embed=embed, view=view)

        except Exception as e:
            await ctx.send(f"❌ Failed to fetch user info: {e}")

# Cog setup
async def setup(bot):
    await bot.add_cog(Roblox(bot))