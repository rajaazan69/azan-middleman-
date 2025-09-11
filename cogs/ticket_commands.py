import os
import discord
from discord.ext import commands
from utils.constants import TICKET_CATEGORY_ID, OWNER_ID
from utils.db import collections

ALLOWED_ROLE_ID = 1373029428409405500  # special staff role


def has_ticket_perms():
    async def predicate(ctx: commands.Context):
        if ctx.author.guild_permissions.administrator:
            return True
        role = discord.utils.get(ctx.author.roles, id=ALLOWED_ROLE_ID)
        return role is not None
    return commands.check(predicate)


class TicketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- ADD USER ----------
    @commands.command(name="add", help="Adds a user to the current ticket channel.")
    @has_ticket_perms()
    async def add(self, ctx, member: discord.Member):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only add users in ticket channels.")
        await ch.set_permissions(member, send_messages=True, view_channel=True)
        await ctx.send(f"✅ {member.mention} added.")

    # ---------- REMOVE USER ----------
    @commands.command(name="remove", help="Removes a user from the current ticket channel.")
    @has_ticket_perms()
    async def remove(self, ctx, member: discord.Member):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only remove users in ticket channels.")
        await ch.set_permissions(member, overwrite=None)
        await ctx.send(f"✅ {member.mention} removed.")

    # ---------- DELETE TICKET ----------
    @commands.command(name="delete", help="Deletes the current ticket channel.")
    @has_ticket_perms()
    async def delete(self, ctx):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only delete ticket channels.")
        try:
            await ch.delete()
        except Exception as e:
            await ctx.send(f"❌ Failed to delete channel: {e}")

    # ---------- RENAME TICKET ----------
    @commands.command(name="rename", help="Renames the current ticket channel.")
    @has_ticket_perms()
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
        is_owner = user.id == OWNER_ID
        is_admin = ctx.author.guild_permissions.administrator
        if not is_owner and not is_admin:
            return await ctx.send("❌ You do not have permission to reset the leaderboard.")

        colls = await collections()
        await colls['clientPoints'].delete_many({})

        try:
            leaderboard_channel = ctx.guild.get_channel(int(os.getenv("LB_CHANNEL_ID")))
            leaderboard_message = await leaderboard_channel.fetch_message(int(os.getenv("LB_MESSAGE_ID")))
            embed = discord.Embed(title="🏆 Client Leaderboard", description="No points recorded yet!", color=0xFFD700)
            await leaderboard_message.edit(embed=embed)
        except:
            pass

        await ctx.send("✅ Leaderboard has been reset.")

    # ---------- SAY COMMAND ----------
    @commands.command(name="say", help="Make the bot say anything.")
    @commands.has_permissions(administrator=True)
    async def say(self, ctx, *, message: str):
        await ctx.message.delete()
        await ctx.send(message)

    # ---------- OPEN TICKET ----------
    @commands.command(name="open", help="Reopens a closed ticket.")
    @has_ticket_perms()
    async def open(self, ctx):
        ch = ctx.channel
        if ch.category_id != TICKET_CATEGORY_ID:
            return await ctx.send("❌ You can only open ticket channels.")
        
        overwrites = ch.overwrites
        for target, perms in overwrites.items():
            if perms.view_channel is False:
                await ch.set_permissions(target, view_channel=True, send_messages=True)

        await ctx.send("✅ Ticket reopened.")


async def setup(bot):
    await bot.add_cog(TicketCommands(bot))