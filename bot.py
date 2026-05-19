import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

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
        await self.load_extension('cogs.logger')


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


@bot.event
async def on_ready() -> None:
    logging.log(logging.INFO, f'Bot {bot.user} byl úspěšně spuštěn!')

LOG_PATH = configure_logging()
if __name__ == "__main__":
    # Spuštění bota
    token = os.getenv("DISCORD_TOKEN")
    if not token or not token.strip():
        print("ERROR: DISCORD_TOKEN není nastavený. Doplň ho do .env souboru.")
        raise SystemExit(1)

    bot.run(token, log_handler=None)