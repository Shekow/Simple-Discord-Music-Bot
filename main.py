import discord
import os
import functools
from discord import app_commands, Interaction
from discord.ext import commands
from datetime import datetime
from dotenv import load_dotenv
from music import MusicQueue

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

bot.queues = {}
# utility functions

def log_command(interaction: Interaction, name: str, **kwargs):
    print(f"[{datetime.now()}][{interaction.channel}] {interaction.user} used \"/{name}\" with {kwargs}")

# views

class PlayerUI(discord.ui.View):
    PREV_LABEL = "|◁"
    NEXT_LABEL = "▷|"
    PAUSE_LABEL = "▷"
    RESUME_LABEL = "||"
    NO_REPEAT_LABEL = "↻"
    REPEAT_ALL_LABEL = "↻."
    REPEAT_THIS_LABEL = "↻₁"
    NO_SHUFFLE_LABEL = "⇄"
    NORMAL_SHUFFLE_LABEL = "⇄."
    SMART_SHUFFLE_LABEL = "⇄✧"

    @staticmethod
    def interaction_respond(func):
        @functools.wraps(func)
        async def wrapper(self, interaction: Interaction, *args, **kwargs):
            await interaction.response.defer()
            await func(self, interaction, *args, **kwargs)
            await interaction.edit_original_response(content="", view=self)
        return wrapper

    def __init__(self, music_queue: MusicQueue) -> None:
        super().__init__()
        self.music_queue = music_queue
    
    @discord.ui.button(label=NO_SHUFFLE_LABEL, style=discord.ButtonStyle.grey)
    @interaction_respond
    async def shuffle(self, interaction: Interaction, button: discord.ui.Button):
        self.music_queue.shuffle_next()
        match self.music_queue.shuffle_mode:
            case self.music_queue.ShuffleMode.NO_SHUFFLE:
                button.label = self.NO_SHUFFLE_LABEL
            case self.music_queue.ShuffleMode.NORMAL_SHUFFLE:
                button.label = self.NORMAL_SHUFFLE_LABEL
            case self.music_queue.ShuffleMode.SMART_SHUFFLE:
                button.label = self.SMART_SHUFFLE_LABEL

    @discord.ui.button(label=PREV_LABEL, style=discord.ButtonStyle.grey)
    @interaction_respond
    async def prev(self, interaction: Interaction, button: discord.ui.Button):
        self.music_queue.play_prev()

    @discord.ui.button(label=RESUME_LABEL, style=discord.ButtonStyle.grey)
    @interaction_respond
    async def pause(self, interaction: Interaction, button: discord.ui.Button):
        if self.music_queue.is_playing:
            self.music_queue.pause()
            button.label = self.PAUSE_LABEL
        else:
            self.music_queue.resume()
            button.label = self.RESUME_LABEL
    
    @discord.ui.button(label=NEXT_LABEL, style=discord.ButtonStyle.grey)
    @interaction_respond
    async def next(self, interaction: Interaction, button: discord.ui.Button):
        self.music_queue.play_next()

    @discord.ui.button(label=NO_REPEAT_LABEL, style=discord.ButtonStyle.grey)
    @interaction_respond
    async def repeat(self, interaction: Interaction, button: discord.ui.Button):
        self.music_queue.repeat_next()
        match self.music_queue.repeat_mode:
            case self.music_queue.RepeatMode:
                button.label = self.NO_REPEAT_LABEL
            case self.music_queue.RepeatMode.REPEAT_THIS:
                button.label = self.REPEAT_THIS_LABEL
            case self.music_queue.RepeatMode.REPEAT_ALL:
                button.label = self.REPEAT_ALL_LABEL

# events

@bot.event
async def on_ready():
    print(f"{bot.user} says \"Let's vibe!\"")
    print("Syncing command(s)...")
    try:
        synced = await bot.tree.sync()
        bot.synced_commands = synced
        print(f"Synced {len(synced)} command(s) successfully")
        print(f"{bot.user.display_name} is listening...")
        await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))
    except Exception as e:
        print(e)

@bot.event
async def on_command_error(interaction: Interaction, error: commands.CommandError):
    error_message = "Something went wrong"
    try:
        await interaction.response.send_message(error_message)
    except Exception as e:
        print(e)

# commands

@bot.tree.command(name="play", description="Play a song")
@app_commands.describe(query="Your query")
async def play(interaction: Interaction, query: str):
    log_command(interaction, "play", query=query)
    try:
        view = None
        if interaction.guild.voice_client is None:
            if interaction.user.voice is None:
                await interaction.response.send_message(content="You're not connected to a voice channel")
                return
            await interaction.user.voice.channel.connect()
            bot.queues[interaction.guild.id] = MusicQueue(interaction.guild.voice_client)
            view = PlayerUI(music_queue=bot.queues[interaction.guild.id])
        await interaction.response.defer(thinking=True)
        response = bot.queues[interaction.guild.id].enqueue(query, is_url=False)
        await interaction.edit_original_response(content=f"Added `{response.title}` to the queue", view=view)
        if not bot.queues[interaction.guild.id].is_playing:
            bot.queues[interaction.guild.id].play_next()
    except Exception as e:
        print(e)    

