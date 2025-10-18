import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.db import collections
from utils.constants import TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID, LB_CHANNEL_ID, LB_MESSAGE_ID
from datetime import datetime

# ------------------------- MM Server/Channel Config -------------------------
MM_VOUCH_CONFIG = {
    1356149794040446998: {  # Replace with actual MM Discord ID
        "server_id": 1373025601212125315,
        "channel_id": 1373027974827212923
    },
}

VOUCH_KEYWORDS = [
    "vouch", "+rep", "rep+", "trusted", "legit", "smooth trade",
    "recommend", "thanks mm", "thank you mm", "great mm"
]

# ------------------------- Confirmation View -------------------------
class VouchConfirmView(View):
    def __init__(self, ticket_channel_id: int, claimed_by: int, expected_users: list, vouch_message_link: str, bot: commands.Bot):
        super().__init__(timeout=300)
        self.ticket_channel_id = ticket_channel_id
        self.claimed_by = claimed_by
        self.expected_users = expected_users
        self.vouch_message_link = vouch_message_link
        self.confirmed = False
        self.bot = bot

    @discord.ui.button(label="Done - Close Ticket", style=discord.ButtonStyle.success, custom_id="vouch_confirm", emoji="<a:checkmarktick:1337113853393109124>")
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        is_admin = interaction.user.guild_permissions.administrator
        if interaction.user.id != self.claimed_by and not is_admin:
            return await interaction.response.send_message(
                "❌ Only the assigned middleman or an admin can confirm this vouch.", ephemeral=True
            )

        if self.confirmed:
            return await interaction.response.send_message("✅ Already confirmed!", ephemeral=True)

        try:
            await interaction.response.defer(ephemeral=True)
            self.confirmed = True
            button.disabled = True
            await interaction.message.edit(view=self)

            ticket_channel = interaction.guild.get_channel(self.ticket_channel_id)
            if not ticket_channel:
                return await interaction.followup.send("❌ Could not find ticket channel.", ephemeral=True)

            # ----------------- Generate Transcript -----------------
            transcript_cog = interaction.client.get_cog("Transcripts")
            if transcript_cog:
                try:
                    await transcript_cog.generate_transcript(interaction, ticket_channel)
                    print(f"[VOUCH] ✅ Transcript generated")
                except Exception as e:
                    print(f"[VOUCH] Transcript error: {e}")

            # ----------------- Log Points & Update Leaderboard & Quota -----------------
            colls = await collections()
            tickets_coll = colls["tickets"]
            points_coll = colls["clientPoints"]
            mm_coll = colls["middlemen"]
            quota_coll = colls["weeklyQuota"]

            ticket_data = await tickets_coll.find_one({"channelId": str(self.ticket_channel_id)})
            if not ticket_data:
                return await interaction.followup.send("❌ Ticket data not found.", ephemeral=True)

            # Only log points for users in the ticket
            user_ids = [str(uid) for uid in self.expected_users if uid]
            for uid in user_ids:
                await points_coll.update_one(
                    {"userId": uid},
                    {"$inc": {"points": 1}, "$setOnInsert": {"userId": uid}},
                    upsert=True
                )

            # ------------------- Update Middleman Leaderboard -------------------
            mm_id_for_db = int(ticket_data.get("claimedBy"))
            current_week = datetime.utcnow().isocalendar()[1]

            await mm_coll.update_one(
                {"_id": mm_id_for_db},
                {"$inc": {"completed": 1}, "$set": {"week": current_week}},
                upsert=True
            )

            # ------------------- Update Weekly Quota -------------------
            quota_doc = await quota_coll.find_one({"_id": mm_id_for_db})
            if quota_doc and quota_doc.get("week") == current_week:
                await quota_coll.update_one(
                    {"_id": mm_id_for_db},
                    {"$inc": {"completed": 1}}
                )
            else:
                await quota_coll.update_one(
                    {"_id": mm_id_for_db},
                    {"$set": {"completed": 1, "week": current_week}},
                    upsert=True
                )

            # ------------------- Refresh Boards -------------------
            quota_cog = self.bot.get_cog("Quota")
            if quota_cog:
                await quota_cog.send_quota_on_startup()  # safe: only sends if none exists

            mm_lb_cog = self.bot.get_cog("MiddlemanLeaderboard")
            if mm_lb_cog:
                for guild in self.bot.guilds:
                    await mm_lb_cog.update_or_create_lb(guild)

            # ----------------- Remove ticket from DB -----------------
            await tickets_coll.delete_one({"channelId": str(self.ticket_channel_id)})

            # ----------------- Delete the ticket channel -----------------
            await ticket_channel.delete(reason="Vouch confirmed by MM/Admin")
            await interaction.followup.send("✅ Points logged, leaderboard & quota updated, and ticket closed!", ephemeral=True)

        except Exception as e:
            print(f"[VOUCH] Confirmation error: {e}")
            import traceback
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="vouch_cancel", emoji="<a:Red_Cross:1380729160141635594>")
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.message.delete()
        await interaction.followup.send("❌ Vouch confirmation cancelled.", ephemeral=True)


