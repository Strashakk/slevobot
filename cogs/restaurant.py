from datetime import datetime, timedelta
import logging
from typing import Literal
from zoneinfo import ZoneInfo

from babel.dates import get_day_names
import discord
from discord import app_commands
from discord.ext import commands
import requests

from lib.restaurant import WEEKDAYS, DayOfWeek, RestaurantScraper, WeeklyMenu

log = logging.getLogger("slevobot.cogs.restaurant")

RestaurantChoice = Literal["nepal"]

CZ_DAY_NAMES: dict[DayOfWeek, str] = {
    WEEKDAYS[i]: get_day_names("wide", locale="cs")[i].capitalize()
    for i in range(7)
}


def _format_price(price: float) -> str:
    if price.is_integer():
        return f"{int(price)} Kč"
    return f"{price:.2f} Kč"


def _build_menu_embed(
    weekly_menu: WeeklyMenu,
    day: DayOfWeek,
    restaurant_name: str,
    menu_url: str,
) -> discord.Embed:
    """Build a Discord embed for a specific day's menu."""
    day_cz = CZ_DAY_NAMES.get(day, day)
    now = datetime.now(ZoneInfo("Europe/Prague"))

    # Compute the date for the selected weekday relative to the current week
    day_index = WEEKDAYS.index(day)
    delta = day_index - now.weekday()
    target_date = now + timedelta(days=delta)

    embed = discord.Embed(
        title=f"Denní menu – {restaurant_name}",
        description=f"📅 **{day_cz} {target_date.strftime('%d. %m. %Y')}**",
        url=menu_url,
        color=discord.Color.orange(),
        timestamp=now,
    )

    today_menu = weekly_menu.get(day)
    if not today_menu:
        embed.add_field(
            name="❌",
            value=f"Pro {day_cz} není k dispozici žádné denní menu.",
            inline=False,
        )
        embed.set_footer(text=f"{restaurant_name} • Denní nabídka")
        return embed

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
    return embed


class DaySelectView(discord.ui.View):
    """View with a select menu to switch between available days."""

    def __init__(
        self,
        weekly_menu: WeeklyMenu,
        available_days: list[DayOfWeek],
        current_day: DayOfWeek,
        restaurant_name: str,
        menu_url: str,
    ) -> None:
        super().__init__(timeout=300)
        self.weekly_menu = weekly_menu
        self.restaurant_name = restaurant_name
        self.menu_url = menu_url

        options = [
            discord.SelectOption(
                label=CZ_DAY_NAMES.get(day, day),
                value=day,
                default=(day == current_day),
            )
            for day in available_days
        ]
        select: discord.ui.Select[DaySelectView] = discord.ui.Select(
            placeholder="Vyber den",
            options=options,
        )
        select.callback = self._on_day_select  # type: ignore[assignment]
        self._day_select = select
        self.add_item(select)

    async def _on_day_select(self, interaction: discord.Interaction) -> None:
        select = self._day_select
        selected_day: DayOfWeek = select.values[0]

        # Update default markers on the options
        for option in select.options:
            option.default = option.value == selected_day

        embed = _build_menu_embed(
            self.weekly_menu, selected_day, self.restaurant_name, self.menu_url,
        )
        await interaction.response.edit_message(embed=embed, view=self)


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

        # Only include days that actually have menu data
        available_days = [
            day for day in WEEKDAYS
            if day in weekly_menu
            and (weekly_menu[day].get("soup") or weekly_menu[day].get("items"))
        ]

        if not available_days:
            today_cz = CZ_DAY_NAMES.get(today, today)
            await interaction.followup.send(
                f"Pro dnešní den ({today_cz}) není k dispozici žádné denní menu z restaurace {restaurant_name}."
            )
            return

        # Default to today if available, otherwise the first available day
        selected_day = today if today in available_days else available_days[0]

        embed = _build_menu_embed(weekly_menu, selected_day, restaurant_name, menu_url)
        view = DaySelectView(
            weekly_menu, available_days, selected_day, restaurant_name, menu_url,
        )
        await interaction.followup.send(embed=embed, view=view)
