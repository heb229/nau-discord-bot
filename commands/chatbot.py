# Imports

    # Discord
import discord
from discord import app_commands
from discord.ext import commands

    # Shared Constants
from commands.constants import *

    # IO
import asyncio
import io
import os
from pathlib import Path


    # Self Services
from services.chatbot_guard import ChatGuard
from services.chatbot_responder import ChatResponder
from services.class_context import ClassContext


    # Env files
from dotenv import load_dotenv
    # load env file in
load_dotenv()
allowed_forum_id = os.getenv("ALLOWED_FORUM_ID")


# HELPERS

# function to truncate message
    # so we don't get stuck with the bot unable to send a message
def truncate_for_discord(text: str, 
                         limit: int) -> tuple[str, bool]:
    """
    Truncate text safely to fit within Discord limits.
    Returns (possibly_truncated_text, was_truncated)
    """

    # check length of text (must be less than the limit)
    if len(text) <= limit:
        return text, False

    # leave extra space for truncation (out of caution)
    cutoff = limit - 200
    truncated = text[:cutoff]

    # avoid cutting mid-word
        # if there is a space, then allow split
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]

    # reframe and return
    truncated += "\n\n… _(response truncated)_"
    return truncated, True


# function to split split message so that it doesn't go
    # over the discord text limit
def split_for_discord(text: str, limit: int = 2000) -> list[str]:
    """
    Split a long message into chunks under Discord's 2000 char limit.
    Tries to avoid cutting mid-word.
    """
    chunks = []

    # while the current text is over our limit
    while len(text) > limit:
        # take slightly less than limit to be safe
        cutoff = limit - 50
        # and chunck it.
        chunk = text[:cutoff]

        # don't cut off the text while it is in the middle
            # of a word
        if " " in chunk:
            chunk = chunk.rsplit(" ", 1)[0]

        # add the new chunck to our list of messages chuncks
        chunks.append(chunk)
        # clean it up a bit (strip it)
        text = text[len(chunk):].lstrip()

    # else, for the remaining text that fits the limit
    if text:
        # toss that into our text chunck list
        chunks.append(text)

    # return all the text chuncks
    return chunks


# function to search for context file info
def find_context_file(base_path: Path, tag_name: str) -> list[Path]:
    """
    Return all valid context files for a tag.
    Tries concepts and projects folders, underscore and hyphen variants.
    """
    # variables
    valid_paths = []

    # file paths to look for
    candidates = [
        base_path / "concepts" / f"{tag_name}.txt",
        base_path / "concepts" / f"{tag_name.replace('_','-')}.txt",
        base_path / "projects" / f"{tag_name}.txt",
        base_path / "projects" / f"{tag_name.replace('_','-')}.txt"
    ]

    # check all possible paths
    for path in candidates:
        if path.exists():
            # if context exists there, add it to paths list
            valid_paths.append(path)

    # return the paths
    return valid_paths






# UI

# Class to gather needed context for message
class ContextSelect(discord.ui.Select):
    # initialize
    def __init__(self, contexts: dict[str, object]):
        
        # set options (allows use to pick context of conversation)
        options = [
            discord.SelectOption(label = name, value = name)
            # display all avaialble options
            for name in contexts.keys()
            ]

        # for selection (may only pick one option from the list)
        super().__init__(
            placeholder = "Choose the topic your question relates to…",
            min_values = 1,
            max_values = 1,
            options = options
        )

        # set context
        self.contexts = contexts

    # function for callback based on selected topic
    async def callback(self, interaction: discord.Interaction):
        # set context
        selected_name = self.values[0]
        context_path = self.contexts[selected_name]

        # set context path based on the specific user
        interaction.client.selected_contexts[interaction.user.id] = context_path


        # informs user that they have selected context and can 
        # now ask a question
        await interaction.response.send_message(
            f"**Selected topic:** {selected_name}\n\n"
            "Now ask your question using `/ask-question`.",
            ephemeral = True
            )


# class defining context view
class ContextView(discord.ui.View):
    # initalize
    def __init__(self, contexts: dict[str, object]):
        # set 60 second timeout
        super().__init__(timeout = 60)
        # then to own self add the context selected
        self.add_item(ContextSelect(contexts))


