import os
from datetime import datetime
import discord
from discord.ext import commands
from utils.constants import TICKET_CATEGORY_ID, LEADERBOARD_CHANNEL_ID, LEADERBOARD_MESSAGE_ID
from utils.db import collections

class TicketPoints(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_points(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        colls = await collections()
        tickets_coll = colls["tickets"]
        points_coll = colls["clientPoints"]

        channel = interaction.channel
        guild = interaction.guild

        if not isinstance(channel, discord.TextChannel):
            return await interaction.followup.send("❌ This is not a text channel.", ephemeral=True)

        if channel.category_id != TICKET_CATEGORY_ID:
            return await interaction.followup.send("❌ This button can only be used inside ticket channels.", ephemeral=True)

        # Get ticket data
        ticket_data = await tickets_coll.find_one({"channelId": str(channel.id)})
        if not ticket_data:
            return await interaction.followup.send("❌ Could not find ticket data.", ephemeral=True)

        user_ids = [ticket_data.get("user1"), ticket_data.get("user2")]
        user_ids = [uid for uid in user_ids if uid]

        if not user_ids:
            return await interaction.followup.send("❌ No users to log points for.", ephemeral=True)

        # Add points
        for uid in user_ids:
            await points_coll.update_one({"userId": uid}, {"$inc": {"points": 1}}, upsert=True)

        # Update leaderboard
        if LEADERBOARD_CHANNEL_ID and LEADERBOARD_MESSAGE_ID:
            leaderboard_channel = guild.get_channel(LEADERBOARD_CHANNEL_ID)
            if leaderboard_channel:
                try:
                    leaderboard_message = await leaderboard_channel.fetch_message(LEADERBOARD_MESSAGE_ID)
                    top_cursor = points_coll.find().sort("points", -1).limit(10)
                    top_users = await top_cursor.to_list(length=10)
                    leaderboard_text = "\n".join(
                        f"**#{i+1}** <@{user['userId']}> — **{user['points']}** point{'s' if user['points'] != 1 else ''}"
                        for i, user in enumerate(top_users)
                    ) or "No data yet."

                    embed = discord.Embed(
                        title="🏆 Top Clients This Month",
                        description=leaderboard_text,
                        color=0x2B2D31,
                        timestamp=datetime.utcnow()
                    )
                    embed.set_footer(text="Client Leaderboard")
                    await leaderboard_message.edit(embed=embed)
                except Exception as e:
                    print("❌ Error updating leaderboard:", e)

        await interaction.followup.send(f"✅ Logged 1 point for <@{'>, <@'.join(user_ids)}>.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketPoints(bot))