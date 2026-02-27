# IMPORTS

    # Discord
import discord
from discord import app_commands
from discord.ext import commands

    # Self
from services.class_info_service import ClassInfoService
from commands.constants import *



# Class defining admins (for admin only commands)
class ClassAdmin(commands.Cog):
    # initialize
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # slash command group: /class
        # allows setting of class (IE: CS249)
    class_group = app_commands.Group(
        name = "class",
        description = "Class setup and administration commands"
        )

    # /class set
    @class_group.command(
        name = "set",
        description = "Set or update class information"
    )
        # check permission of user
    @app_commands.checks.has_permissions(administrator = True)
        # describe the command
    @app_commands.describe(
        key = "What you are setting (e.g. office_hours, class_times)",
        value = "The value to store"
        )
    
    # function to allow for a class to be set
    async def class_set( self,
                        interaction: discord.Interaction,
                        key: str,
                        value: str):
        
        # set service and data
        service = ClassInfoService(interaction.guild.id)
        data = service.load() or {}

        data[key] = value
        service.save(data)

        # when set, send a message noting that the class was updated
        await interaction.response.send_message(
            f"`{key}` updated successfully.",
            ephemeral = True)

    # /class show (optional but useful)
        # allows admin to check and make sure the right class is set
    @class_group.command(
        name = "show",
        description = "Show all stored class information"
        )
    
        # check permission of user
    @app_commands.checks.has_permissions(administrator = True)


    # function to allow user to see the set class
    async def class_show(self, interaction: discord.Interaction):
        # set service and data
        service = ClassInfoService(interaction.guild.id)
        data = service.load()

        # if no data (the class isn't set) then inform the user
        if not data:
            await interaction.response.send_message(
                "No class information has been set yet.",
                ephemeral = True)
            return None

        # set embed (formatting)
        embed = discord.Embed(
            title = "Current Class Information",
            color = discord.Color.green())

        # for all the data items, throw them in
            # to display to user about the class
        for key, value in data.items():
            embed.add_field(name = key, value = value, inline = False)

        # then send a message when ready
        await interaction.response.send_message(embed = embed, ephemeral = True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ClassAdmin(bot))
