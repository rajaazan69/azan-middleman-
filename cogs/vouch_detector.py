import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.db import collections
from utils.constants import TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID, LB_CHANNEL_ID, LB_MESSAGE_ID

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
    def __init__(self, ticket_channel_id: int, claimed_by: int, vouch_message_link: str):
        super().__init__(timeout=300)
        self.ticket_channel_id = ticket_channel_id
        self.claimed_by = claimed_by
        self.vouch_message_link = vouch_message_link
        self.confirmed = False

    @discord.ui.button(label="✅ Done - Close Ticket", style=discord.ButtonStyle.success, custom_id="vouch_confirm")
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

            # ----------------- Log Points & Update Leaderboard -----------------
            try:
                colls = await collections()
                tickets_coll = colls["tickets"]
                points_coll = colls["clientPoints"]
                mm_coll = colls["middlemen"]

                ticket_data = await tickets_coll.find_one({"channelId": str(self.ticket_channel_id)})
                if not ticket_data:
                    return await interaction.followup.send("❌ Ticket data not found.", ephemeral=True)

                # Log points for users
                user_ids = [str(uid) for uid in [ticket_data.get("user1"), ticket_data.get("user2")] if uid]
                for uid in user_ids:
                    await points_coll.update_one(
                        {"userId": uid},
                        {"$inc": {"points": 1}, "$setOnInsert": {"userId": uid}},
                        upsert=True
                    )
                print(f"[VOUCH] ✅ Points logged for users: {user_ids}")

                # Increment MM completed tickets
                mm_id = int(ticket_data.get("claimedBy"))
                await mm_coll.update_one({"_id": mm_id}, {"$inc": {"completed": 1}}, upsert=True)
                print(f"[VOUCH] ✅ MM {mm_id} completed count incremented")

                # Update leaderboard
                lb_channel = interaction.guild.get_channel(LB_CHANNEL_ID)
                if lb_channel:
                    try:
                        lb_message = await lb_channel.fetch_message(LB_MESSAGE_ID)
                    except Exception:
                        import datetime
                        embed = discord.Embed(
                            title="🏆 Top Clients This Month",
                            description="No data yet.",
                            color=0x2B2D31,
                            timestamp=datetime.datetime.utcnow()
                        )
                        embed.set_footer(text="Client Leaderboard")
                        lb_message = await lb_channel.send(embed=embed)

                    top_users = await points_coll.find().sort("points", -1).limit(10).to_list(length=10)
                    leaderboard_text = "\n".join(
                        f"**#{i+1}** <@{user.get('userId')}> — **{user.get('points',0)}** point{'s' if user.get('points',0)!=1 else ''}"
                        for i, user in enumerate(top_users) if user.get("userId")
                    ) or "No data yet."

                    embed = discord.Embed(
                        title="🏆 Top Clients This Month",
                        description=leaderboard_text,
                        color=0x2B2D31
                    )
                    embed.set_footer(text="Client Leaderboard")
                    await lb_message.edit(embed=embed)

                # Remove ticket from DB
                await tickets_coll.delete_one({"channelId": str(self.ticket_channel_id)})

                # Delete the ticket channel
                await ticket_channel.delete(reason="Vouch confirmed by MM/Admin")
                await interaction.followup.send("✅ Points logged, leaderboard updated, and ticket closed!", ephemeral=True)

            except Exception as e:
                print(f"[VOUCH] Points/Leaderboard error: {e}")
                await interaction.followup.send(f"⚠️ Points/Leaderboard update failed: {e}", ephemeral=True)

        except Exception as e:
            print(f"[VOUCH] Confirmation error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="vouch_cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.message.delete()
        await interaction.followup.send("❌ Vouch confirmation cancelled.", ephemeral=True)


# ------------------------- Vouch Detector Cog -------------------------
class VouchDetector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._vouched_users_cache = {}  # dict: ticket_channel_id -> set of user IDs who have vouched

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

            # Track vouched users per ticket
            vouched_set = self._vouched_users_cache.get(ticket_channel_id, set())
            vouched_set.add(str(message.author.id))
            self._vouched_users_cache[ticket_channel_id] = vouched_set

            # Send confirmation message for each vouch
            ticket_channel = message.guild.get_channel(ticket_channel_id) or await message.guild.fetch_channel(ticket_channel_id)
            await ticket_channel.send(f"**{message.author.display_name} has vouched!**")

            # Only send embed once all users have vouched (or single user)
            if all(uid in vouched_set for uid in expected_users):
                mm_member = message.guild.get_member(mm_id)
                vouch_text = " | ".join(f"<@{uid}>" for uid in expected_users)
                embed = discord.Embed(
                    title="**BOTH USERS HAVE VOUCHED | HOW WOULD YOU LIKE TO PROCEED**",
                    description=(
                        f"**Vouched Users:** | {vouch_text}\n"
                        f"**Actions:** | Click **Done** to | Generate transcript | Log points | Close ticket"
                    ),
                    color=0x000000,
                    timestamp=message.created_at
                )
                embed.set_author(
                    name=f"{message.author.display_name} | Vouched",
                    icon_url=message.author.display_avatar.url
                )
                if len(expected_users) == 1:
                    embed.add_field(
                        name="**Notice**",
                        value="**No vouch could be detected as no second user exists**",
                        inline=False
                    )
                embed.set_footer(text="Middleman Confirmation | Proceed Carefully")

                view = VouchConfirmView(ticket_channel.id, mm_id, message.jump_url)
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