import discord
from discord.ext import commands
from db.crypto_json import get_crypto_address

# ---------------- Crypto Buttons View ----------------
class CryptoButtonView(discord.ui.View):
    def __init__(self, mm_id: int):
        super().__init__(timeout=None)
        self.mm_id = mm_id  # claimed middleman ID

    # ---------- LTC Button ----------
    @discord.ui.button(
        label="LTC Address",
        emoji="<:emoji_27:1413667063951659038>",
        style=discord.ButtonStyle.primary,
        custom_id="show_ltc"
    )
    async def show_ltc(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Restrict access: only middleman or admin role
        if interaction.user.id != self.mm_id and not any(role.id == 1373029428409405500 for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You cannot use this button.")

        address = get_crypto_address(str(self.mm_id), "LTC")
        if not address:
            return await interaction.response.send_message("❌ **No LTC address saved for this middleman.**")

        embed = discord.Embed(
            title="__**• LTC Address •**__",
            description=f"**Address:**\n`{address}`\n\n**⚠️ Warning:** *Funds sent to the wrong address will be lost!*",
            color=0x000000
        )
        embed.set_thumbnail(url="https://cryptologos.cc/logos/litecoin-ltc-logo.png")
        await interaction.response.send_message(embed=embed)

    # ---------- ETH Button ----------
    @discord.ui.button(
        label="ETH Address",
        emoji="<:emoji_26:1413666923756912640>",
        style=discord.ButtonStyle.primary,
        custom_id="show_eth"
    )
    async def show_eth(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Restrict access: only middleman or admin role
        if interaction.user.id != self.mm_id and not any(role.id == 1373029428409405500 for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You cannot use this button.")

        address = get_crypto_address(str(self.mm_id), "ETH")
        if not address:
            return await interaction.response.send_message("❌ **No ETH address saved for this middleman.**")

        embed = discord.Embed(
            title="__**• ETH Address •**__",
            description=f"**Address:**\n`{address}`\n\n**⚠️ Warning:** *Funds sent to the wrong address will be lost!*",
            color=0x000000
        )
        embed.set_thumbnail(url="https://cryptologos.cc/logos/ethereum-eth-logo.png")
        await interaction.response.send_message(embed=embed)


# ---------------- Cog Registration ----------------
class CryptoButtons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ CryptoButtons loaded")


async def setup(bot):
    await bot.add_cog(CryptoButtons(bot))