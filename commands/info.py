# pulls from data/classes where the filename is the
# discord_server_id.json


# IMPORTS
    # Discord
import discord
from discord import app_commands
from discord.ext import commands

    # Self
from services.class_info_service import ClassInfoService


# Class degining general course information
class Info(commands.Cog):
    # initilize self
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # set command name
    @app_commands.command(
        name = "info",
        description = "Get class information")
    # set command description
    @app_commands.describe(topic = "What information you want")

    
    # function allowing users to find information about the course
    async def info(self, interaction: discord.Interaction, topic: str):
        # set service and data
        service = ClassInfoService(interaction.guild.id)
        data = service.load()

        # if there is no course information
            # then inform the user
        if not data:
            await interaction.response.send_message(
                "Class information has not been set up yet.",
                ephemeral = True)
            return None

        # set topic to allow lowercase for string matching
        topic = topic.lower()

        # if the asked topic is not in the course information
            # then tell the user that their topic isn't available
        if topic not in data:
            await interaction.response.send_message(
                f"No information found for `{topic}`.",
                ephemeral = True
                )
            return None

        # set embed (for formatting)
        embed = discord.Embed(
            title = data.get("class_name", "Class Information"),
            description = data[topic],
            color = discord.Color.blurple())

        await interaction.response.send_message(embed = embed, ephemeral = True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