@bot.tree.command(name="playlink", description="Play a song")
@app_commands.describe(link="Your link")
async def playlink(interaction: Interaction, link: str):
    log_command(interaction, "playlink", link=link)
    try:
        view = None
        if interaction.guild.voice_client is None:
            if interaction.user.voice is None:
                await interaction.response.send_message(content="You're not connected to a voice channel")
                return
            await interaction.user.voice.channel.connect()
            bot.queues[interaction.guild.id] = MusicQueue(interaction.guild.voice_client)
            view = PlayerUI(music_queue=bot.queues[interaction.guild.id])
        await interaction.response.defer(thinking=True)
        response = bot.queues[interaction.guild.id].enqueue(link, is_url=True)
        await interaction.edit_original_response(content=f"Added `{response.title}` to the queue", view=view)
        if not bot.queues[interaction.guild.id].is_playing:
            bot.queues[interaction.guild.id].play_next()
    except Exception as e:
        print(e)

@bot.tree.command(name="pause", description="Pause the player")
async def pause(interaction: Interaction):
    try:
        if interaction.guild.voice_client is None or not bot.queues[interaction.guild.id].is_playing:
            await interaction.response.send_message("The player is not connected")
            return
        bot.queues[interaction.guild.id].pause()
        await interaction.response.send_message("Player paused successfully")
    except Exception as e:
        print(e)

@bot.tree.command(name="resume", description="Resume the player")
async def resume(interaction: Interaction):
    try:
        if interaction.guild.voice_client is None or not bot.queues[interaction.guild.id].is_paused:
            await interaction.response.send_message("The player is not paused")
            return
        bot.queues[interaction.guild.id].resume()
        await interaction.response.send_message("Player resumed successfully")
    except Exception as e:
        print(e)

@bot.tree.command(name="repeat", description="Enable/Disable repeat")
@app_commands.describe(enable="On/Off")
async def repeat(interaction: Interaction, enable: bool):
    try:
        if interaction.guild.voice_client is None or not bot.queues[interaction.guild.id].is_playing:
            await interaction.response.send_message("The player is not connected")
            return
        bot.queues[interaction.guild.id].repeat(enable)
        await interaction.response.send_message(f"Repeat {"enabled" if enable else "disabled"} successfully")
    except Exception as e:
        print(e)

@bot.tree.command(name="stop", description="Stop the current song")
async def stop(interaction: Interaction):
    try:
        if interaction.guild.voice_client is None or not bot.queues[interaction.guild.id].is_playing:
            await interaction.response.send_message("The player is not connected")
            return
        bot.queues[interaction.guild.id].stop()
        await interaction.response.send_message("song stoped successfully")
    except Exception as e:
        print(e)

@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: Interaction):
    try:
        if interaction.guild.voice_client is None or not bot.queues[interaction.guild.id].is_playing:
            await interaction.response.send_message("The player is not connected")
            return
        bot.queues[interaction.guild.id].skip()
        await interaction.response.send_message("song skiped successfully")
    except Exception as e:
        print(e)

@bot.tree.command(name="queue", description="Display the current queue")
async def queue(interaction: Interaction):
    try:
        if interaction.guild.voice_client is None:
            await interaction.response.send_message("Player is not connected")
            return
        response = "## Current Queue\n"
        for index, item in enumerate(bot.queues[interaction.guild.id].queue):
            response += f"**{index + 1}**-`{item.title}`\n"
        embed = discord.Embed(description=response, color=0x000000, )
        embed.set_author(name=bot.user.display_name, icon_url=bot.user.avatar.url)
        await interaction.response.send_message(content="", embed=embed)
    except Exception as e:
        print(e)

@bot.tree.command(name="clear", description="Clear the current queue")
async def clear(interaction: Interaction):
    try:
        if interaction.guild.voice_client is None:
            await interaction.response.send_message("Player is not connected")
            return
        bot.queues[interaction.guild.id].clear()
        await interaction.response.send_message(content="Queue cleared successfully")
    except Exception as e:
        print(e)

@bot.tree.command(name="help", description="Shows a list of commands along with their description")
async def help(interaction: Interaction):
    response = "# Available Commands:\n"
    for command in bot.synced_commands:
        response += f"`{bot.command_prefix}{command.name}`"
        for option in command.options:
            response += f" `{option.name}`"
        response += f"\n\t\t**{command.description}**\n"

    embed = discord.Embed(description=response, color=0xcccccc)
    embed.set_author(name=bot.user.display_name, icon_url=bot.user.avatar.url)
    if bot.user.banner is not None:
        embed.set_thumbnail(url=bot.user.banner.url)
    try:
        await interaction.response.send_message(content="", embed=embed)
    except Exception as e:
        print(e)

def main():
    bot.run(token=DISCORD_TOKEN)

if __name__ == "__main__":
    main()
