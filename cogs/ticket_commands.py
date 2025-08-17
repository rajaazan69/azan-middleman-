import os
import discord
from discord.ext import commands
from utils.constants import TICKET_CATEGORY_ID, OWNER_ID
from utils.db import collections
from datetime import datetime

class TicketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- ADD USER ----------
    @commands.command(name="add", help="Adds a user to the current ticket channel.")
    async def add(self, ctx, member: discord.Member):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only add users in ticket channels.")
        await ch.set_permissions(member, send_messages=True, view_channel=True)
        await ctx.send(f"✅ {member.mention} added.")

    # ---------- REMOVE USER ----------
    @commands.command(name="remove", help="Removes a user from the current ticket channel.")
    async def remove(self, ctx, member: discord.Member):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only remove users in ticket channels.")
        await ch.set_permissions(member, overwrite=None)
        await ctx.send(f"✅ {member.mention} removed.")

    # ---------- RENAME TICKET ----------
    @commands.command(name="rename", help="Renames the current ticket channel.")
    async def rename(self, ctx, *, new_name: str):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only rename ticket channels.")
        await ch.edit(name=new_name)
        await ctx.send(f"✅ Renamed to `{new_name}`.")
    # ---------- RESET LEADERBOARD ----------
    @commands.command(name="resetlb", help="Resets the client leaderboard.")
    async def resetlb(self, ctx):
        user = ctx.author
        member = ctx.author
        is_owner = user.id == OWNER_ID
        is_admin = ctx.author.guild_permissions.administrator
        if not is_owner and not is_admin:
            return await ctx.send("❌ You do not have permission to reset the leaderboard.")

        colls = await collections()
        await colls['clientPoints'].delete_many({})

        # Update leaderboard message
        try:
            leaderboard_channel = ctx.guild.get_channel(int(os.getenv("LB_CHANNEL_ID")))
            leaderboard_message = await leaderboard_channel.fetch_message(int(os.getenv("LB_MESSAGE_ID")))
            embed = discord.Embed(title="🏆 Client Leaderboard", description="No points recorded yet!", color=0xFFD700)
            await leaderboard_message.edit(embed=embed)
        except:
            pass

        await ctx.send("✅ Leaderboard has been reset.")


async def setup(bot):
    await bot.add_cog(TicketCommands(bot))