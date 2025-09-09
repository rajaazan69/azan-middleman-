import discord
from discord.ext import commands
import re

class SayEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- SAY EMBED COMMAND ----------
    @commands.command(name="sayembed", help="Make the bot say anything in an embed.")
    @commands.has_permissions(administrator=True)  # ✅ Only admins can use
    async def sayembed(self, ctx, *, args: str):
        await ctx.message.delete()

        # Regex parser for key:value pairs
        pattern = r'(\w+):\s*([^$]+?)(?=\s+\w+:|$)'
        matches = re.findall(pattern, args)

        data = {key.lower(): value.strip() for key, value in matches}

        # Build embed
        embed = discord.Embed(
            title=data.get("title", ""),
            description=data.get("description", ""),
            color=0x000000
        )

        if "footer" in data:
            embed.set_footer(text=data["footer"])

        if "thumbnail" in data:
            embed.set_thumbnail(url=data["thumbnail"])

        if "image" in data:
            embed.set_image(url=data["image"])

        await ctx.send(embed=embed)

    # ---------- Error handler ----------
    @sayembed.error
    async def sayembed_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                f"❌ {ctx.author.mention}, you don’t have permission to use this command.",
                delete_after=5
            )

# ---------- REQUIRED SETUP ----------
async def setup(bot):
    await bot.add_cog(SayEmbed(bot))