# ------------------------- Vouch Detector Cog -------------------------
class VouchDetector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._vouched_users_cache = {}  # ticket_channel_id -> set of user IDs who have vouched

    def _contains_vouch(self, content: str) -> bool:
        return any(keyword in content.lower() for keyword in VOUCH_KEYWORDS)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        mm_id = None
        for mid, config in MM_VOUCH_CONFIG.items():
            if message.guild and message.guild.id == config["server_id"] and message.channel.id == config["channel_id"]:
                mm_id = mid
                break

        if not mm_id or not self._contains_vouch(message.content):
            return

        try:
            colls = await collections()
            tickets_coll = colls["tickets"]

            ticket_data = await tickets_coll.find_one({"claimedBy": str(mm_id)})
            if not ticket_data:
                return

            ticket_channel_id = int(ticket_data["channelId"])
            expected_users = [str(ticket_data.get("user1"))]
            if ticket_data.get("user2"):
                expected_users.append(str(ticket_data.get("user2")))

            # Only detect vouches from users in the ticket
            if str(message.author.id) not in expected_users:
                return

            # Track vouched users per ticket
            vouched_set = self._vouched_users_cache.get(ticket_channel_id, set())
            vouched_set.add(str(message.author.id))
            self._vouched_users_cache[ticket_channel_id] = vouched_set

            ticket_channel = message.guild.get_channel(ticket_channel_id) or await message.guild.fetch_channel(ticket_channel_id)
            await ticket_channel.send(f"**{message.author.mention} has vouched!**")

            # Only send confirmation when all expected users have vouched
            if all(uid in vouched_set for uid in expected_users):
                mm_member = message.guild.get_member(mm_id)
                vouch_text = " | ".join(f"<@{uid}>" for uid in expected_users)
                embed = discord.Embed(
                    title="**•__ALL USERS HAVE VOUCHED | HOW WOULD YOU LIKE TO PROCEED?•__**",
                    description=(
                        f"**| Vouched Users:** | {vouch_text}\n"
                        f"**| Actions:** | Click **Done** to | Generate **Transcript** | Log **Points** | Close **Ticket**"
                    ),
                    color=0x000000,
                    timestamp=message.created_at
                )
                embed.set_author(
                    name=f"{message.author.display_name} | Vouched",
                    icon_url=message.author.display_avatar.url
                )
                embed.set_footer(text="Middleman Confirmation | Proceed Carefully")

                view = VouchConfirmView(ticket_channel.id, mm_id, expected_users, message.jump_url, self.bot)
                await ticket_channel.send(content=mm_member.mention, embed=embed, view=view)

        except Exception as e:
            print(f"[VOUCH DEBUG] ❌ Vouch detection error: {e}")
            import traceback
            traceback.print_exc()


# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(VouchDetector(bot))