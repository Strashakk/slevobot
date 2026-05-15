import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging

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


@bot.event
async def on_ready() -> None:
    print(f'Bot {bot.user} byl úspěšně spuštěn!')

# basic logging so our cog logs are visible in container logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

# Spuštění bota
token = os.getenv("DISCORD_TOKEN")
if not token or not token.strip():
    print("ERROR: DISCORD_TOKEN není nastavený. Doplň ho do .env souboru.")
    raise SystemExit(1)

bot.run(token)
