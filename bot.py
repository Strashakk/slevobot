import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


# Inicializace bota a nastavení práv pro čtení zpráv
intents = discord.Intents.default()
intents.message_content = True


class Slevobot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension('cogs.dluhy')
        await self.load_extension('cogs.rizky')
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
async def on_ready():
    print(f'Bot {bot.user} byl úspěšně spuštěn!')

# Spuštění bota
bot.run(os.getenv("DISCORD_TOKEN"))
