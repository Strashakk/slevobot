import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


# Inicializace bota a nastavení práv pro čtení zpráv
intents = discord.Intents.default()
intents.message_content = True


class Slevobot(commands.Bot):
    async def setup_hook(self) -> None:
        await self.load_extension('cogs.dluhy')
        await self.load_extension('cogs.akce')
        await self.load_extension('cogs.sync')
        await self.load_extension('cogs.lockin')


bot = Slevobot(command_prefix=commands.when_mentioned_or('!'), intents=intents)
startup_message_sent = False


@bot.event
async def on_ready() -> None:
    global startup_message_sent
    logging.log(logging.INFO, f'Bot {bot.user} byl úspěšně spuštěn!')

    if startup_message_sent:
        return

    startup_message_sent = True

    channel_id = 1478443099679227930
    try:
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        await channel.send(f'Bot byl spuštěn!')
    except discord.Forbidden:
        logging.warning('Could not send message to channel %s.', channel_id)
    except discord.NotFound:
        logging.warning('Channel %s does not exist or is not accessible.', channel_id)
    except discord.HTTPException:
        logging.exception('Failed to send startup message to channel %s.', channel_id)

# Spuštění bota
token = os.getenv("DISCORD_TOKEN")
if not token or not token.strip():
    print("ERROR: DISCORD_TOKEN není nastavený. Doplň ho do .env souboru.")
    raise SystemExit(1)

bot.run(token)
