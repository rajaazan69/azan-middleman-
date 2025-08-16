import aiohttp
import discord
from discord.ext import commands
from datetime import datetime

@commands.command(name="i", help="Fetches Roblox user information by username.")
async def roblox_info(self, ctx: commands.Context, username: str):
    async with aiohttp.ClientSession() as session:
        try:
            # Fetch user ID
            async with session.post(
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": [username], "excludeBannedUsers": False}
            ) as resp:
                data = await resp.json()
                user = data.get("data", [None])[0]

            if not user:
                return await ctx.send("❌ User not found.", delete_after=10)

            user_id = user["id"]

            # Fetch profile, followers, following, avatar
            async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
                profile = await resp.json()
            async with session.get(f"https://friends.roblox.com/v1/users/{user_id}/followers/count") as resp:
                followers = await resp.json()
            async with session.get(f"https://friends.roblox.com/v1/users/{user_id}/followings/count") as resp:
                following = await resp.json()
            async with session.get(
                f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png&isCircular=false"
            ) as resp:
                avatar_data = await resp.json()
                avatar_url = avatar_data.get("data", [{}])[0].get("imageUrl")

            # Account age
            created_date = datetime.fromisoformat(profile["created"].replace("Z", "+00:00"))
            now = datetime.utcnow()
            years_old = round((now - created_date).days / 365, 1)

            # Build embed
            embed = discord.Embed(title="Roblox User Information", color=0x000000)
            embed.set_thumbnail(url=f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=true")
            embed.add_field(name="Display Name", value=profile.get("displayName", "N/A"), inline=False)
            embed.add_field(name="Username", value=profile.get("name", "N/A"), inline=False)
            embed.add_field(name="User ID", value=str(user_id), inline=False)
            embed.add_field(name="\u200B", value="\u200B", inline=False)
            embed.add_field(name="Account Created", value=f"<t:{int(created_date.timestamp())}:F>", inline=False)
            embed.add_field(name="Account Age", value=f"{years_old} years", inline=False)
            embed.add_field(name="\u200B", value="\u200B", inline=False)
            embed.add_field(name="Followers", value=f"{followers.get('count', 'N/A'):,}", inline=False)
            embed.add_field(name="Following", value=f"{following.get('count', 'N/A'):,}", inline=False)
            embed.set_footer(text="Roblox Profile Info", icon_url="https://tr.rbxcdn.com/4f82333f5f54d234e95d1f81251a67dc/150/150/Image/Png")
            if avatar_url:
                embed.set_image(url=avatar_url)

            # Add view profile button
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="View Profile", url=f"https://www.roblox.com/users/{user_id}/profile"))

            await ctx.send(embed=embed, view=view)

        except Exception as e:
            print("❌ Roblox user info error:", e)
            await ctx.send("❌ Failed to fetch user info.", delete_after=10)
