import discord
from discord.ext import commands, tasks
from datetime import datetime
from utils.db import collections

# -------------------------
# CONFIG
# -------------------------
WEEKLY_QUOTA = 5
MIDDLEMAN_ROLE_ID = 1373029428409405500
QUOTA_CHANNEL_ID = 1429161206467268609

class Quota(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_weekly_quota.start()

    def cog_unload(self):
        self.reset_weekly_quota.cancel()

    # ------------------------- AUTO RESET -------------------------
    @tasks.loop(hours=24)
    async def reset_weekly_quota(self):
        try:
            colls = await collections()
            quota_coll = colls["weeklyQuota"]
            all_mms = await quota_coll.find().to_list(length=None)
            if not all_mms:
                return

            current_week = datetime.utcnow().isocalendar()[1]
            for mm in all_mms:
                if mm.get("week") != current_week:
                    await quota_coll.update_one(
                        {"_id": mm["_id"]},
                        {"$set": {"completed": 0, "week": current_week}}
                    )
            print(f"✅ [Quota Reset] Week {current_week} processed.")
        except Exception as e:
            print(f"[Quota Reset Error] {e}")

    @reset_weekly_quota.before_loop
    async def before_reset(self):
        await self.bot.wait_until_ready()

    # ------------------------- COMMAND -------------------------
    @commands.command(name="quota", aliases=["quotaboard", "qboard"])
    async def quota_command(self, ctx: commands.Context = None, channel: discord.TextChannel = None):
        guild = self.bot.get_guild(channel.guild.id if channel else ctx.guild.id)
        colls = await collections()
        quota_coll = colls["weeklyQuota"]

        mm_role = guild.get_role(MIDDLEMAN_ROLE_ID)
        if not mm_role:
            if ctx:
                return await ctx.reply("❌ Middleman role not found!", mention_author=False)
            return

        role_members = [m for m in mm_role.members if not m.bot]
        all_mms = await quota_coll.find().to_list(length=None)
        db_data = {int(mm["_id"]): mm for mm in all_mms}

        current_week = datetime.utcnow().isocalendar()[1]
        mm_progress = []
        for member in role_members:
            db_mm = db_data.get(member.id)
            completed = 0
            if db_mm:
                completed = db_mm.get("completed", 0)
                if db_mm.get("week") != current_week:
                    completed = 0

            mm_progress.append({
                "id": member.id,
                "name": member.display_name,
                "completed": completed
            })

        mm_progress.sort(key=lambda x: x["completed"], reverse=True)
        completed_quota = [m for m in mm_progress if m["completed"] >= WEEKLY_QUOTA]
        incomplete_quota = [m for m in mm_progress if m["completed"] < WEEKLY_QUOTA]

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
            icon_url=self.bot.user.display_avatar.url
        )
        embed.timestamp = datetime.utcnow()

        if ctx:
            await ctx.reply(embed=embed, mention_author=False)
        elif channel:
            await channel.send(embed=embed)

    # ------------------------- SEND QUOTA ON STARTUP -------------------------
    async def send_quota_on_startup(self, channel: discord.TextChannel = None):
        """Send the quota embed if one doesn't exist. Call this from bot.py."""
        if not channel:
            channel = self.bot.get_channel(QUOTA_CHANNEL_ID)
        if not channel:
            print(f"[Quota Startup] Channel with ID {QUOTA_CHANNEL_ID} not found!")
            return

        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if "WEEKLY MIDDLEMEN QUOTA" in msg.embeds[0].title:
                    return  # Already exists

        await self.quota_command(channel=channel)


# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(Quota(bot))