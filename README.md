# Bitcrush Discord Bot

This is a simple Discord bot that provides two main features:
1.  **Spotify Release Announcements**: Automatically checks a Spotify artist page and announces new releases in a specific channel.
2.  **Admin Say Command**: A slash command (`/say`) for administrators to make the bot send messages.

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- A Discord Bot Token
- A Spotify Artist Page URL
- The ID of the Discord channel where you want announcements

### 2. Configuration
1.  Open the `config.json` file.
2.  Replace the placeholder values with your actual information:
    - `"DISCORD_BOT_TOKEN"`: Your bot's unique token from the Discord Developer Portal.
    - `"SPOTIFY_ARTIST_URL"`: The full URL to the Spotify artist's main page (e.g., `https://open.spotify.com/artist/xxxxxxxxxxx`).
    - `"ANNOUNCEMENT_CHANNEL_ID"`: The ID of the channel where the bot should post new release announcements.

### 3. Installation
1.  Clone or download this repository.
2.  Open a terminal or command prompt in the project's root directory.
3.  Install the required Python packages by running:
    ```bash
    pip install -r requirements.txt
    ```

### 4. Running the Bot
Once you have configured the bot and installed the dependencies, you can start it by running:
```bash
python bot.py
```

## Bot Commands

### `/say`
- **Description**: Makes the bot send a custom message in an embed.
- **Usage**: `/say message: [your message] dm: [True/False] ping_user: [@user] ping_everyone: [True/False]`
- **Parameters**:
  - `message` (required): The text you want the bot to say.
  - `dm` (optional): If set to `True`, the bot will send the message as a Direct Message to you. Pinging is disabled for DMs.
  - `ping_user` (optional): A specific user to ping with the message.
  - `ping_everyone` (optional): Set to `True` to ping @everyone. Cannot be used with `ping_user`.
- **Permissions**: Administrator only.

### `/set-ann-channel`
- **Description**: Sets the channel where new release announcements will be posted.
- **Usage**: `/set-ann-channel channel: [#your-channel]`
- **Permissions**: Administrator only.

### `/set-ping-role`
- **Description**: Sets the role that will be pinged in new release announcements.
- **Usage**: `/set-ping-role role: [@your-role]`
- **Permissions**: Administrator only.

## How It Works

- The bot uses `selenium` to perform web scraping on the provided Spotify artist's "Singles" page. It runs this check periodically (default is every 30 seconds, this can be changed in `bot.py`).
- To avoid duplicate announcements, the bot saves the URL of every announced track in a file named `announced_tracks.txt`.
- When a new track is found (i.e., a track URL from Spotify is not in `announced_tracks.txt`), it posts an announcement in the configured channel and pings the configured role.
