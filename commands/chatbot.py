# Imports

    # Discord
import discord
from discord.ext import commands

    # Shared Constants
from commands.constants import *

    # IO
import asyncio
import os


    # Self Services
from services.ai.selector import get_embedding_engine, get_response_engine
from services.chatbot.guard import ChatGuard
from services.chatbot.responder import ChatResponder
from services.chatbot.settings import RuntimeSettings, load_settings
from services.rag.retriever import (
    pack_context,
    retrieve_class_context,
    retrieve_recent_thread_memory,
    retrieve_thread_memory,
)
from services.db import pool

    # Env files
from dotenv import load_dotenv
    # load env file in
load_dotenv()
allowed_forum_id = int(os.getenv("ALLOWED_FORUM_ID"))

    # debugging
import traceback

# Class to handle sending debug logs to a Discord thread when debug mode is enabled, allowing for real-time 
# monitoring of the bot's operations and easier troubleshooting during development and testing.
class DiscordDebugReporter:
    def __init__(self, thread: discord.Thread, enabled: bool):
        self.thread = thread
        self.enabled = enabled
        self.message: discord.Message | None = None
        self.lines: list[str] = []

    # function to log a message to the Discord thread, accumulating messages and editing a single message to update the 
    # log in real-time, while respecting the enabled flag to avoid unnecessary operations when debug mode is off.
    async def log(self, message: str):
        if not self.enabled:
            return

        self.lines.append(message)
        body = "\n".join(f"- {line}" for line in self.lines[-15:])
        content = f"**Debug mode**\n{body}"

        if self.message is None:
            self.message = await self.thread.send(content)
        else:
            await self.message.edit(content=content)

# function to summarize the current runtime settings into a string for logging and debugging purposes
def summarize_settings(settings: RuntimeSettings) -> str:
    return (
        f"thread_mode={settings.thread_context_mode}, "
        f"thread_k={settings.thread_context_k}, "
        f"class_k={settings.class_context_k}, "
        f"verbosity={settings.response_verbosity}, "
        f"max_context_chars={settings.max_context_chars}, "
        f"integrity={settings.enforce_academic_integrity}"
    )


