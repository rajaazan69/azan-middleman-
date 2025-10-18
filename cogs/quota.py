import discord
from discord.ext import commands, tasks
from datetime import datetime
from utils.db import collections

WEEKLY_QUOTA = 5

class Quota(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_weekly_quota.start()  # auto reset on startup

    def cog_unload(self):
        self.reset_weekly_quota.cancel()

    # ------------------------- AUTO RESET -------------------------
    @tasks.loop(hours=24)
    async def reset_weekly_quota(self):
        """Resets middleman weekly progress when the week changes."""
        try:
            colls = await collections()
            mm_coll = colls["middlemen"]
            all_mms = await mm_coll.find().to_list(length=None)

            current_week = datetime.utcnow().isocalendar()[1]
            reset_count = 0

            for mm in all_mms:
                if mm.get("week") != current_week:
                    await mm_coll.update_one(
                        {"_id": mm["_id"]},
                        {"$set": {"completed": 0, "week": current_week}}
                    )
                    reset_count += 1

            if reset_count > 0:
                print(f"✅ [Quota Reset] Reset weekly quota for {reset_count} middlemen (Week {current_week})")
        except Exception as e:
            print(f"[Quota Reset Error] {e}")

    @reset_weekly_quota.before_loop
    async def before_reset(self):
        await self.bot.wait_until_ready()

    # ------------------------- COMMAND -------------------------
    @commands.command(name="quota", aliases=["quotaboard", "qboard"])
    async def quota_command(self, ctx: commands.Context):
        """Displays the weekly middleman quota leaderboard."""
        colls = await collections()
        mm_coll = colls["middlemen"]

        all_mms = await mm_coll.find().to_list(length=None)
        if not all_mms:
            return await ctx.reply("❌ No middlemen data found.", mention_author=False)

        current_week = datetime.utcnow().isocalendar()[1]
        mm_progress = []

        for mm in all_mms:
            completed = mm.get("completed", 0)
            week = mm.get("week")

            # Reset display progress if week mismatched
            if week != current_week:
                completed = 0

            mm_progress.append({
                "id": mm["_id"],
                "completed": completed
            })

        # Sort by completed count
        mm_progress.sort(key=lambda x: x["completed"], reverse=True)

        # Split groups
        completed_quota = [m for m in mm_progress if m["completed"] >= WEEKLY_QUOTA]
        incomplete_quota = [m for m in mm_progress if m["completed"] < WEEKLY_QUOTA]

        # ---------------- EMBED BUILD ----------------
        embed = discord.Embed(
            title="**WEEKLY MIDDLEMEN QUOTA**",
            description=(
                f"**Weekly Goal:** {WEEKLY_QUOTA} trades per middleman\n"
                f"**Current Week:** {current_week}\n\n"
                f"__**Completed Quota:**__\n"
                + (
                    "\n".join([
                        f"**#{i+1}** <@{mm['id']}> — **{mm['completed']} tickets**"
                        for i, mm in enumerate(completed_quota)
                    ]) if completed_quota else "*No middlemen have met their quota yet.*"
                )
                + "\n\n__**Incomplete Quota:**__\n"
                + (
                    "\n".join([
                        f"**#{i+1+len(completed_quota)}** <@{mm['id']}> — **{mm['completed']} / {WEEKLY_QUOTA}**"
                        for i, mm in enumerate(incomplete_quota)
                    ]) if incomplete_quota else "*Everyone has met the quota!*"
                )
            ),
            color=discord.Color.from_str("#2B2D31")  # Dark elegant theme
        )

        embed.set_footer(
            text="Weekly middleman progress — auto resets every Monday",
            icon_url=ctx.bot.user.display_avatar.url
        )
        embed.timestamp = datetime.utcnow()

        await ctx.reply(embed=embed, mention_author=False)

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(Quota(bot))