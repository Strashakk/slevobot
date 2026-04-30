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
        await self.load_extension('cogs.rizky')
        await self.load_extension('cogs.socials')
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.clear_commands(guild=guild)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            self.tree.clear_commands(guild=None)
            await self.tree.sync()


bot = Slevobot(command_prefix=commands.when_mentioned_or('!'), intents=intents)


@bot.event
async def on_ready() -> None:
    print(f'Bot {bot.user} byl úspěšně spuštěn!')

# Spuštění bota
token = os.getenv("DISCORD_TOKEN")
if not token or not token.strip():
    print("ERROR: DISCORD_TOKEN není nastavený. Doplň ho do .env souboru.")
    raise SystemExit(1)

bot.run(token)
