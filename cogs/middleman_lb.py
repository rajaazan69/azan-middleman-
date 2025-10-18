import discord
from discord.ext import commands
from utils.db import collections
from datetime import datetime

# optional: constant for your leaderboard channel
LB_CHANNEL_ID = 1409663820053483642  # change to your actual leaderboard channel ID

class MiddlemanLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------- UPDATE OR CREATE MIDDLEMAN LB -------------------------
    async def update_or_create_lb(self, guild: discord.Guild):
        """Finds an existing middleman leaderboard message or creates one."""
        try:
            colls = await collections()
            mm_coll = colls["middlemen"]
        except Exception as e:
            print(f"[MM-LB] DB error: {e}")
            return None

        # Fetch top 10 MMs
        docs = await mm_coll.find().sort("completed", -1).limit(10).to_list(length=10)
        if not docs:
            desc = "*No middleman data yet.*"
        else:
            lines = [
                f"**#{i+1}** <@{mm['_id']}> — **{mm.get('completed', 0)}** ticket{'s' if mm.get('completed', 0) != 1 else ''}"
                for i, mm in enumerate(docs)
            ]
            desc = "\n".join(lines)

        embed = discord.Embed(
            title="> **MIDDLEMAN LEADERBOARD**",
            description=f"__**Top Middlemen:**__\n{desc}",
            color=discord.Color.from_str("#2B2D31"),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Middleman leaderboard — auto updates on ticket close")

        lb_channel = guild.get_channel(LB_CHANNEL_ID)
        if not lb_channel:
            print("[MM-LB] ❌ Leaderboard channel not found.")
            return None

        # Try to find existing leaderboard message in the last few messages
        async for msg in lb_channel.history(limit=20):
            if msg.embeds and msg.embeds[0].title and "MIDDLEMAN LEADERBOARD" in msg.embeds[0].title:
                await msg.edit(embed=embed)
                print("[MM-LB] ✅ Updated existing leaderboard message.")
                return msg

        # If no existing LB found, send a new one
        new_msg = await lb_channel.send(embed=embed)
        print("[MM-LB] 🆕 Sent new leaderboard message.")
        return new_msg

    # ------------------------- MIDDLEMAN LEADERBOARD COMMAND -------------------------
    @commands.command(name="mmlb", aliases=["middlemanlb", "mmlboard"])
    async def show_mm_leaderboard(self, ctx: commands.Context):
        """Displays or updates the middleman leaderboard (top 10)."""
        msg = await self.update_or_create_lb(ctx.guild)
        if msg:
            await ctx.reply(
                f"✅ Middleman leaderboard {'updated' if msg.edited_at else 'created'} in {msg.channel.mention}.",
                mention_author=False
            )
        else:
            await ctx.reply("⚠️ Failed to update leaderboard.", mention_author=False)

    # ------------------------- RESET LEADERBOARD -------------------------
    @commands.command(name="resetmmlb", aliases=["resetmiddlemanlb"])
    @commands.has_permissions(administrator=True)
    async def reset_mm_leaderboard(self, ctx: commands.Context):
        """Resets all middleman completed counts to 0 and refreshes the leaderboard."""
        try:
            colls = await collections()
            mm_coll = colls["middlemen"]
        except Exception as e:
            return await ctx.reply(f"❌ Could not access DB: {e}", mention_author=False)

        try:
            result = await mm_coll.update_many({}, {"$set": {"completed": 0}})
            modified = getattr(result, "modified_count", 0)
            await ctx.reply(f"✅ Reset {modified} middlemen stats to 0.", mention_author=False)

            # Auto refresh leaderboard after reset
            await self.update_or_create_lb(ctx.guild)
        except Exception as e:
            await ctx.reply(f"❌ Reset failed: {e}", mention_author=False)
            print("[resetmmlb] Reset error:", e)


# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(MiddlemanLeaderboard(bot))