import discord
from discord.ext import commands

class VouchCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="vouch", help="Send a DM to someone asking them to vouch for you.")
    async def a_command(self, ctx, middleman_id: int):
        # Check permissions: only middlemen + admin can run
        allowed_role_id = 1373029428409405500
        has_role = any(r.id == allowed_role_id for r in ctx.author.roles)
        is_admin = ctx.author.guild_permissions.administrator
        if not (has_role or is_admin):
            return await ctx.reply("❌ You don’t have permission to use this command.", mention_author=False)
        if not member:
            return await ctx.send("❌ Please mention a user to vouch.")

        try:
            embed = discord.Embed(
                title="Vouch Request",
                description=(
                    f"Hello {member.mention},\n\n"
                    f"{ctx.author.mention} has requested a vouch from you.\n\n"
                    "If you have traded or interacted with them, "
                    "please consider leaving a vouch to help build their credibility."
                ),
                color=0x000000
            )
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()

            await member.send(embed=embed)

            confirmation = discord.Embed(
                description=f"A vouch request has been sent to {member.mention}.",
                color=0x000000
            )
            await ctx.send(embed=confirmation)

        except discord.Forbidden:
            await ctx.send(f"❌ I couldn't DM {member.mention}. They may have DMs disabled.")
        except Exception as e:
            await ctx.send(f"❌ Something went wrong: {e}")

async def setup(bot):
    await bot.add_cog(VouchCommand(bot))