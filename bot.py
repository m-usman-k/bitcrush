import discord
from discord.ext import tasks, commands
from discord import app_commands, TextChannel, Role, User
import json
import os
from spotify_scraper import get_all_tracks
import datetime
import sys
import asyncio

# --- CONFIGURATION & VALIDATION ---
CONFIG_FILE = 'config.json'
ANNOUNCED_TRACKS_FILE = 'announced_tracks.txt'

def load_config():
    """Loads and validates the configuration from config.json."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Please create it.")
        sys.exit(1)
        
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    # Basic validation
    if "YOUR_DISCORD_BOT_TOKEN" in config.get('DISCORD_BOT_TOKEN', ""):
        print("Error: Please set your DISCORD_BOT_TOKEN in config.json")
        sys.exit(1)
    if "YOUR_ANNOUNCEMENT_CHANNEL_ID" in str(config.get('ANNOUNCEMENT_CHANNEL_ID', "")):
        print("Error: Please set your ANNOUNCEMENT_CHANNEL_ID in config.json")
        sys.exit(1)
        
    return config

def _save_config_sync(data):
    """(Internal) Synchronously saves data to the config file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

async def save_config(data):
    """Asynchronously saves the configuration to prevent blocking the event loop."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _save_config_sync, data)

config = load_config()
TOKEN = config['DISCORD_BOT_TOKEN']
ARTIST_URL = config['SPOTIFY_ARTIST_URL']

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- HELPER FUNCTIONS ---
def get_announced_tracks():
    """Reads all announced track URLs from the file into a set."""
    if not os.path.exists(ANNOUNCED_TRACKS_FILE):
        return set()
    with open(ANNOUNCED_TRACKS_FILE, 'r') as f:
        return set(line.strip() for line in f)

def add_announced_track(track_url):
    """Appends a new announced track URL to the file."""
    with open(ANNOUNCED_TRACKS_FILE, 'a') as f:
        f.write(track_url + '\n')

# --- DISCORD BOT EVENTS ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    check_for_new_release.start()

# --- BACKGROUND TASK ---
@tasks.loop(seconds=30)
async def check_for_new_release():
    print("Checking for new Spotify release...")
    
    channel_id = config.get('ANNOUNCEMENT_CHANNEL_ID')
    if not channel_id:
        print("Announcement channel not set. Use /set-ann-channel")
        return

    channel = bot.get_channel(int(channel_id))
    if not channel:
        print(f"Error: Channel with ID {channel_id} not found.")
        return

    # Run the blocking scraper function in an executor to avoid freezing the bot
    loop = asyncio.get_running_loop()
    all_tracks = await loop.run_in_executor(None, get_all_tracks, ARTIST_URL)
    
    if not all_tracks:
        print("No tracks found or an error occurred during scraping.")
        return

    announced_tracks = get_announced_tracks()
    new_tracks_found = False
    
    for track_name, track_url in all_tracks:
        if track_url not in announced_tracks:
            new_tracks_found = True
            print(f"New release found: {track_name}")
            
            # --- Create Embed ---
            embed = discord.Embed(
                title=f"🎵 New Release by bitcrush!",
                color=discord.Color.blue()
            )
            embed.description = (
                f"**[{track_name}]({track_url})** is out now on Spotify!\n\n"
                f"💥 Stream it, share it, and turn it up loud.\n\n"
            )
            
            embed.add_field(
                name="🕒 Released",
                value=f"<t:{int(datetime.datetime.now().timestamp())}:f>",
                inline=True
            )
            embed.add_field(
                name="🎶 Listen Now",
                value=f"[Click Here]({track_url})",
                inline=True
            )

            embed.add_field(name="🔗 Follow bitcrush", value=f"[Follow bitcrush on Spotify]({ARTIST_URL})", inline=False)

            # --- Ping Role ---
            ping_content = ""
            role_id = config.get('PING_ROLE_ID')
            if role_id:
                ping_content = f"<@&{role_id}>"

            await channel.send(content=ping_content, embed=embed)
            add_announced_track(track_url)
    
    if not new_tracks_found:
        print("No new release found.")

@check_for_new_release.before_loop
async def before_check():
    await bot.wait_until_ready()

# --- SLASH COMMANDS ---
@bot.tree.command(name="say", description="Make the bot say something in an embed.")
@app_commands.describe(
    message="The message you want the bot to say.",
    dm="Send the message as a DM to yourself (default: False). Pinging is disabled in DMs.",
    ping_user="A specific user to ping with the message.",
    ping_everyone="Ping @everyone with the message. Cannot be used with ping_user."
)
@app_commands.checks.has_permissions(administrator=True)
async def say(interaction: discord.Interaction, message: str, dm: bool = False, ping_user: User = None, ping_everyone: bool = False):
    if dm and (ping_user or ping_everyone):
        return await interaction.response.send_message("You cannot use ping options when sending a DM.", ephemeral=True)

    if ping_user and ping_everyone:
        return await interaction.response.send_message("You can ping a user or @everyone, but not both.", ephemeral=True)

    ping_content = None
    if ping_everyone:
        ping_content = "@everyone"
    elif ping_user:
        ping_content = ping_user.mention

    embed = discord.Embed(
        description=message,
        color=discord.Color.green(),
        timestamp=datetime.datetime.now()
    )
    embed.set_author(name=f"A message from {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    
    if dm:
        try:
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("Message sent to your DMs!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I couldn't send you a DM. Please check your privacy settings.", ephemeral=True)
    else:
        await interaction.response.send_message(content=ping_content, embed=embed)

# Set Announcement Channel
@bot.tree.command(name="set-ann-channel", description="Sets the channel for release announcements.")
@app_commands.describe(channel="The channel to send announcements to.")
@app_commands.checks.has_permissions(administrator=True)
async def set_ann_channel(interaction: discord.Interaction, channel: TextChannel):
    embed = discord.Embed(
        description=f"✅ Announcement channel set to {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
    config['ANNOUNCEMENT_CHANNEL_ID'] = str(channel.id)
    await save_config(config)

# Set Ping Role
@bot.tree.command(name="set-ping-role", description="Sets the role to ping for new releases.")
@app_commands.describe(role="The role to ping.")
@app_commands.checks.has_permissions(administrator=True)
async def set_ping_role(interaction: discord.Interaction, role: Role):
    embed = discord.Embed(
        description=f"✅ Ping role has been set to {role.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
    config['PING_ROLE_ID'] = str(role.id)
    await save_config(config)

# --- ERROR HANDLING ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    error_message = "An unexpected error occurred. Please try again later."
    if isinstance(error, app_commands.MissingPermissions):
        error_message = "🚫 You don't have permission to use this command."
    elif isinstance(error, app_commands.CommandInvokeError):
        print(f"Command '{error.command.name}' raised an exception: {error.original}")
    else:
        print(f"Unhandled command error: {error}")
    
    try:
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)
    except discord.errors.NotFound:
        print(f"Could not respond to interaction for command '{interaction.command.name if interaction.command else 'unknown'}' because it was not found.")
    except Exception as e:
        print(f"An error occurred while trying to send an error message: {e}")

# --- RUN BOT ---
if __name__ == "__main__":
    bot.run(TOKEN) 