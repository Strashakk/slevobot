import os
import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


# Inicializace bota a nastavení práv pro čtení zpráv
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    await bot.load_extension('cogs.dluhy')
    await bot.load_extension('cogs.rizky')
    print(f'Bot {bot.user} byl úspěšně spuštěn!')
  
# Spuštění bota
token = os.getenv("DISCORD_TOKEN")
if not token or not token.strip():
    print("ERROR: DISCORD_TOKEN není nastavený. Doplň ho do .env souboru.")
    raise SystemExit(1)

bot.run(token)