import discord
from discord.ext import commands
from datetime import datetime
from utils.constants import TICKET_CATEGORY_ID
from utils.db import collections

# Hardcoded leaderboard IDs
LEADERBOARD_CHANNEL_ID = 1402387584860033106
LEADERBOARD_MESSAGE_ID = 1402392182425387050

class TicketPoints(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_points(self, channel: discord.TextChannel):
        """
        Log points for the ticket users and update leaderboard.
        Only handles DB operations; does NOT touch interaction responses.
        """
        colls = await collections()
        tickets_coll = colls["tickets"]
        points_coll = colls["clientPoints"]

        # Check if this is a ticket channel
        if channel.category_id != TICKET_CATEGORY_ID:
            print(f"❌ Channel {channel.id} is not a ticket channel.")
            return None

        # Get ticket data
        ticket_data = await tickets_coll.find_one({"channelId": str(channel.id)})
        if not ticket_data:
            print(f"❌ No ticket data found for channel {channel.id}.")
            return None

        user_ids = [ticket_data.get("user1"), ticket_data.get("user2")]
        user_ids = [uid for uid in user_ids if uid]

        if not user_ids:
            print(f"❌ No users found in ticket {channel.id} to log points for.")
            return None

        # Add points to DB
        for uid in user_ids:
            await points_coll.update_one({"userId": uid}, {"$inc": {"points": 1}}, upsert=True)

        guild = channel.guild
        leaderboard_channel = guild.get_channel(LEADERBOARD_CHANNEL_ID)
        if not leaderboard_channel:
            print(f"❌ Could not find leaderboard channel with ID {LEADERBOARD_CHANNEL_ID}")
            return user_ids

        # Try fetching the leaderboard message; if missing, create a new one
        try:
            leaderboard_message = await leaderboard_channel.fetch_message(LEADERBOARD_MESSAGE_ID)
        except Exception:
            print("⚠️ Leaderboard message missing, sending a new one.")
            embed = discord.Embed(
                title="🏆 Top Clients This Month",
                description="No data yet.",
                color=0x2B2D31,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Client Leaderboard")
            leaderboard_message = await leaderboard_channel.send(embed=embed)

        # Build leaderboard embed
        try:
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

        return user_ids  # Return who got points for followup messages


# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(TicketPoints(bot))