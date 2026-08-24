import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from lib.db import get_cog_by_module
from lib.db import sync_cogs_from_bot

load_dotenv()


# Inicializace bota a nastavení práv pro čtení zpráv
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True


class Slevobot(commands.Bot):
    startup_message_sent = False

    async def setup_hook(self) -> None:
        cogs_dir = Path(__file__).resolve().parent / "cogs"
        extension_names = sorted(
            f"cogs.{path.stem}"
            for path in cogs_dir.glob("*.py")
            if path.stem != "cog_toggle"
        )

        for extension_name in extension_names:
            stored_cog = await get_cog_by_module(extension_name)
            if stored_cog is None or stored_cog.enabled:
                await self.load_extension(extension_name)

        await self.load_extension('cogs.cog_toggle')
        await sync_cogs_from_bot(self, excluded_modules={"cogs.cog_toggle"})


def configure_logging() -> Path:
    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "slevobot.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    return log_path


bot = Slevobot(command_prefix=commands.when_mentioned_or('!'), intents=intents)
startup_message_sent = False


@bot.event
async def on_ready() -> None:
    logging.info("Bot %s byl úspěšně spuštěn!", bot.user)

    if bot.startup_message_sent:
        return

    bot.startup_message_sent = True

    channel_id = os.getenv("HOME_CHANNEL_ID")
    if not channel_id or not channel_id.strip():
        logging.warning(
            'HOME_CHANNEL_ID není nastavený. Nelze poslat zprávu o spuštění bota.')
    else:
        try:
            channel_id_int = int(channel_id.strip())
        except (TypeError, ValueError):
            logging.warning(
                'HOME_CHANNEL_ID má neplatnou hodnotu %r. Nelze poslat zprávu o spuštění bota.', channel_id)
        else:
            try:
                channel = bot.get_channel(channel_id_int) or await bot.fetch_channel(channel_id_int)
                if isinstance(channel, discord.abc.Messageable):
                    await channel.send('Bot byl spuštěn!')
                else:
                    logging.warning(
                        'Channel %s is not messageable (got %s). Startup message was not sent.',
                        channel_id_int,
                        type(channel).__name__,
                    )
            except discord.Forbidden:
                logging.warning(
                    'Could not send message to channel %s.', channel_id_int)
            except discord.NotFound:
                logging.warning(
                    'Channel %s does not exist or is not accessible.', channel_id_int)
            except discord.HTTPException:
                logging.exception(
                    'Failed to send startup message to channel %s.', channel_id_int)

LOG_PATH = configure_logging()
if __name__ == "__main__":
    # Spuštění bota
    token = os.getenv("DISCORD_TOKEN")
    if not token or not token.strip():
        print("ERROR: DISCORD_TOKEN není nastavený. Doplň ho do .env souboru.")
        raise SystemExit(1)

    bot.run(token, log_handler=None)
