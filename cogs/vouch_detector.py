import discord
from discord.ext import commands
from discord.ui import View, Button
import re
from utils.db import collections
from utils.constants import TICKET_CATEGORY_ID, MIDDLEMAN_ROLE_ID

# ———————–– MM Server/Channel Config ———————––

# Add each middleman’s ID with their vouch server/channel

MM_VOUCH_CONFIG = {
1356149794040446998: {  # Replace with actual MM Discord ID
“server_id”: 1373025601212125315,  # Their vouch server ID
“channel_id”: 1373027974827212923  # Their vouch channel ID
},
# Add more middlemen here:
# 234567890123456789: {
#     “server_id”: 876543210987654321,
#     “channel_id”: 222333444555666777
# },
}

# Vouch keywords to detect

VOUCH_KEYWORDS = [
“vouch”, “+rep”, “rep+”, “trusted”, “legit”, “smooth trade”,
“recommend”, “thanks mm”, “thank you mm”, “great mm”
]

# ———————–– Confirmation View ———————––

class VouchConfirmView(View):
def **init**(self, ticket_channel_id: int, vouch_message_link: str):
super().**init**(timeout=300)  # 5 minute timeout
self.ticket_channel_id = ticket_channel_id
self.vouch_message_link = vouch_message_link
self.confirmed = False

```
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

        # Import the transcript cog and close panel
        from .ticket import ClosePanel

        # Generate transcript
        transcript_cog = interaction.client.get_cog("Transcripts")
        if transcript_cog:
            try:
                await transcript_cog.generate_transcript(interaction, ticket_channel)
            except Exception as e:
                print(f"Transcript error: {e}")

        # Log points
        try:
            colls = await collections()
            tickets_coll = colls["tickets"]
            points_coll = colls["clientPoints"]
            mm_coll = colls["middlemen"]

            ticket_data = await tickets_coll.find_one({"channelId": str(self.ticket_channel_id)})
            
            if ticket_data:
                # Log points for users
                user_ids = [str(uid) for uid in [ticket_data.get("user1"), ticket_data.get("user2")] if uid]
                for uid in user_ids:
                    await points_coll.update_one(
                        {"userId": uid},
                        {"$inc": {"points": 1}, "$setOnInsert": {"userId": uid}},
                        upsert=True
                    )

                # Increment MM completed tickets
                claimed_by = ticket_data.get("claimedBy")
                if claimed_by:
                    try:
                        mm_id = int(claimed_by)
                    except:
                        mm_id = claimed_by
                    await mm_coll.update_one({"_id": mm_id}, {"$inc": {"completed": 1}}, upsert=True)

                await interaction.followup.send("✅ Points logged successfully!", ephemeral=True)
        except Exception as e:
            print(f"Points logging error: {e}")
            await interaction.followup.send(f"⚠️ Points logging failed: {e}", ephemeral=True)

        # Delete the ticket channel
        try:
            await ticket_channel.delete(reason="Vouch detected and confirmed by MM")
        except Exception as e:
            print(f"Channel deletion error: {e}")
            await interaction.followup.send(f"❌ Could not delete channel: {e}", ephemeral=True)

    except Exception as e:
        print(f"Vouch confirmation error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

@discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="vouch_cancel")
async def cancel_button(self, interaction: discord.Interaction, button: Button):
    await interaction.response.defer(ephemeral=True)
    await interaction.message.delete()
    await interaction.followup.send("❌ Vouch confirmation cancelled.", ephemeral=True)
```

# ———————–– Vouch Detector Cog ———————––

class VouchDetector(commands.Cog):
def **init**(self, bot):
self.bot = bot

```
def _contains_vouch(self, content: str) -> bool:
    """Check if message contains vouch keywords"""
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in VOUCH_KEYWORDS)

async def _get_ticket_info(self, channel_id: int):
    """Get ticket information from database"""
    colls = await collections()
    tickets_coll = colls["tickets"]
    return await tickets_coll.find_one({"channelId": str(channel_id)})

@commands.Cog.listener()
async def on_message(self, message: discord.Message):
    # Ignore bot messages
    if message.author.bot:
        return

    # Check if message is in a configured vouch channel
    mm_id = None
    for mid, config in MM_VOUCH_CONFIG.items():
        if (message.guild and 
            message.guild.id == config["server_id"] and 
            message.channel.id == config["channel_id"]):
            mm_id = mid
            break

    if not mm_id:
        return

    # Check if message contains vouch keywords
    if not self._contains_vouch(message.content):
        return

    # Find the MM's active ticket in the main server
    try:
        # Get the main guild (where tickets are)
        main_guild = None
        for guild in self.bot.guilds:
            category = guild.get_channel(TICKET_CATEGORY_ID)
            if category:
                main_guild = guild
                break

        if not main_guild:
            return

        # Find MM member in main guild
        mm_member = main_guild.get_member(mm_id)
        if not mm_member:
            return

        # Search for MM's claimed ticket
        colls = await collections()
        tickets_coll = colls["tickets"]
        
        ticket_data = await tickets_coll.find_one({"claimedBy": str(mm_id)})
        if not ticket_data:
            return

        ticket_channel_id = int(ticket_data["channelId"])
        ticket_channel = main_guild.get_channel(ticket_channel_id)
        
        if not ticket_channel:
            return

        # Check if the vouch is from a user in the ticket
        user_ids = [ticket_data.get("user1"), ticket_data.get("user2")]
        if str(message.author.id) not in [str(uid) for uid in user_ids if uid]:
            return

        # Send confirmation to MM in the ticket channel
        vouch_link = message.jump_url
        
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

        view = VouchConfirmView(ticket_channel_id, vouch_link)
        
        await ticket_channel.send(
            content=mm_member.mention,
            embed=embed,
            view=view
        )

    except Exception as e:
        print(f"Vouch detection error: {e}")
```

# ———————––

# Cog setup

# ———————––

async def setup(bot):
await bot.add_cog(VouchDetector(bot))