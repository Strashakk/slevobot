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
            status_message = await ctx.send("Starting sync...")

            if guild:
                await status_message.edit(content=f"Starting sync in guild {guild_id}...")
                self.bot.tree.copy_global_to(guild=guild)

            await status_message.edit(content="Reloading extensions...")
            cmds = list(self.bot.extensions.keys())
            for index, cmd in enumerate(cmds, start=1):
                await status_message.edit(content=f"Reloading extensions... ({index}/{len(cmds)}) {cmd}")
                await self.bot.reload_extension(cmd)

            await status_message.edit(content="Syncing slash commands...")
            synced = await self.bot.tree.sync(guild=guild)
            synced_str = "".join(f"- {command.name}\n" for command in synced)
            destination = f"in guild {guild_id}" if guild_id else "globally"
            suffix = "s" if len(synced) != 1 else ""
            await status_message.edit(
                content=f"Successfully synced {len(synced)} command{suffix} {destination}.\n{synced_str}"
            )
        except (commands.ExtensionError, discord.Forbidden, discord.HTTPException, discord.NotFound, ValueError) as e:  # noqa: BLE001
            if "status_message" in locals():
                await status_message.edit(content=f"Failed to sync: {e}")
            else:
                await ctx.send(f"Failed to sync: {e}")

    @commands.command(name="unsync")
    @commands.has_permissions(administrator=True)
    async def unsync(self, ctx: commands.Context) -> None:
        try:
            guilds = [guild.id for guild in self.bot.guilds]
            status_message = await ctx.send("Starting unsync...")

            for index, guild_id in enumerate(guilds, start=1):
                guild = discord.Object(id=guild_id)
                await status_message.edit(content=f"Removing slash commands from guild {guild_id} ({index}/{len(guilds)})...")
                self.bot.tree.clear_commands(guild=guild, type=None)
                await self.bot.tree.sync(guild=guild)

            await status_message.edit(content="Removing global slash commands...")
            self.bot.tree.clear_commands(guild=None, type=None)
            await self.bot.tree.sync(guild=None)
            await status_message.edit(content="Removed all global and guild registered slash commands")
        except (discord.Forbidden, discord.HTTPException, discord.NotFound) as e:  # noqa: BLE001
            if "status_message" in locals():
                await status_message.edit(content=f"Failed to unsync: {e}")
            else:
                await ctx.send(f"Failed to unsync: {e}")
