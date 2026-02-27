import discord
from discord import app_commands
from discord.ext import commands


# Class for using the bot to send messages
class Message(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # check permissions (must be admin)
    def is_admin(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    # set the command group (/message)-
    message = app_commands.Group(
        name = "message",
        description = "Post, edit, or delete bot messages (Admin only)"
    )



    # POST A MESSAGE
    @message.command(name = "post", description = "Post a message as the bot")
    async def post( self,
                    interaction: discord.Interaction,
                    channel: discord.TextChannel,
                    content: str):

        # ensure user is an admin
        if not self.is_admin(interaction):
            await interaction.response.send_message(
                "❌ You must be an administrator to use this command.",
                ephemeral = True)
            return

        # defer response
        await interaction.response.defer(ephemeral=True)

        # send the message is the correct channel
        msg = await channel.send(content)

        # inform success to user sending the message
        await interaction.followup.send(
            f"✅ Message posted in {channel.mention}\n"
            f"Message ID: `{msg.id}`")



    # EDIT A MESSAGE
    @message.command(name = "edit", description = "Edit a previously posted bot message")
    async def edit( self,
                    interaction: discord.Interaction,
                    channel: discord.TextChannel,
                    message_id: str,
                    new_content: str):
        
        # ensure user is an admin
        if not self.is_admin(interaction):

            await interaction.response.send_message(
                "❌ You must be an administrator to use this command.",
                ephemeral = True)
            return

        # refer response
        await interaction.response.defer(ephemeral=True)

        # try to grab the message
        try:
            msg = await channel.fetch_message(int(message_id))

        # if the message doesn't exist, inform of not found
        except discord.NotFound:
            await interaction.followup.send("❌ Message not found.")
            return

        # if the message isn't from the bot
        if msg.author != self.bot.user:
            # inform the user that it can only edits messages it sent
            await interaction.followup.send(
                "❌ I can only edit messages that I posted."
            )
            return

        # edit the message and add new context
        await msg.edit(content = new_content)
        # inform of success
        await interaction.followup.send("✅ Message edited successfully.")



    # DELETE MESSAGE
    @message.command(name = "delete", description = "Delete a bot message")
    async def delete( self,
                    interaction: discord.Interaction,
                    channel: discord.TextChannel,
                    message_id: str):

        # ensure user is an admin
        if not self.is_admin(interaction):
            await interaction.response.send_message(
                "❌ You must be an administrator to use this command.",
                ephemeral = True)
            return

        # defer response
        await interaction.response.defer(ephemeral=True)

        # attempt to fetch selected message
        try:
            msg = await channel.fetch_message(int(message_id))
        # inform message not found if not exist
        except discord.NotFound:
            await interaction.followup.send("❌ Message not found.")
            return

        # make sure the bot was the one who sent the message
            # inform if not
        if msg.author != self.bot.user:
            await interaction.followup.send(
                "❌ I can only delete messages that I posted."
            )
            return

        # delete the message
        await msg.delete()
        # inform success
        await interaction.followup.send("🗑️ Message deleted successfully.")


# Required setup function
async def setup(bot: commands.Bot):
    await bot.add_cog(Message(bot))
