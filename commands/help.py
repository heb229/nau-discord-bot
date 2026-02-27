# IMPORTS
    # Discord
import discord
from discord import app_commands
from discord.ext import commands


# Class defining help command(s)
class Help(commands.Cog):
    # initlize self
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /help command set
    @app_commands.command(
        name = "help",
        description = "Show available bot commands")
    
    # function to define help
    async def help(self, interaction: discord.Interaction):
        """
        Displays available commands.
        Admin commands are only shown to administrators.
        """
        # checks permissions
        is_admin = interaction.user.guild_permissions.administrator

        # sets embed for formatting
        embed = discord.Embed(
            title = "Bot Commands",
            description = "Here are the commands you can use:",
            color = discord.Color.blurple()
            )

        # COMMANDS FOR EVERYONE
        embed.add_field(
            name = "Everyone",
            value = (
                "**`/verify <identifier>`**\n"
                "Verify your identity and set your nickname using your\n"
                "email, username, or student ID.\n\n"

                "**`/ask`**\n"
                "Set the context for the LLM chatbot. Then do /ask-question.\n\n"

                "**`/ask-question <question:str> <long:bool>`**\n"
                "Ask a **conceptual** question about course topics.\n"
                "_Homework answers and solutions are blocked._\n\n"

                "**`/info <topic>`**\n"
                "View class-related information such as office hours,\n"
                "class times, policies, or other instructor-provided info.\n"
                "Options <topic>: professor, office_hours, class_times, location, contact, syllabus.\n\n"

                "**`/ping`**\n"
                "Check if the bot is online.\n\n"

                ),
            inline = False
        )

        # COMMANDS ONLY FOR ADMIN
        if is_admin:
            embed.add_field(
                name = "Administrators",
                value = (
                    "**`/message post <channel> <content>`**\n"
                    "Post an announcement message as the bot.\n\n"

                    "**`/message edit <message_id> <content>`**\n"
                    "Edit a message previously sent by the bot.\n\n"

                    "**`/message delete <message_id>`**\n"
                    "Delete a message previously sent by the bot.\n\n"

                    "**`/class set`**\n"
                    "Configure class-specific settings for this server\n"
                    "(used for `/info` and class context).\n\n"

                    "**`/class view`**\n"
                    "View the current class configuration for this server."
                    ),
                inline = False
            )

        # Extra note
        embed.set_footer(
            text = "Some commands may be restricted based on your permissions."
        )

        # send the message
        await interaction.response.send_message(embed = embed, ephemeral = True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
