import discord
from discord.ext import commands
from discord.ui import View, Button
import re
from utils.db import collections
from utils.constants import TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID
from db import tickets_json

# ------------------------- MM Server/Channel Config -------------------------
# Add each middleman's ID with their vouch server/channel

MM_VOUCH_CONFIG = {
    1356149794040446998: {  # Replace with actual MM Discord ID
        "server_id": 1373025601212125315,  # Their vouch server ID
        "channel_id": 1373027974827212923  # Their vouch channel ID
    },
    # Add more middlemen here:
    # 234567890123456789: {
    #     "server_id": 876543210987654321,
    #     "channel_id": 222333444555666777
    # },
}

# Vouch keywords to detect
VOUCH_KEYWORDS = [
    "vouch", "+rep", "rep+", "trusted", "legit", "smooth trade",
    "recommend", "thanks mm", "thank you mm", "great mm"
]

# ------------------------- Confirmation View -------------------------
class VouchConfirmView(View):
    def __init__(self, ticket_channel_id: int, vouch_message_link: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.ticket_channel_id = ticket_channel_id
        self.vouch_message_link = vouch_message_link
        self.confirmed = False

    @discord.ui.button(label="✅ Done - Close Ticket", style=discord.ButtonStyle.success, custom_id="vouch_confirm")
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if self.confirmed:
            return await interaction.response.send_message("✅ Already confirmed!", ephemeral=True)

        try:
            await interaction.response.defer(ephemeral=True)
            self.confirmed = True

            # Disable the button
            button.disabled = True
            await interaction.message.edit(view=self)

            # Get the ticket channel
            ticket_channel = interaction.guild.get_channel(self.ticket_channel_id)
            if not ticket_channel:
                return await interaction.followup.send("❌ Could not find ticket channel.", ephemeral=True)

            # Generate transcript
            transcript_cog = interaction.client.get_cog("Transcripts")
            if transcript_cog:
                try:
                    await transcript_cog.generate_transcript(interaction, ticket_channel)
                    print(f"[VOUCH] ✅ Transcript generated")
                except Exception as e:
                    print(f"[VOUCH] Transcript error: {e}")

            # Log points using JSON file
            try:
                ticket_data = tickets_json.get_ticket(str(self.ticket_channel_id))

                if ticket_data:
                    # Use MongoDB for points (since that's still working)
                    colls = await collections()
                    points_coll = colls["clientPoints"]
                    mm_coll = colls["middlemen"]

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
                    claimed_by = ticket_data.get("claimedBy")
                    if claimed_by:
                        try:
                            mm_id = int(claimed_by)
                        except:
                            mm_id = claimed_by
                        await mm_coll.update_one({"_id": mm_id}, {"$inc": {"completed": 1}}, upsert=True)
                        print(f"[VOUCH] ✅ MM {mm_id} completed count incremented")

                    await interaction.followup.send("✅ Points logged successfully!", ephemeral=True)
            except Exception as e:
                print(f"[VOUCH] Points logging error: {e}")
                await interaction.followup.send(f"⚠️ Points logging failed: {e}", ephemeral=True)

            # Delete ticket from JSON
            tickets_json.delete_ticket(str(self.ticket_channel_id))
            print(f"[VOUCH] ✅ Ticket deleted from JSON")

            # Delete the ticket channel
            try:
                await ticket_channel.delete(reason="Vouch detected and confirmed by MM")
                print(f"[VOUCH] ✅ Ticket channel deleted")
            except Exception as e:
                print(f"[VOUCH] Channel deletion error: {e}")
                await interaction.followup.send(f"❌ Could not delete channel: {e}", ephemeral=True)

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

    def _contains_vouch(self, content: str) -> bool:
        """Check if message contains vouch keywords"""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in VOUCH_KEYWORDS)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return

        print(f"[VOUCH DEBUG] Message detected: '{message.content[:50]}' from {message.author} in guild {message.guild.id if message.guild else 'DM'}")

        # Check if message is in a configured vouch channel
        mm_id = None
        for mid, config in MM_VOUCH_CONFIG.items():
            if (message.guild and 
                message.guild.id == config["server_id"] and 
                message.channel.id == config["channel_id"]):
                mm_id = mid
                print(f"[VOUCH DEBUG] ✅ Message is in MM {mm_id}'s vouch channel")
                break

        if not mm_id:
            print(f"[VOUCH DEBUG] ❌ Not in a configured vouch channel")
            return

        # Check if message contains vouch keywords
        if not self._contains_vouch(message.content):
            print(f"[VOUCH DEBUG] ❌ No vouch keywords detected")
            return
        
        print(f"[VOUCH DEBUG] ✅ Vouch keyword detected!")

        # Find the MM's active ticket in the main server
        try:
            # Get the main guild (where tickets are)
            main_guild = None
            for guild in self.bot.guilds:
                category = guild.get_channel(TICKET_CATEGORY_ID)
                if category:
                    main_guild = guild
                    print(f"[VOUCH DEBUG] ✅ Found main guild: {main_guild.name}")
                    break

            if not main_guild:
                print(f"[VOUCH DEBUG] ❌ Could not find main guild with ticket category")
                return

            # Find MM member in main guild
            mm_member = main_guild.get_member(mm_id)
            if not mm_member:
                print(f"[VOUCH DEBUG] ❌ MM {mm_id} not found in main guild")
                return
            
            print(f"[VOUCH DEBUG] ✅ Found MM member: {mm_member}")

            # Search for MM's claimed ticket using JSON
            ticket_data = tickets_json.get_ticket_by_claimed(str(mm_id))
            if not ticket_data:
                print(f"[VOUCH DEBUG] ❌ No claimed ticket found for MM {mm_id}")
                return
            
            print(f"[VOUCH DEBUG] ✅ Found ticket: {ticket_data}")

            ticket_channel_id = int(ticket_data["channelId"])
            ticket_channel = main_guild.get_channel(ticket_channel_id)
            
            if not ticket_channel:
                # Try fetching instead of getting from cache
                try:
                    ticket_channel = await main_guild.fetch_channel(ticket_channel_id)
                    print(f"[VOUCH DEBUG] ✅ Fetched ticket channel: {ticket_channel.name}")
                except discord.NotFound:
                    print(f"[VOUCH DEBUG] ❌ Channel {ticket_channel_id} doesn't exist")
                    return
                except discord.Forbidden:
                    print(f"[VOUCH DEBUG] ❌ Bot can't access channel {ticket_channel_id} (permissions)")
                    return

            # Check if the vouch is from a user in the ticket
            user_ids = [ticket_data.get("user1"), ticket_data.get("user2")]
            print(f"[VOUCH DEBUG] Ticket user IDs: {user_ids}, Voucher ID: {message.author.id}")
            
            if str(message.author.id) not in [str(uid) for uid in user_ids if uid]:
                print(f"[VOUCH DEBUG] ❌ Voucher {message.author.id} is not in this ticket")
                return
            
            print(f"[VOUCH DEBUG] ✅ Voucher is a user in the ticket!")

            # Determine which user vouched
            user1_id = ticket_data.get("user1")
            user2_id = ticket_data.get("user2")
            
            vouched_users = []
            if str(message.author.id) == str(user1_id):
                vouched_users.append("User 1")
            if str(message.author.id) == str(user2_id):
                vouched_users.append("User 2")
            
            vouch_status = f"**{' & '.join(vouched_users)}** has vouched!" if vouched_users else f"{message.author.mention} has vouched!"

            # Send confirmation to MM in the ticket channel
            vouch_link = message.jump_url
            
            # Send simple vouch notification first
            await ticket_channel.send(f"✅ {vouch_status}")
            
            embed = discord.Embed(
                title="✅ Vouch Detected!",
                description=(
                    f"A vouch was detected from {message.author.mention} in your vouch server!\n\n"
                    f"**Vouch Message:**\n>>> {message.content[:1000]}\n\n"
                    f"[Jump to Vouch]({vouch_link})\n\n"
                    f"Click **Done** to:\n"
                    f"• Generate transcript\n"
                    f"• Log points for clients\n"
                    f"• Close this ticket"
                ),
                color=0x00ff00,
                timestamp=message.created_at
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            embed.set_footer(text=f"Vouched by {message.author}")

            view = VouchConfirmView(ticket_channel.id, vouch_link)
            
            await ticket_channel.send(
                content=mm_member.mention,
                embed=embed,
                view=view
            )
            
            print(f"[VOUCH DEBUG] ✅ Successfully sent vouch confirmation to ticket channel")

        except Exception as e:
            print(f"[VOUCH DEBUG] ❌ Vouch detection error: {e}")
            import traceback
            traceback.print_exc()

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(VouchDetector(bot))