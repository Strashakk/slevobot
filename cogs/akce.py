import requests
import discord
from discord import app_commands
from discord.ext import commands
from bs4 import BeautifulSoup
from datetime import datetime
import re


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Akce(bot))


class Akce(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def _build_message(title: str, emoji: str, vysledky: list[dict[str, str]]) -> str:
        zprava = f"{emoji} **{title} - nalezeno {len(vysledky)} akcí:**\n"
        for i, v in enumerate(vysledky, 1):
            zprava += (
                f"**{i}. {v['obchod']}**"
                f"   💰 Cena: **{v['cena']}** {v['sleva']}\n"
                f"   📅 Platnost: {v['platnost']}\n\n"
            )
        return zprava

    @staticmethod
    def _chunk_text(text: str, max_len: int =1990) -> list[str]:
        if text:
            return [text[i:i+max_len] for i in range(0, len(text), 1990)]
        else:
            return [""]

    async def _send_discounts(self, interaction: discord.Interaction, *, title: str, empty_text: str, error_text: str, name: str, emoji: str) -> None:
        meowssage = empty_text
        try:
            vysledky = self._scrape_discounts(name)
            if vysledky:
                meowssage = self._build_message(title, emoji, vysledky)

        except (requests.RequestException, ValueError, TypeError, AttributeError) as e:
            meowssage = f"{error_text}: {e}"

        chunks = self._chunk_text(meowssage)
        if chunks:
            await interaction.response.send_message(chunks[0])
            for cast in chunks[1:]:
                await interaction.followup.send(cast)

    async def _send_discounts_ctx(self, ctx: commands.Context, *, title: str, empty_text: str, error_text: str, name: str, emoji: str) -> None:
        try:
            vysledky = self._scrape_discounts(name)
            if not vysledky:
                await ctx.send(empty_text)
                return

            zprava = self._build_message(title, emoji, vysledky)
            if len(zprava) <= 2000:
                await ctx.send(zprava)
                return

            for cast in self._chunk_text(zprava):
                await ctx.send(cast)
        except (requests.RequestException, ValueError, TypeError, AttributeError) as e:
            await ctx.send(f"{error_text}: {e}")

    @commands.command(name="rizky")
    async def rizky_text(self, ctx: commands.Context) -> None:
        await self._send_discounts_ctx(
            ctx,
            title="Kuřecí prsní řízky",
            empty_text="Nebyly nalezeny žádné akce na kuřecí prsní řízky.",
            error_text="Došlo k chybě při stahování akcí na kuřecí prsní řízky",
            name="kureci-prsni-rizky",
            emoji="🐔",
        )

    @app_commands.command(name="rizky", description="🐔Najde slevy na kuřecí prsní řízky")
    async def rizky(self, interaction: discord.Interaction) -> None:
        await self._send_discounts(
            interaction,
            title="Kuřecí prsní řízky",
            empty_text="Nebyly nalezeny žádné akce na kuřecí prsní řízky.",
            error_text="Došlo k chybě při stahování akcí na kuřecí prsní řízky",
            name="kureci-prsni-rizky",
            emoji="🐔",
        )

    @app_commands.command(name="monster", description="⚡Najde slevy na energetický nápoj Monster, také známý jako monster nebo monstr")
    async def monster(self, interaction: discord.Interaction) -> None:
        await self._send_discounts(
            interaction,
            title="Monster",
            empty_text="Nebyly nalezeny žádné akce na Monster.",
            error_text="Došlo k chybě při stahování akcí na Monster",
            name="energeticky-napoj-monster-energy",
            emoji="⚡",
        )
