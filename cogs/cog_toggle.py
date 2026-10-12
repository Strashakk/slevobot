import discord
from discord import app_commands
from discord.ext import commands

from lib.decorators import dev_server_only
from lib.db import get_cog
from lib.db import list_disabled_cog_names
from lib.db import list_enabled_cog_names
from lib.db import list_cogs
from lib.db import set_cog_enabled


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CogToggle(bot))


class CogToggle(commands.Cog):
    bot: commands.Bot
    command_group = app_commands.Group(
        name="cog", description="Cog management commands")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CheckFailure):
            if interaction.response.is_done():
                await interaction.followup.send(
                    "This command is only available on the dev server.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "This command is only available on the dev server.",
                    ephemeral=True,
                )
            return

        raise error

    async def _enabled_cog_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        del interaction
        current_value = current.lower().strip()
        cogs = await list_enabled_cog_names()

        suggestions: set[str] = {
            cog_name
            for cog_name in cogs
            if cog_name.lower().startswith(current_value)
        }

        return [
            app_commands.Choice(name=value, value=value)
            for value in sorted(suggestions)[:25]
        ]

    async def _disabled_cog_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        del interaction
        current_value = current.lower().strip()
        cogs = await list_disabled_cog_names()

        suggestions: set[str] = {
            cog_name
            for cog_name in cogs
            if cog_name.lower().startswith(current_value)
        }

        return [
            app_commands.Choice(name=value, value=value)
            for value in sorted(suggestions)[:25]
        ]

    @dev_server_only
    @command_group.command(name="disable", description="👑Disables a cog")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(cog=_enabled_cog_autocomplete)
    async def disable(self, interaction: discord.Interaction, cog: str) -> None:
        await interaction.response.defer()

        await self._set_cog_state(interaction, cog, False)

    @dev_server_only
    @command_group.command(name="enable", description="👑Enables a cog")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(cog=_disabled_cog_autocomplete)
    async def enable(self, interaction: discord.Interaction, cog: str) -> None:
        await interaction.response.defer()

        await self._set_cog_state(interaction, cog, True)

    @dev_server_only
    @command_group.command(name="list", description="👑Shows all tracked cogs and their state")
    @app_commands.default_permissions(administrator=True)
    async def list_cogs_command(self, interaction: discord.Interaction) -> None:
        cogs = await list_cogs()

        if not cogs:
            await interaction.response.send_message("No cogs are tracked yet.")
            return

        lines = [
            f"{'✅' if cog.enabled else '⛔'} {cog.name} — {'enabled' if cog.enabled else 'disabled'}"
            for cog in cogs
        ]

        await interaction.response.send_message("\n".join(lines))

    async def _set_cog_state(
        self,
        interaction: discord.Interaction,
        cog: str,
        enabled: bool,
    ) -> None:
        stored_cog = await get_cog(cog)
        loaded_cog = self.bot.get_cog(cog)

        if stored_cog is None:
            if loaded_cog is None:
                await interaction.followup.send(f"Unknown cog: {cog}")
                return

            stored_cog = await set_cog_enabled(cog, enabled, loaded_cog.__module__)

        was_enabled = stored_cog.enabled
        await set_cog_enabled(cog, enabled, stored_cog.module)
        module_name = stored_cog.module

        if enabled:
            if loaded_cog is None:
                await self.bot.load_extension(module_name)
                await interaction.followup.send(f"Enabled cog: {cog}")
            else:
                await interaction.followup.send(f"Cog already enabled: {cog}")
            return

        if loaded_cog is not None:
            await self.bot.unload_extension(module_name)

        if was_enabled:
            await interaction.followup.send(f"Disabled cog: {cog}")
        else:
            await interaction.followup.send(f"Cog already disabled: {cog}")
