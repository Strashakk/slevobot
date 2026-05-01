from os import getenv
from discord.ext import commands
import discord


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sync(bot))


class Sync(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context) -> None:
        try:
            guild_id = getenv("DISCORD_GUILD_ID")
            guild = discord.Object(id=int(guild_id)) if guild_id else None
            if guild:
                self.bot.tree.copy_global_to(guild=guild)
            synced = await self.bot.tree.sync(guild=guild)
            synced_str = "".join([f"- {command.name}\n" for command in synced])
            await ctx.reply(f"Successfully synced {len(synced)} command{"s" if len(synced) != 1 else ""} {f"in guild {guild_id}" if guild_id else "globally"}.\n{synced_str}")
        except Exception as e:
            await ctx.reply(f"Failed to sync: {e}")

    @commands.command(name="unsync")
    @commands.has_permissions(administrator=True)
    async def unsync(self, ctx: commands.Context) -> None:
        try:
            print(f'We have logged in as {self.bot.user}')
            guilds = [guild.id for guild in self.bot.guilds]
            print(
                f'The {self.bot.user.name} bot is in {len(guilds)} Guilds.\nThe guilds IDs list: {guilds}')
            for guild_id in guilds:
                guild = discord.Object(id=guild_id)
                self.bot.tree.clear_commands(guild=guild, type=None)
                await self.bot.tree.sync(guild=guild)
                print(f'Deleted commands from {guild_id}!')
                continue
            self.bot.tree.clear_commands(guild=None, type=None)
            await self.bot.tree.sync(guild=None)
            print('Deleted global commands!')
            await ctx.reply("Removed all global and guild registered slash commands")
        except Exception as e:
            await ctx.reply(f"Failed to sync: {e}")
