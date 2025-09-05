import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from db.crypto_json import save_crypto_address

# role allowed to use crypto commands
ALLOWED_ROLE_ID = 1373029428409405500


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # check if user is admin OR has allowed role
    def is_allowed():
        async def predicate(ctx):
            if ctx.author.guild_permissions.administrator:
                return True
            role = discord.utils.get(ctx.author.roles, id=ALLOWED_ROLE_ID)
            return role is not None
        return commands.check(predicate)

    # ---------- SAVE LTC ----------
    @commands.command(name="saveltc")
    @is_allowed()
    async def save_ltc(self, ctx, address: str):
        save_crypto_address(str(ctx.author.id), "LTC", address)
        await ctx.send(f"✅ Saved your **LTC** address: `{address}`")

    # ---------- SAVE ETH ----------
    @commands.command(name="saveeth")
    @is_allowed()
    async def save_eth(self, ctx, address: str):
        save_crypto_address(str(ctx.author.id), "ETH", address)
        await ctx.send(f"✅ Saved your **ETH** address: `{address}`")


async def setup(bot):
    await bot.add_cog(Crypto(bot))