import discord
from discord.ext import commands
from utils.constants import EMBED_COLOR
import datetime

MM_BANNED_ROLE_ID = 1395343230832349194  # MM Banned role
MAX_TIMEOUT_SECONDS = 28 * 24 * 60 * 60  # Discord max: 28 days

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def mod_embed(self, title, description):
        return discord.Embed(title=title, description=description, color=EMBED_COLOR)

    # -------------------- Ban --------------------
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        await member.ban(reason=reason)
        e = self.mod_embed("User Banned", f"**User**: {member} (<@{member.id}>)\n**Reason**: {reason}\n**Moderator**: {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    # -------------------- Unban --------------------
    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban(self, ctx, user_id: int, *, reason: str = "No reason provided."):
        user = await self.bot.fetch_user(user_id)
        try:
            await ctx.guild.unban(user, reason=reason)
        except discord.NotFound:
            return await ctx.reply("❌ That user is **not banned** in this server.", mention_author=False)
        except discord.Forbidden:
            return await ctx.reply("❌ I don’t have permission to unban that user.", mention_author=False)
        except discord.HTTPException as exc:
            return await ctx.reply(f"❌ Failed to unban: `{exc}`", mention_author=False)

        e = self.mod_embed("User Unbanned", f"**User**: {user} (<@{user.id}>)\n**Reason**: {reason}\n**Moderator**: {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    # -------------------- Kick --------------------
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        await member.kick(reason=reason)
        e = self.mod_embed("User Kicked", f"**User**: {member} (<@{member.id}>)\n**Reason**: {reason}\n**Moderator**: {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    # -------------------- Mute (Timeout) --------------------
    @commands.command(name="mute", aliases=["timeout"])
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def mute(self, ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided."):
        # Safety checks (role hierarchy / admin / owner)
        if member == ctx.guild.owner:
            return await ctx.reply("❌ Can't mute the server owner.", mention_author=False)
        if member.guild_permissions.administrator:
            return await ctx.reply("❌ Can't mute an administrator.", mention_author=False)
        if ctx.author != ctx.guild.owner and member.top_role >= ctx.author.top_role:
            return await ctx.reply("❌ You can't mute someone with an equal or higher role.", mention_author=False)
        if ctx.guild.me.top_role <= member.top_role:
            return await ctx.reply("❌ My role is not high enough to mute that member.", mention_author=False)

        # Parse duration like 10s/10m/2h/1d (case-insensitive)
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            unit = duration[-1].lower()
            amount = int(duration[:-1])
            if unit not in units or amount <= 0:
                raise ValueError
            secs = amount * units[unit]
        except Exception:
            return await ctx.reply("❌ Invalid duration. Use like `10m`, `1h`, `2d`.", mention_author=False)

        if secs > MAX_TIMEOUT_SECONDS:
            return await ctx.reply("❌ Max mute is **28 days**. Please choose a shorter duration.", mention_author=False)

        until = discord.utils.utcnow() + datetime.timedelta(seconds=secs)

        try:
            # Prefer the official kwarg (discord.py 2.x)
            await member.edit(timed_out_until=until, reason=reason)
        except TypeError:
            # Fallback for forks that use a method
            if hasattr(member, "timeout"):
                await member.timeout(until=until, reason=reason)  # py-cord style
            else:
                raise
        except discord.Forbidden:
            return await ctx.reply("❌ I don't have permission to mute that member.", mention_author=False)
        except discord.HTTPException as exc:
            return await ctx.reply(f"❌ Failed to mute: `{exc}`", mention_author=False)

        e = self.mod_embed(
            "User Muted",
            f"**User:** <@{member.id}> ({member})\n"
            f"**Duration:** {duration}\n"
            f"**Reason:** {reason}\n"
            f"**Moderator:** {ctx.author}"
        )
        await ctx.reply(embed=e, mention_author=False)

    # -------------------- Unmute (Remove Timeout) --------------------
    @commands.command(name="unmute", aliases=["untimeout"])
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def unmute(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        try:
            await member.edit(timed_out_until=None, reason=reason)
        except TypeError:
            if hasattr(member, "timeout"):
                await member.timeout(until=None, reason=reason)  # py-cord style
            else:
                raise
        except discord.Forbidden:
            return await ctx.reply("❌ I don't have permission to unmute that member.", mention_author=False)
        except discord.HTTPException as exc:
            return await ctx.reply(f"❌ Failed to unmute: `{exc}`", mention_author=False)

        e = self.mod_embed(
            "User Unmuted",
            f"**User:** <@{member.id}> ({member})\n"
            f"**Reason:** {reason}\n"
            f"**Moderator:** {ctx.author}"
        )
        await ctx.reply(embed=e, mention_author=False)

    # -------------------- Warn --------------------
    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        e = self.mod_embed("User Warned",
                           f"**User:** <@{member.id}> ({member})\n**Reason:** {reason}\n**Moderator:** {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    # -------------------- Lock --------------------
    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def lock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        e = self.mod_embed("Channel Locked", f"**Channel:** {ctx.channel.name}\n**Locked by:** {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    # -------------------- Unlock --------------------
    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        e = self.mod_embed("Channel Unlocked", f"**Channel:** {ctx.channel.name}\n**Unlocked by:** {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    # -------------------- MM Ban --------------------
    @commands.command(name="mmban")
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def mm_ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        role = ctx.guild.get_role(MM_BANNED_ROLE_ID)
        if not role:
            return await ctx.reply("❌ MM Banned role not found.", mention_author=False)

        await member.add_roles(role, reason=reason)
        e = self.mod_embed("Middleman Banned",
                           f"**User:** <@{member.id}> ({member})\n**Reason:** {reason}\n**Moderator:** {ctx.author}\n**Action:** Added MM Banned role")
        await ctx.reply(embed=e, mention_author=False)

    # -------------------- Role Command (Toggle) --------------------
    @commands.command(name="role")
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def role(self, ctx, member: discord.Member, role: discord.Role, *, reason: str = "No reason provided."):
        if role in member.roles:
            await member.remove_roles(role, reason=reason)
            e = self.mod_embed(
                "Role Removed",
                f"**User:** <@{member.id}> ({member})\n"
                f"**Role:** {role.mention}\n"
                f"**Reason:** {reason}\n"
                f"**Moderator:** {ctx.author}"
            )
        else:
            await member.add_roles(role, reason=reason)
            e = self.mod_embed(
                "Role Assigned",
                f"**User:** <@{member.id}> ({member})\n"
                f"**Role:** {role.mention}\n"
                f"**Reason:** {reason}\n"
                f"**Moderator:** {ctx.author}"
            )
        await ctx.reply(embed=e, mention_author=False)


async def setup(bot):
    await bot.add_cog(Moderation(bot))