import discord
from discord import app_commands
from discord.ext import commands

import os

from services.roster_service import RosterService
from services.name_service import format_full_name


class Verify(commands.Cog):

    # initialize from roster services 
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # set command "verify"
    @app_commands.command(
        name = "verify",
        description = "Verify your identity and set your server Discord nickname!"
        )
    
    # function to verify account and set username
    async def verify(self, 
                     interaction: discord.Interaction, 
                     identifier: str):
        """
        Students provide email, username, or user ID.
        Bot finds them in roster and sets nickname to full name.
        """
        # wait for response
        await interaction.response.defer(ephemeral = True)

        # build roster path using guild ID
        if not interaction.guild_id:
            await interaction.followup.send(
                "This command can only be used in a server."
                )
            return None

        guild_id = interaction.guild_id
        roster_path = f"data/classes/{guild_id}/students.xlsx"

        # ensure roster exists for this guild
        if not os.path.exists(roster_path):
            await interaction.followup.send(
                "Roster file not found for this server."
                "\nPlease contact the TA or Professor."
                )
            return None

        # initialize roster service per guild
        self.roster = RosterService(roster_path)

        # lookup student
        student = self.roster.find_student(identifier)

        # if the student is not found in the loopup
        if not student:
            # notify that the student was not found
            await interaction.followup.send(
                "You were not found in the roster."
                "\nPlease try a different method of verification and/or contact the TA or Professor."
                )
            return None


        # otherwise, the student has been found


        # Condition 1: REFORMAT NEW NAME
        try:
            # reformat new name from full name
            new_name = format_full_name(student["fullname"])
        
        # if there is a problem
        except Exception:
            # inform the user that there was an error with the name formatting in the roster file.
            await interaction.followup.send(
                "Name format error in roster."
                "\nPlease try a different method of verification and/or contact the TA or Professor."
                )
            return None



        # Condition 2: CHECK IF SERVER OWNER (can not be server own)
            # discord bots can not change the username of the server owner
            # if server owner, throw an error
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            await interaction.followup.send(
                f"You are the server owner!"
                f"\n Verification succeeded, and your nickname *would* be set to:"
                f"\n**{new_name}**"
                f"\n\n Discord does not allow bots to change the server owner's nickname."
            )
            return None



        # Condition 3: CHANGE NICKNAME
        try:
            # wait for the interaction to occur
            await interaction.user.edit(nick = new_name)

            # send confirmation of success
            await interaction.followup.send(
                f"Your nickname has been set to **{new_name}**!"
            )
        
        # if there is a problem
        except discord.Forbidden:
            # notify user that their nickname can not be changed.
            await interaction.followup.send(
                "I cannot change your nickname.\n"
                "Please ask a server administrator to check the permissions."
            )


# ADD TO COG (required)
async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))
