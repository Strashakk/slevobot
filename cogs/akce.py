import requests
import discord
from discord import app_commands
from discord.ext import commands
from lib.scraper import Scraper, ScrapedProducts
import re


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Akce(bot))


class Akce(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.scraper = Scraper("Brno")

    @staticmethod
    def _build_message(title: str, emoji: str, vysledky: ScrapedProducts) -> str:
        zprava = f"{emoji} **{title} - {"nalezeno" if len(vysledky) != 1 else "nalezena"} {len(vysledky)} {"akcí" if len(vysledky) != 1 else "akce"}:**\n"
        for i, v in enumerate(vysledky, 1):
            zprava += (
                f"**{i}. {v['nazev']}**"
                f"   💰 Cena: **{v['cena']}** {v['sleva']}\n"
                f"   📅 Platnost: {v['platnost']}\n\n"
            )
        return zprava

    @staticmethod
    def _chunk_text(text: str, max_len: int = 1990) -> list[str]:
        if text:
            return [text[i:i+max_len] for i in range(0, len(text), 1990)]
        else:
            return [""]

    async def _send_discounts(self, interaction: discord.Interaction, *, title: str, empty_text: str, error_text: str, url: str, emoji: str, filter_: str | None = None, whitelist: bool = True) -> None:
        meowssage = empty_text
        try:
            vysledky = self.scraper.scrape(url)
            if filter_:
                vysledky = list(
                    filter(lambda x: whitelist if re.search(filter_, x["nazev"]) is not None else not whitelist, vysledky))
            if vysledky:
                meowssage = self._build_message(title, emoji, vysledky)

        except (requests.RequestException, ValueError, TypeError, AttributeError) as e:
            meowssage = f"{error_text}: {e}"

        chunks = self._chunk_text(meowssage)
        if chunks:
            await interaction.response.send_message(chunks[0])
            for cast in chunks[1:]:
                await interaction.followup.send(cast)

    async def _send_discounts_ctx(self, ctx: commands.Context, *, title: str, empty_text: str, error_text: str, url: str, emoji: str, filter_: str | None = None, whitelist: bool = True) -> None:
        try:
            vysledky = self.scraper.scrape(url)
            if filter_:
                vysledky = list(
                    filter(lambda x: whitelist if re.search(filter_, x["nazev"]) is not None else not whitelist, vysledky))
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
            url="https://www.kupi.cz/sleva/kureci-prsni-rizky/",
            emoji="🐔",
        )

    @app_commands.command(name="rizky", description="🐔Najde slevy na kuřecí prsní řízky")
    async def rizky(self, interaction: discord.Interaction) -> None:
        await self._send_discounts(
            interaction,
            title="Kuřecí prsní řízky",
            empty_text="Nebyly nalezeny žádné akce na kuřecí prsní řízky.",
            error_text="Došlo k chybě při stahování akcí na kuřecí prsní řízky",
            url="https://www.kupi.cz/sleva/kureci-prsni-rizky/",
            emoji="🐔",
        )

    @app_commands.command(name="monster", description="⚡Najde slevy na energetický nápoj Monster, také známý jako monster nebo monstr")
    async def monster(self, interaction: discord.Interaction) -> None:
        await self._send_discounts(
            interaction,
            title="Monster",
            empty_text="Nebyly nalezeny žádné akce na Monster.",
            error_text="Došlo k chybě při stahování akcí na Monster",
            url="https://www.kupi.cz/sleva/energeticky-napoj-monster-energy/",
            emoji="⚡",
        )

    @app_commands.command(name="vejce", description="🥚Najde slevy na vejce v velikosti M/L")
    async def vejce(self, interaction: discord.Interaction) -> None:
        await self._send_discounts(
            interaction,
            title="Vejce",
            empty_text="Nebyly nalezeny žádné akce na Vejce",
            error_text="Došlo k chybě při stahování akcí na Vejce",
            url="https://www.kupi.cz/slevy/vejce-a-drozdi/",
            emoji="🥚",
            filter_=r"Vejce.*\b(?:M|L)\b"
        )

    @app_commands.command(name="mlete_veprove", description="🐖Najde slevy na mleté vepřové")
    async def mlete_veprove(self, interaction: discord.Interaction) -> None:
        await self._send_discounts(
            interaction,
            title="Mleté vepřové",
            empty_text="Nebyly nalezeny žádné akce na Mleté vepřové",
            error_text="Došlo k chybě při stahování akcí na Mleté vepřové",
            url="https://www.kupi.cz/sleva/maso-mlete-veprove/",
            emoji="🐖"
        )
