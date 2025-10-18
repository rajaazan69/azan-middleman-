# ticketpoints.py
import discord
from discord.ext import commands
from datetime import datetime
from utils.db import collections
import os

LEADERBOARD_CHANNEL_ID = 1402387584860033106
TICKET_CATEGORY_ID = 1373027564926406796  # Replace with your ticket category

class TicketPoints(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_points(self, channel: discord.TextChannel):
        if channel.category_id != TICKET_CATEGORY_ID:
            print(f"❌ Channel {channel.id} is not a ticket channel.")
            return None

        colls = await collections()
        tickets_coll = colls["tickets"]
        points_coll = colls["clientPoints"]

        # Fetch ticket users
        ticket_data = await tickets_coll.find_one({"channelId": str(channel.id)})
        if not ticket_data:
            print(f"❌ No ticket data found for channel {channel.id}.")
            return None

        user_ids = [ticket_data.get("user1"), ticket_data.get("user2")]
        user_ids = [uid for uid in user_ids if uid]

        if not user_ids:
            print(f"❌ No users in ticket {channel.id} to log points for.")
            return None

        # Add points
        for uid in user_ids:
            await points_coll.update_one(
                {"userId": uid},
                {"$inc": {"points": 1}, "$setOnInsert": {"userId": uid}},
                upsert=True
            )

        # -------------------------------
        # Handle leaderboard
        # -------------------------------
        guild = channel.guild
        lb_channel = guild.get_channel(LEADERBOARD_CHANNEL_ID)
        if not lb_channel:
            print(f"❌ Leaderboard channel {LEADERBOARD_CHANNEL_ID} not found.")
            return user_ids

        # Try to fetch message ID from env
        lb_message_id = os.getenv("LEADERBOARD_MESSAGE_ID")
        lb_message = None
        if lb_message_id:
            try:
                lb_message = await lb_channel.fetch_message(int(lb_message_id))
            except Exception:
                lb_message = None

        # Create message if missing
        if not lb_message:
            embed = discord.Embed(
                title="# TOP CLIENTS THIS MONTH",
                description="> No data yet",
                color=0x2B2D31,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Client Leaderboard | Auto-updates")
            lb_message = await lb_channel.send(embed=embed)
            print(f"ℹ️ New leaderboard message created! ID: {lb_message.id}")
            print("Update your .env LEADERBOARD_MESSAGE_ID with this ID.")

        # Fetch top users
        top_users_cursor = points_coll.find().sort("points", -1).limit(10)
        top_users = await top_users_cursor.to_list(length=10)

        # Format leaderboard
        leaderboard_lines = []
        for i, user in enumerate(top_users):
            rank = f"#{i+1}"
            line = f"> **{rank} | <@{user['userId']}> | {user['points']} point{'s' if user['points'] != 1 else ''}**"
            leaderboard_lines.append(line)

        leaderboard_text = "\n".join(leaderboard_lines) or "> No data yet"

        # Update embed
        embed = discord.Embed(
            title="# TOP CLIENTS THIS MONTH",
            description=leaderboard_text,
            color=0x2B2D31,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Client Leaderboard | Auto-updates")
        await lb_message.edit(embed=embed)

        return user_ids

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(TicketPoints(bot))