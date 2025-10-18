import discord
from discord.ext import commands, tasks
from datetime import datetime
from utils.db import collections

# -------------------------
# CONFIG
# -------------------------
WEEKLY_QUOTA = 5
MIDDLEMAN_ROLE_ID = 1373029428409405500  # 🔧 Replace with your actual Middleman role ID

# -------------------------
# MAIN COG
# -------------------------
class Quota(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_weekly_quota.start()

    def cog_unload(self):
        self.reset_weekly_quota.cancel()

    # ------------------------- AUTO RESET -------------------------
    @tasks.loop(hours=24)
    async def reset_weekly_quota(self):
        """Resets middleman weekly progress every Monday."""
        try:
            colls = await collections()
            quota_coll = colls["weeklyQuota"]  # ✅ separate collection for weekly quota
            all_mms = await quota_coll.find().to_list(length=None)

            if not all_mms:
                return

            current_week = datetime.utcnow().isocalendar()[1]
            reset_count = 0

            for mm in all_mms:
                if mm.get("week") != current_week:
                    await quota_coll.update_one(
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
        guild = ctx.guild
        colls = await collections()
        quota_coll = colls["weeklyQuota"]  # ✅ use weekly quota collection

        # Get the Middleman role
        mm_role = guild.get_role(MIDDLEMAN_ROLE_ID)
        if not mm_role:
            return await ctx.reply("❌ Middleman role not found!", mention_author=False)

        # Get all members with MM role
        role_members = [m for m in mm_role.members if not m.bot]

        # Fetch DB data
        all_mms = await quota_coll.find().to_list(length=None)
        db_data = {int(mm["_id"]): mm for mm in all_mms}

        current_week = datetime.utcnow().isocalendar()[1]
        mm_progress = []

        # Combine DB and Role data
        for member in role_members:
            db_mm = db_data.get(member.id)
            completed = 0
            week = current_week

            if db_mm:
                completed = db_mm.get("completed", 0)
                if db_mm.get("week") != current_week:
                    completed = 0

            mm_progress.append({
                "id": member.id,
                "name": member.display_name,
                "completed": completed
            })

        # Sort leaderboard
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
            color=discord.Color.from_str("#2B2D31")
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