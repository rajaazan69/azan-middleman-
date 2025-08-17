import discord
from discord.ext import commands
from datetime import datetime
from utils.db import collections

# Hardcoded leaderboard IDs
LEADERBOARD_CHANNEL_ID = 1402387584860033106
LEADERBOARD_MESSAGE_ID = 1402392182425387050

class TicketPoints(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_points(self, channel: discord.TextChannel):
        """
        Log points for ticket users and update leaderboard.
        Returns the list of user IDs who got points.
        """
        colls = await collections()
        tickets_coll = colls["tickets"]
        points_coll = colls["clientPoints"]

        # Ensure this is a ticket channel
        if channel.category_id is None:
            print(f"❌ Channel {channel.id} has no category_id.")
            return []

        # Get ticket data
        ticket_data = await tickets_coll.find_one({"channelId": str(channel.id)})
        if not ticket_data:
            print(f"❌ No ticket data for channel {channel.id}")
            return []

        user_ids = [ticket_data.get("user1"), ticket_data.get("user2")]
        user_ids = [uid for uid in user_ids if uid]
        if not user_ids:
            print(f"❌ No users in ticket {channel.id}")
            return []

        # Add points
        for uid in user_ids:
            await points_coll.update_one({"userId": uid}, {"$inc": {"points": 1}}, upsert=True)

        # Update leaderboard
        guild = channel.guild
        lb_channel = guild.get_channel(LEADERBOARD_CHANNEL_ID)
        if not lb_channel:
            print(f"❌ Leaderboard channel {LEADERBOARD_CHANNEL_ID} not found")
            return user_ids

        # Try fetching existing message
        lb_message = None
        try:
            lb_message = await lb_channel.fetch_message(LEADERBOARD_MESSAGE_ID)
        except Exception:
            # Create a new leaderboard message if not found
            embed = discord.Embed(
                title="🏆 Top Clients This Month",
                description="No data yet.",
                color=0x2B2D31,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Client Leaderboard")
            lb_message = await lb_channel.send(embed=embed)
            print(f"ℹ️ Created new leaderboard message with ID {lb_message.id}")

        # Build top 10 leaderboard
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

        try:
            await lb_message.edit(embed=embed)
        except Exception as e:
            print(f"❌ Failed to update leaderboard: {e}")

        return user_ids  # Return IDs for confirmation
        

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(TicketPoints(bot))