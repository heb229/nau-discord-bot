import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ---------- ENV ----------

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not found in environment variables!")

# ---------- INTENTS ----------


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.guild_messages = True


# ---------- BOT ----------

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ---------- EVENTS ----------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    for guild in bot.guilds:
        print(f"Connected to server: {guild.name} (ID: {guild.id})")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as err:
        print(f"Failed to sync commands: {err}")

# ---------- MAIN ----------

async def main():
    # Load command cogs
    await bot.load_extension("commands.verify")
    await bot.load_extension("commands.message")
    await bot.load_extension("commands.help")
    await bot.load_extension("commands.info")
    await bot.load_extension("commands.class_admin")
    await bot.load_extension("commands.chatbot")

    # Start bot
    await bot.start(TOKEN)

# ---------- RUN ----------

asyncio.run(main())