# Class to handle the chatbot functionality, including listening for new threads and messages, 
# retrieving context, generating responses, and enforcing academic integrity guidelines.
class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.response_engine = get_response_engine()
        self.guard = ChatGuard(engine=self.response_engine)
        self.embedder = get_embedding_engine()

    @commands.Cog.listener()
    # function to listen for new threads in allowed forum channels and send a welcome message.
    # Tags are optional and simply make course retrieval more targeted.
    async def on_thread_create(self, thread: discord.Thread):
        if (not isinstance(thread.parent, discord.ForumChannel)) \
            or (thread.parent_id != allowed_forum_id):
            return None

        # if there are no tags, let the user know the bot will still work and just use broader course context.
        if not thread.applied_tags:
            await thread.send(
                "Welcome!\n\n"
                "Topic tags are optional. If you add one, I'll use it to narrow the course material I retrieve. "
                "If you leave tags off, I'll just use broader course context for this thread. "
                "I am currently setting up the thread and will reply to your first message shortly!"
            )
        # if there are tags, acknowledge them and say that they will be used for more targeted retrieval.
        else:
            tag_names = ", ".join(tag.name for tag in thread.applied_tags)
            await thread.send(
                f"Welcome! I'll use the **{tag_names}** tags to target the course context more precisely.\n\n"
                "I am currently setting up the thread and context and will reply to your first message shortly!"
            )

    @commands.Cog.listener()
    # function to listen for new messages in threads, retrieve relevant context, generate a response using the ChatResponder, and send the response back to the thread while enforcing academic integrity guidelines.
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # only respond to messages in threads within the allowed forum channel
        if not isinstance(message.channel, discord.Thread):
            return
        thread = message.channel

        # only respond to threads in the allowed forum channel
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        # check if the question is empty or just whitespace, and if so, ignore it
        question = message.content.strip()
        if not question:
            return

        print(f"[ChatBot] Received question: {question}")

        # load runtime settings and initialize debug reporter for this message
        settings = load_settings()
        debug_reporter = DiscordDebugReporter(thread, enabled=settings.discord_debug)
        await debug_reporter.log(
            "commands/chatbot.py::on_message started "
            f"with settings [{summarize_settings(settings)}]"
        )

        # ensure database records exist for this class, thread, and user before proceeding with context retrieval and response generation
        try:
            ensure_class_exists(str(message.guild.id))
            ensure_user_exists(str(message.author.id))
            ensure_user_exists("bot")
            ensure_thread_exists(str(thread.id), str(message.guild.id), thread.name)
            await debug_reporter.log("Database setup helpers completed successfully")

        # exception handling for database setup to catch and log any issues that arise when ensuring necessary 
        # records exist before storing messages or retrieving context
        except Exception as err:
            print("[ChatBot] DB setup failed:", err)
            await debug_reporter.log(f"Database setup failed: {err}")

        # enforce chat guard restrictions to prevent generating responses to questions that 
        # violate academic integrity guidelines, and log the outcome of the guard check
        if self.guard.classify(question) == "restricted":
            await thread.send(
                "I can't help with solving homework or giving final answers.\n\n"
                "I *can* explain the underlying concepts.\n\n"
                "Try asking:\n"
                "- What does this concept mean?\n"
                "- Why is it used?\n"
                "- How does it work conceptually?"
            )
            await debug_reporter.log("ChatGuard blocked the request as restricted")
            return

        # select tags from the thread to use for context retrieval, and log the selected tags or if no tags were found
        selected_tags = []
        if thread.applied_tags:
            selected_tags = [t.name.lower().replace(" ", "_") for t in thread.applied_tags]
        await debug_reporter.log(f"Resolved thread tags: {selected_tags or ['<none>']}")

        # try to retrieve class context and thread memory based on the selected tags and question, 
        # and log the success or failure of each retrieval step along with any exceptions that occur during the process.
        try:
            ctx = await asyncio.to_thread(
                retrieve_class_context,
                class_id = str(message.guild.id),
                selected_tags = selected_tags,
                question = question,
                k = settings.class_context_k
            )
            class_context = pack_context(ctx)
            await debug_reporter.log(
                "services/rag/retriever.py::retrieve_class_context "
                f"returned {len(ctx.class_chunks)} chunk(s)"
            )
        # exception handling for context retrieval to catch and log any issues that arise when 
        # retrieving class context or thread memory, which are critical steps before generating a response. 
        # This ensures that if there are problems with the retrieval process, they are logged for debugging 
        # and the bot can handle the failure gracefully without crashing.
        except Exception as err:
            print("[ChatBot] Failed to retrieve class context:", err)
            class_context = ""
            await debug_reporter.log(f"Class context retrieval failed: {err}")

        # try to retrieve thread memory based on the selected thread context mode (semantic or recent), 
        # and log the results or any exceptions that occur during retrieval.
        try:
            # if set to semantic retrieval
            if settings.thread_context_mode == "semantic":
                thread_mem = await asyncio.to_thread(
                    retrieve_thread_memory,
                    thread_id = str(thread.id),
                    question = question,
                    k = settings.thread_context_k
                )
                await debug_reporter.log(
                    "services/rag/retriever.py::retrieve_thread_memory "
                    f"returned {len(thread_mem)} semantic match(es)"
                )
            # else, if based on recency
            else:
                thread_mem = await asyncio.to_thread(
                    retrieve_recent_thread_memory,
                    thread_id= str(thread.id),
                    k = settings.thread_context_k
                )
                await debug_reporter.log(
                    "services/rag/retriever.py::retrieve_recent_thread_memory "
                    f"returned {len(thread_mem)} recent message(s)"
                )
            
            # join the retrieved thread memory into a single string to be used as part of the context for response generation
            thread_context = "\n\n".join(thread_mem)

        # note error
        except Exception as err:
            print("[ChatBot] Failed to retrieve thread memory:", err)
            thread_context = ""
            await debug_reporter.log(f"Thread context retrieval failed: {err}")

        # attempt to store the message into thread memory
        try:
            await store_thread_message(
                thread_id = str(thread.id),
                class_id = str(message.guild.id),
                user_id = str(message.author.id),
                content = question,
                embedder = self.embedder
            )
            await debug_reporter.log("store_thread_message saved the current user message")
        # if storeing fails, catch the error and log it
        except Exception as err:
            print("[ChatBot] Failed to store user message:", err)
            await debug_reporter.log(f"Storing user message failed: {err}")

        # saved the combined context of the retireved relevent class context and conversation context
        combined_context = f"""
        COURSE CONTEXT:
        {class_context}

        THREAD CONTEXT:
        {thread_context}
        """

        combined_context = combined_context[:settings.max_context_chars]
        # log the length of the combined context and a preview if debug mode is enabled, 
        # to help with debugging and ensuring that the context being sent to the response generator 
        # is within expected limits and contains relevant information.
        await debug_reporter.log(
            f"Combined context prepared with {len(combined_context)} characters"
        )

        if settings.discord_debug:
            preview = combined_context[:settings.debug_context_preview_chars]
            await debug_reporter.log(f"Context preview:\n```text\n{preview}\n```")

        # inform user that the bot is generating a response and will reply shortly
        await thread.typing()
        await thread.send(
            "I am currently thinking about my answer and making sure it follows academic integrity. "
            "I will respond shortly!"
        )

        # notice sent debug logger that the thinking notice was sent to the thread
        await debug_reporter.log("Thinking notice sent to the thread")

        print("\n========== DEBUG CONTEXT ==========")
        print("Question:", question)
        print("Context length:", len(combined_context))
        print("Thread context:", thread_context[:500])
        print("===================================\n")

        # initialize the ChatResponder with the combined context and generate a response to the user's question, 
        # while enforcing academic integrity guidelines based on the runtime settings. 
        # Log the generated response or any exceptions that occur during generation to help with debugging and 
        # ensuring that the response generation process is working as intended.
        responder = ChatResponder(
            message.guild.id,
            raw_context=combined_context,
            engine=self.response_engine,
        )


        # try to generate a response using the ChatResponder (and send it to the Discord thread), 
        # and catch any exceptions that occur during generation to log them for debugging.
        try:
            # generate reply and send it the the thread
            reply = await asyncio.to_thread(
                responder.generate,
                question,
                allow_long = True,
                enforce_integrity = settings.enforce_academic_integrity,
                verbosity = settings.response_verbosity
            )
            print(f"[ChatBot] Generated reply:\n{reply}")

            # debug report
            await debug_reporter.log(
                "services/chatbot/responder.py::ChatResponder.generate "
                f"returned {len(reply)} characters"
            )
        # note error if it occurs
        except Exception as err:
            print("[ChatBot] Responder failed with traceback:")
            traceback.print_exc()
            await thread.send("Sorry, something went wrong generating a response. Please inform the developers and ask them to check the bot logs.")
            await debug_reporter.log(f"Responder failed: {err}")
            return

        # if there is no reply recieved, inform the user and log it for debugging
        if not reply.strip():
            await thread.send("Hmm, I couldn't generate a response. Please try again.")
            await debug_reporter.log("Responder returned an empty reply")
            return

        # attempt to split the reply into chucks so that it can be sent within Discord's message limits, and send the chunks to the thread.
        try:
            chunks = split_for_discord(reply)
            for chunk in chunks:
                await thread.send(chunk)
            await debug_reporter.log(f"Sent {len(chunks)} reply chunk(s) to Discord")
        # if it fails, catch the error and log it for debugging
        except Exception as e:
            print("[ChatBot] Failed to send message:", e)
            await debug_reporter.log(f"Sending reply failed: {e}")
            return

        # try and store the bot's response in the thread memory, and log the success or failure of this operation for debugging purposes.
        try:
            await store_thread_message(
                thread_id = str(thread.id),
                class_id = str(message.guild.id),
                user_id = "bot",
                content = reply,
                embedder = self.embedder
            )
            await debug_reporter.log("store_thread_message saved the bot response")
        except Exception as err:
            print("[ChatBot] Failed to store bot message:", err)
            await debug_reporter.log(f"Storing bot response failed: {err}")

        # @commands.guild_only()
        # @app_commands.command(name="end-thread", description="End this conversation thread")
        # async def end_thread(self, interaction: discord.Interaction):
        #     thread = interaction.channel
        #
        #     if not isinstance(thread, discord.Thread):
        #         await interaction.response.send_message("This must be used inside a thread.", ephemeral=True)
        #         return
        #
        #     await interaction.response.send_message("Ending thread...")
        #
        #     delete_thread_memory(thread.id)
        #     await thread.delete()


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
    truncated += "\n\n... _(response truncated)_"
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

