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
        """Displays the overall middleman leaderboard (top 10)."""
        try:
            colls = await collections()
            mm_coll = colls.get("middlemen") if isinstance(colls, dict) else colls["middlemen"]
        except Exception as e:
            return await ctx.reply(f"❌ Could not access DB: {e}", mention_author=False)

        try:
            # fetch top 10 by completed
            docs = await mm_coll.find().sort("completed", -1).limit(10).to_list(length=10)
        except Exception as e:
            return await ctx.reply(f"❌ Query failed: {e}", mention_author=False)

        if not docs:
            desc = "*No middleman data yet.*"
        else:
            lines = []
            for i, mm in enumerate(docs, start=1):
                completed = mm.get("completed", 0)
                # ensure id present
                mm_id = mm.get("_id", "unknown")
                lines.append(f"**#{i}** <@{mm_id}> — **{completed}** ticket{'s' if completed != 1 else ''}")
            desc = "\n".join(lines)

        embed = discord.Embed(
            title=">**MIDDLEMAN LEADERBOARD**",
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
        """Resets all middleman completed counts to 0 and reports results."""
        try:
            colls = await collections()
            mm_coll = colls.get("middlemen") if isinstance(colls, dict) else colls["middlemen"]
        except Exception as e:
            return await ctx.reply(f"❌ Could not access DB: {e}", mention_author=False)

        try:
            # optionally show counts before resetting
            total_before = await mm_coll.count_documents({})
            result = await mm_coll.update_many({}, {"$set": {"completed": 0}})
            # result is MotorUpdateResult or similar; some drivers expose modified_count
            modified = getattr(result, "modified_count", None)
            matched = getattr(result, "matched_count", None)

            # also fetch a total after to sanity-check
            total_after = await mm_coll.count_documents({})

            reply = (
                f"**Reset middleman stats**.\n"
                f"**Documents matched**: {matched if matched is not None else total_before}\n"
                f"**Documents modified**: {modified if modified is not None else 'unknown'}\n"
                f"**Total documents before**: {total_before}\n"
                f"**Total documents after**: {total_after}"
            )
            await ctx.reply(reply, mention_author=False)
        except Exception as e:
            await ctx.reply(f"❌ Reset failed: {e}", mention_author=False)
            # also print to your bot console for debugging
            print("[resetmmlb] Reset error:", e)

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(MiddlemanLeaderboard(bot))