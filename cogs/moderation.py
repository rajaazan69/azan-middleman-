import discord
from discord.ext import commands
from utils.constants import EMBED_COLOR

class Moderation(commands.Cog):
    def __init__(self, bot): self.bot = bot

    def mod_embed(self, title, description):
        return discord.Embed(title=title, description=description, color=EMBED_COLOR)

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        await member.ban(reason=reason)
        e = self.mod_embed("User Banned", f"**User**: {member} (<@{member.id}>)\n**Reason**: {reason}\n**Moderator**: {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        await member.kick(reason=reason)
        e = self.mod_embed("User Kicked", f"**User**: {member} (<@{member.id}>)\n**Reason**: {reason}\n**Moderator**: {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    @commands.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided."):
        # duration like 10m, 1h, 2d
        ms = {"s":1, "m":60, "h":3600, "d":86400}
        try:
            secs = int(duration[:-1]) * ms[duration[-1]]
        except Exception:
            return await ctx.reply("❌ Invalid duration. Use like `10m`, `1h`.", mention_author=False)
        await member.timeout(discord.utils.utcnow() + discord.timedelta(seconds=secs), reason=reason)
        e = self.mod_embed("User Timed Out",
                           f"**User:** <@{member.id}> ({member})\n**Duration:** {duration}\n**Reason:** {reason}\n**Moderator:** {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    @commands.command(name="untimeout")
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        await member.timeout(None, reason=reason)
        e = self.mod_embed("Timeout Removed",
                           f"**User:** <@{member.id}> ({member})\n**Reason:** {reason}\n**Moderator:** {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
        e = self.mod_embed("User Warned",
                           f"**User:** <@{member.id}> ({member})\n**Reason:** {reason}\n**Moderator:** {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        e = self.mod_embed("Channel Locked", f"**Channel:** {ctx.channel.name}\n**Locked by:** {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        e = self.mod_embed("Channel Unlocked", f"**Channel:** {ctx.channel.name}\n**Unlocked by:** {ctx.author}")
        await ctx.reply(embed=e, mention_author=False)

async def setup(bot):
    await bot.add_cog(Moderation(bot))