import discord
from discord.ext import commands
import aiohttp
from utils.db import collections

class SaveCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_roblox_user(self, query: str):
        """Resolve username or ID into Roblox user object, or None if not found."""
        query = query.strip()

        # If numeric, treat as ID
        if query.isdigit():
            user_id = int(query)
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None

        # Otherwise treat as username
        async with aiohttp.ClientSession() as session:
            url = "https://users.roblox.com/v1/usernames/users"
            payload = {"usernames": [query], "excludeBannedUsers": False}

            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

                if not data.get("data") or len(data["data"]) == 0:
                    return None

                user_id = data["data"][0]["id"]

            # Fetch user details
            async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
                if resp.status == 200:
                    return await resp.json()
                return None

    @commands.command(name="s", aliases=["save"], help="Save your Roblox username/ID.")
    async def save(self, ctx, *, roblox_user: str):
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

            # Save Roblox user ID
            await colls["tags"].update_one(
                {"_id": str(ctx.author.id)},
                {"$set": {"robloxUser": str(user_data['id'])}},
                upsert=True
            )

            await loading_msg.edit(
                content=f"✅ Saved Roblox user `{user_data['name']}` (ID: {user_data['id']}) for {ctx.author.mention}"
            )

        except Exception as e:
            await loading_msg.edit(content=f"❌ Error while checking Roblox user.")
            raise e

async def setup(bot):
    await bot.add_cog(SaveCommand(bot))