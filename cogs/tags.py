from discord.ext import commands
import discord
from utils.db import collections

class Tags(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="tagcreate")
    @commands.has_permissions(manage_messages=True)
    async def tagcreate(self, ctx, name: str, *, message: str):
        colls = await collections()
        await colls["tags"].update_one({"name": name}, {"$set": {"message": message}}, upsert=True)
        await ctx.reply(f"✅ Tag `{name}` saved.", mention_author=False)

    @commands.command(name="tag")
    async def tag(self, ctx, name: str):
        colls = await collections()
        tag = await colls["tags"].find_one({"name": name})
        if not tag:
            return await ctx.reply(f"❌ Tag `{name}` not found.", mention_author=False)
        await ctx.send(tag["message"][:2000])

    @commands.command(name="tagdelete")
    @commands.has_permissions(manage_messages=True)
    async def tagdelete(self, ctx, name: str):
        colls = await collections()
        res = await colls["tags"].delete_one({"name": name})
        await ctx.reply("🗑️ Tag deleted." if res.deleted_count else f"❌ Tag `{name}` not found.", mention_author=False)

    @commands.command(name="taglist")
    async def taglist(self, ctx):
        colls = await collections()
        items = [f"• `{t['name']}`" async for t in colls["tags"].find({}, {"name":1})]
        await ctx.reply("\n".join(items) or "No tags found.", mention_author=False)

async def setup(bot):
    await bot.add_cog(Tags(bot))