# Class for the chatbot to actually chat
class Chat(commands.Cog):
    # init (set bot and gaurd)
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guard = ChatGuard()

    # create a thread listener
    @commands.Cog.listener()
    # function for setup on thread creation
    async def on_thread_create(self, thread: discord.Thread):

        # only operate inside allowed forum channels
            # checks if forum, then if the specific forum is an allowed 
        if (not isinstance(thread.parent, discord.ForumChannel)) \
            or (thread.parent_id != allowed_forum_id):
            return None
        

        # if no tags selected
        if not thread.applied_tags:
            # ask user to select tags, and infor them if they don't that the thread will be treated like
            # a general forum channel, using general class context.
            # then, let the user know that the thread is being setup and the first response will come soon.
            await thread.send(
                "👋 Welcome!\n\n"
                "If you haven't already, please select a topic tag for this thread so I know which course material to reference, as we go forward. For now, I'll just treat this as a general questions thread."
                "I am currently setting up the thread and will be replying to your first message shortly!"
            )
        
        # otherwise, tags are selected
        else:
            # join the tags 
            tag_names = ", ".join(tag.name for tag in thread.applied_tags)

            # send an intro and inform the user of the current thread tags being user.
            await thread.send(
                f"👋 Welcome! I'll use the **{tag_names}** context to help answer questions.\n\n"
                "I am currently setting up the thread and context and will be replying to your first message shortly!"
            )


    @commands.Cog.listener()
    # function for when the user sends a messages (waits and listens for them to send a message)
    async def on_message(self, message: discord.Message):
        # ignore bots
        if message.author.bot:
            return

        # only respond inside threads 
        if not isinstance(message.channel, discord.Thread):
            return

        # set the thread
        thread = message.channel

        # only respond to forum threads
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        # ignore empty messages
        question = message.content.strip()
        if not question:
            return

        # ensure tag exists
        if not thread.applied_tags:
            await thread.send(
                "Please select a topic tag for this thread so I know what context to use."
                "If you don't wish to, I will continue useing general class context."
            )

        # GUARD CHECK 

            # if the question falls into restricted
        if self.guard.classify(question) == "restricted":
            # inform the user you can't help.
            await thread.send(
                "I can't help with solving homework or giving final answers.\n\n"
                "I *can* explain the underlying concepts.\n\n"
                "Try asking:\n"
                "• What does this concept mean?\n"
                "• Why is it used?\n"
                "• How does it work conceptually?"
            )
            return

        # determine context from threads
        base_path = Path(f"data/classes/{message.guild.id}")
        contexts = []

        # check all tags and load them in
        for tag in thread.applied_tags:
            tag_name = tag.name.lower().replace(" ", "_")
            files = find_context_file(base_path, tag_name)
            for file_path in files:
                print("Loaded context:", file_path)
                contexts.append(file_path)


        # if no tag-specific context found, fallback to general
        if not contexts:
            general_path = base_path / "general.txt"
            if general_path.exists():
                contexts.append(general_path)

        # if there is no context in the selected tags
        if not contexts:
            await thread.send("I couldn't find any course material for these tags.")
            return
        


        # Merge context files
        combined_context = ""

        for path in contexts:
            with open(path, "r", encoding="utf-8") as f:
                combined_context += f"\n\n--- Context from {path.stem} ---\n\n"
                combined_context += f.read()



        # Generate response to user from context
            # start typeing (so the user can see it is in progress)
        await thread.typing()
            # send status check
        await thread.send(
            "I am currently thinking about my answer, and then making sure it doesn't violate academic integrity! "
            "I will be responding soon!"
        )

            # get the responser
        responder = ChatResponder(
            message.guild.id,
            raw_context = combined_context
        )

        # response pass
        reply = await asyncio.to_thread(
            responder.generate,
            question,
            allow_long = True,
            enforce_integrity = True
        )


        # send response
        try:
            print("About to send message...")

            # split message
            chunks = split_for_discord(reply)

            # send each chunck
            for chunk in chunks:
                await thread.send(chunk)

            print("... message sent!")
            
        # don't send message (because of an error)
        except Exception as err:
            print("ERROR SENDING MESSAGE:")
            print(err)




# SETUP CALL

async def setup(bot: commands.Bot):
    await bot.add_cog(Chat(bot))
