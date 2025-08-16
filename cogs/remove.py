@commands.command(name="remove", help="Removes a user from the current ticket channel.")
@commands.has_permissions(manage_channels=True)
async def remove(self, ctx: commands.Context, user: discord.Member):
    channel = ctx.channel

    # Ensure this is a ticket channel
    if channel.category_id != TICKET_CATEGORY_ID:
        return await ctx.send("❌ You can only remove users in ticket channels!", delete_after=10)

    # Remove the user's permissions
    try:
        await channel.set_permissions(user, overwrite=None)  # removes any specific permissions
        await ctx.send(f"✅ {user.mention} has been removed from the ticket.", delete_after=10)
    except Exception as e:
        await ctx.send(f"❌ Error: {e}", delete_after=10)
