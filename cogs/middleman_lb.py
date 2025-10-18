import discord
from discord.ext import commands
from utils.db import collections
from datetime import datetime

class MiddlemanLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------- MIDDLEMAN LEADERBOARD -------------------------
    @commands.command(name="mmlb", aliases=["middlemanlb", "mmlboard"])
    async def show_mm_leaderboard(self, ctx: commands.Context):
        """Displays the overall middleman leaderboard."""
        colls = await collections()
        mm_coll = colls["middlemen"]

        all_mms = await mm_coll.find().sort("completed", -1).limit(10).to_list(length=10)

        if not all_mms:
            desc = "*No middleman data yet.*"
        else:
            desc = "\n".join(
                f"**#{i+1}** <@{mm['_id']}> — **{mm.get('completed', 0)}** ticket{'s' if mm.get('completed', 0) != 1 else ''}"
                for i, mm in enumerate(all_mms)
            )

        embed = discord.Embed(
            title="# **MIDDLEMAN LEADERBOARD**",
            description=f"__**Top Middlemen:**__\n{desc}",
            color=discord.Color.from_str("#2B2D31"),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Middleman leaderboard — auto updates on ticket close")

        await ctx.send(embed=embed)

    # ------------------------- RESET LEADERBOARD -------------------------
    @commands.command(name="resetmmlb", aliases=["resetmiddlemanlb"])
    @commands.has_permissions(administrator=True)
    async def reset_mm_leaderboard(self, ctx: commands.Context):
        """Resets all middleman stats."""
        colls = await collections()
        mm_coll = colls["middlemen"]

        await mm_coll.update_many({}, {"$set": {"completed": 0}})
        await ctx.reply("✅ All middleman stats have been reset to **0**.", mention_author=False)

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(MiddlemanLeaderboard(bot))