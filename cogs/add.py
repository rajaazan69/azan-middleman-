@commands.command(name="add", help="Adds a user to the current ticket channel.")
@commands.has_permissions(manage_channels=True)
async def add(self, ctx: commands.Context, user: discord.Member):
    channel = ctx.channel

    # Ensure this is a ticket channel
    if channel.category_id != TICKET_CATEGORY_ID:
        return await ctx.send("❌ You can only add users in ticket channels!", delete_after=10)

    # Give the user permissions
    try:
        await channel.set_permissions(user, send_messages=True, view_channel=True)
        await ctx.send(f"✅ {user.mention} has been added to the ticket.", delete_after=10)
    except Exception as e:
        await ctx.send(f"❌ Error: {e}", delete_after=10)
