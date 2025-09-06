import discord
from discord.ext import commands
from datetime import datetime

EMBED_COLOR = 0x000000  # same color scheme

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- SERVER INFO ---------------- #
    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        owner = guild.owner

        embed = discord.Embed(
            title=f"Server Information - {guild.name}",
            color=EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)

        embed.add_field(name="**Owner**", value=f"{owner.mention} (`{owner}`)", inline=True)
        embed.add_field(name="**Server ID**", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="**Created On**", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=False)

        embed.add_field(name="**Members**", value=f"{guild.member_count}", inline=True)
        embed.add_field(name="**Roles**", value=f"{len(guild.roles)}", inline=True)
        embed.add_field(name="**Channels**", value=f"Text: {len(guild.text_channels)}\nVoice: {len(guild.voice_channels)}", inline=True)

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ---------------- WHOIS ---------------- #
    @commands.command(name="whois")
    async def whois(self, ctx, member: discord.Member = None):
        member = member or ctx.author  # default to command invoker

        embed = discord.Embed(
            title=f"User Information - {member}",
            color=EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="**Username**", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="**Nickname**", value=f"{member.nick if member.nick else 'None'}", inline=True)
        embed.add_field(name="**Top Role**", value=f"{member.top_role.mention}", inline=True)
        embed.add_field(name="**Joined Server**", value=f"<t:{int(member.joined_at.timestamp())}:F>", inline=False)
        embed.add_field(name="**Account Created**", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=False)

        roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
        embed.add_field(name="**Roles**", value=" ".join(roles) if roles else "None", inline=False)

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ServerInfo(bot))