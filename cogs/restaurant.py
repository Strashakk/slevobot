from datetime import datetime
import logging
from typing import Literal
from zoneinfo import ZoneInfo

from babel.dates import format_date
import discord
from discord import app_commands
from discord.ext import commands
import requests

from lib.restaurant import WEEKDAYS, DayOfWeek, RestaurantScraper

log = logging.getLogger("slevobot.cogs.restaurant")

RestaurantChoice = Literal["nepal"]


def _format_price(price: float) -> str:
    if price.is_integer():
        return f"{int(price)} Kč"
    return f"{price:.2f} Kč"


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Restaurant(bot))


class Restaurant(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="menu",
        description="Zobrazí dnešní denní menu vybrané restaurace",
    )
    @app_commands.describe(restaurant="Výběr restaurace")
    async def menu(
        self,
        interaction: discord.Interaction,
        restaurant: RestaurantChoice,
    ) -> None:
        await interaction.response.defer()

        now = datetime.now(ZoneInfo("Europe/Prague"))
        today: DayOfWeek = WEEKDAYS[now.weekday()]
        today_cz = format_date(now, "EEEE", locale="cs").capitalize()

        match restaurant:
            case "nepal":
                try:
                    weekly_menu = RestaurantScraper.nepal()
                except requests.RequestException as e:
                    log.exception("Chyba při stahování denního menu pro Nepal: %s", e)
                    await interaction.followup.send(
                        f"Došlo k chybě při stahování denního menu: {e}"
                    )
                    return
                restaurant_name = "Nepal Brno"
                menu_url = "https://nepalbrno.cz/NepalBrno/poledni.php"
            case _:
                await interaction.followup.send("Neznámá restaurace.")
                return

        today_menu = weekly_menu.get(today)
        if not today_menu or (not today_menu.get("soup") and not today_menu.get("items")):
            await interaction.followup.send(
                f"Pro dnešní den ({today_cz}) není k dispozici žádné denní menu z restaurace {restaurant_name}."
            )
            return

        embed = discord.Embed(
            title=f"Denní menu – {restaurant_name}",
            description=f"📅 **{today_cz} {now.strftime('%d. %m. %Y')}**",
            url=menu_url,
            color=discord.Color.orange(),
            timestamp=now,
        )

        soup = today_menu.get("soup")
        if soup:
            embed.add_field(
                name="🍲 Polévka",
                value=f"{soup['name']} – **{_format_price(soup['price'])}**",
                inline=False,
            )

        items = today_menu.get("items")
        if items:
            dishes = "\n".join(
                f"**{i}.** {item['name']} – **{_format_price(item['price'])}**"
                for i, item in enumerate(items, 1)
            )
            embed.add_field(
                name="🍛 Hlavní jídla",
                value=dishes,
                inline=False,
            )

        embed.set_footer(text=f"{restaurant_name} • Denní nabídka")
        await interaction.followup.send(embed=embed)