# function to store message in thread memory
async def store_thread_message(thread_id: str, class_id: str, user_id: str, content: str, embedder):
    # embed the message content to get vector representation
    vec = await asyncio.to_thread(embedder.embed, [content])
    vec = vec[0]

    # store the message, embedding, and metadata in the database
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO thread_memory (thread_id, class_id, mem_type, author_id, content, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (thread_id, class_id, "message_chunk", user_id, content, vec),
        )

    print(f"\n-----------\nStoring message: thread_id={thread_id}, user_id={user_id}, content={content[:50]}\n--------\n")


# function to delete thread memory (used when ending a thread)
def delete_thread_memory(thread_id: str):
    # delete all messages in the thread memory for a given thread ID
    with pool.connection() as conn:
        conn.execute(
            "DELETE FROM thread_memory WHERE thread_id = %s",
            (thread_id,)
        )

# function to ensure that a thread, class, and user exist in the database before storing messages or retrieving context
def ensure_thread_exists(thread_id: str, class_id: str, title: str):
    # ensure thread exists in the database (if not, create it)
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO threads (thread_id, class_id, title)
            VALUES (%s, %s, %s)
            ON CONFLICT (thread_id) DO NOTHING
            """,
            (thread_id, class_id, title),
        )

# function to ensure that a class exists in the database (if not, create it)
def ensure_class_exists(class_id: str):
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO classes (class_id)
            VALUES (%s)
            ON CONFLICT (class_id) DO NOTHING
            """,
            (class_id,),
        )

# function to ensure that a user exists in the database (if not, create it)
def ensure_user_exists(user_id: str):
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user_id,),
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Chat(bot))
