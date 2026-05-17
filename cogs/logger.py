from collections import deque
from io import BytesIO
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from bot import LOG_PATH


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Logger(bot))


class Logger(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="logs", description="👑Admin: pošle posledních n řádků záznamů")
    @app_commands.describe(lines="Kolik řádků záznamu vrátit")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def logs(self, interaction: discord.Interaction, lines: app_commands.Range[int, 1, 500] = 25) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        if not LOG_PATH.exists():
            await interaction.followup.send("Log file not found.", ephemeral=True)
            return

        with LOG_PATH.open("r", encoding="utf-8", errors="replace") as log_file:
            tail_lines = deque(log_file, maxlen=lines)

        content = "".join(tail_lines).rstrip()
        if not content:
            await interaction.followup.send("Log file is empty.", ephemeral=True)
            return

        header = f"Last {min(lines, len(tail_lines))} log line{'s' if len(tail_lines) != 1 else ''}:"
        payload = f"{header}\n```text\n{content}\n```"

        if len(payload) <= 2000:
            await interaction.followup.send(payload, ephemeral=True)
            return

        attachment = discord.File(
            BytesIO((content + "\n").encode("utf-8")),
            filename=f"last_{len(tail_lines)}_log_lines.txt",
        )
        await interaction.followup.send(
            content=header,
            file=attachment,
            ephemeral=True,
        )
