import requests
import discord
from discord import app_commands
from discord.ext import commands
from typing import TypedDict, Literal
from babel.numbers import format_currency


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Dluhy(bot))


class Debt(TypedDict):
    """Structure of a debt record"""
    id: int
    person: str
    amount: float | int
    currency: str
    description: str
    direction: str
    settled: int
    created_at: str
    updated_at: str


class DebtResponse(TypedDict):
    debts: list[Debt]
    debt_totals_by_currency: dict[str, int]
    debt_total_eur: float
    conversion: dict[str, int]
    currency_format: str


class Seznam:
    DIRECTION = Literal["i_owe", "owed_to_me"]

    def __init__(self) -> None:
        self.response: DebtResponse | None = None
        self.debts: list[Debt] | None = None
        self.API_URL = "https://flowernal.dev/debt/api/v2/debts?settled=false"

    def fetch(self) -> None:
        response = requests.get(self.API_URL, timeout=15)
        response.raise_for_status()
        self.response = response.json()

    def filter_active(self) -> list[Debt]:
        if self.response is None:
            self.fetch()
        if self.debts is None:
            self.debts = self.response["debts"]
        self.debts = [d for d in self.debts if d["settled"] == 0]

    def filter_by_direction(self, direction: DIRECTION) -> list[Debt]:
        if self.response is None:
            self.fetch()
        if self.debts is None:
            self.debts = self.response["debts"]
        self.debts = [d for d in self.debts if d["direction"] == direction]

    def sum_by_currency(self) -> dict[str, float | int]:
        if self.response is None:
            self.fetch()
        if self.debts is None:
            self.debts = self.response["debts"]
        totals = {}
        for d in self.debts:
            cur = d["currency"]
            totals[cur] = totals.get(cur, 0) + d["amount"]
        return totals

    @staticmethod
    def format(amount: float, currency: str = "EUR") -> str:
        return format_currency(amount, currency=currency, locale="cs_CZ")

    def format_debt(self, debt: Debt) -> str:
        desc = f' ({debt["description"]})' if debt.get("description") else ""
        return f'{debt["person"]}: {self.format(debt.get('amount'), debt.get('currency'))} {desc}'

    async def send(self, interaction: discord.Interaction) -> None:
        try:
            self.filter_active()
            self.filter_by_direction("i_owe")

            zprava = f"### 👀💰💸 Flowernal dluhy \n**nalezeno {len(self.debts)} aktivních dluhů:**\n\n"
            for d in self.debts:
                zprava += f"🤑 {self.format_debt(d)}\n"

            zprava += "\n"
            zprava += "Celkový dluh:\n"
            total = self.sum_by_currency()
            for cur, total_amount in total.items():
                zprava += f"🔥✍ {cur}: {total_amount:.2f}\n"

            await interaction.response.send_message(zprava)
        except requests.RequestException as e:
            await interaction.followup.send(
                f"Failed to fetch debt: {e}",
                ephemeral=True
            )
        except TypeError as e:
            await interaction.followup.send(
                f"Received unexpected API response: {e}",
                ephemeral=True
            )


class Celkem(Seznam):
    async def send(self, interaction: discord.Interaction) -> None:
        try:
            self.filter_active()
            self.filter_by_direction("i_owe")
            total = self.sum_by_currency()
            zprava = "### 🧾💐 Flowernalův Celkový dluh:\n"
            total_debt = 0
            for cur, total_amount in total.items():
                if cur == "EUR":
                    total_amount *= 24.3
                elif cur == "ILS":
                    total_amount *= 6.8
                total_debt += total_amount

            zprava += f"🔥✍ Celkem: {self.format(total_debt, "CZK")} 💸💸\n"

            await interaction.response.send_message(zprava)
        except requests.RequestException as e:
            await interaction.followup.send(
                f"Failed to fetch debt: {e}",
                ephemeral=True
            )
        except TypeError as e:
            await interaction.followup.send(
                f"Received unexpected API response: {e}",
                ephemeral=True
            )


class GraphResponse(TypedDict):
    range: Literal["weekly", "monthly", "3months", "6months", "1year"]
    image_url: str
    image_path: str
    points_used: int


class Graf:
    RANGE_TYPE = Literal["weekly", "monthly", "3months", "6months", "1year"]

    def __init__(self) -> None:
        self.API_PATH = "https://flowernal.dev/debt/api/v2/graphs/debt-total?range={}"
        self.response: GraphResponse | None = None

    def fetch(self, window: RANGE_TYPE = "monthly") -> None:
        response = requests.get(f"{self.API_PATH.format(window)}", timeout=15)
        response.raise_for_status()
        self.response = response.json()

    async def send(self, interaction: discord.Interaction,
                   time: RANGE_TYPE = "monthly") -> None:
        await interaction.response.defer()

        try:
            self.fetch(time)

            image_url = self.response.get("image_url")
            if not image_url:
                await interaction.followup.send("No image found in API response.", ephemeral=True)
                return

            embed = discord.Embed(title="Debt History",
                                  color=discord.Color.blue())
            embed.set_image(url=image_url)
            embed.set_footer(text=f"Range: {self.response.get('range')}")

            await interaction.followup.send(embed=embed)

        except requests.RequestException as e:
            await interaction.followup.send(
                f"Failed to fetch graph: {e}",
                ephemeral=True
            )
        except TypeError as e:
            await interaction.followup.send(
                f"Received unexpected API response: {e}",
                ephemeral=True
            )


class DiffResponse(TypedDict):
    current: float
    previous: float
    change: float
    change_percent: float
    horizon: "HORIZON_TYPE"


class Diff(Seznam):
    HORIZON_TYPE = Literal["daily", "weekly", "monthly"]

    def __init__(self) -> None:
        self.API_PATH = "https://flowernal.dev/debt/api/v2/debt-diff?horizon={}"
        self.response: DiffResponse | None = None

    def fetch(self, horizon: HORIZON_TYPE = "daily") -> None:
        response = requests.get(f"{self.API_PATH.format(horizon)}", timeout=15)
        response.raise_for_status()
        self.response = response.json()

    def construct_diff_message(self, horizon: HORIZON_TYPE = "daily") -> str:
        if self.response is None:
            self.fetch(horizon)
        msg = "### 📈📉💸 změna ve Flowernalových dluzích"
        horizon = self.response["horizon"]
        match horizon:
            case "daily":
                msg += " za den\n"
            case "weekly":
                msg += " za týden\n"
            case "monthly":
                msg += " za měsíc\n"
        msg += f"⏪ Dluh původně: {self.format(self.response['previous'])}\n"
        msg += f"⚡ Dluh nyní: {self.format(self.response['current'])}\n"
        debt_delta = float(self.response["change"])
        msg += "Změna: "
        if int(debt_delta) == 0:
            msg += "beze změny"
            return msg
        elif debt_delta > 0:
            msg += f"📈 nárůst o {self.format(debt_delta)}\n"
        else:
            msg += f"📉 pokles o {self.format(abs(debt_delta))}\n"
        msg += "Změna (v procentech): "
        debt_delta_percent = float(self.response["change_percent"])
        if debt_delta_percent > 0:
            msg += f"📈 nárůst o {debt_delta_percent}%"
        else:
            msg += f"📉 pokles o {abs(debt_delta_percent)}%"
        return msg

    async def send(self, interaction: discord.Interaction, horizon: HORIZON_TYPE) -> None:
        try:
            reply_msg = self.construct_diff_message(horizon)
            await interaction.response.send_message(reply_msg)

        except requests.RequestException as e:
            await interaction.followup.send(
                f"Failed to fetch diff: {e}",
                ephemeral=True
            )
        except TypeError as e:
            await interaction.followup.send(
                f"Received unexpected API response: {e}",
                ephemeral=True
            )


class Dluhy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    dluhy_group = app_commands.Group(
        name="dluhy", description="Příkazy související s dluhy")

    @dluhy_group.command(name="seznam", description="💸Vypíše aktivní dluhy")
    async def dluhy(self, interaction: discord.Interaction) -> None:
        await Seznam().send(interaction)

    @dluhy_group.command(name="celkem", description="💰Spočítá celkový dluh v Kč")
    async def dluhycelkem(self, interaction: discord.Interaction) -> None:
        await Celkem().send(interaction)

    @dluhy_group.command(name="graf", description="📉 Zobrazí graf dluhů (výchozí je měsíc)")
    @app_commands.describe(time="⏱️ Vyberte časové období pro graf")
    async def dluhygraf(self, interaction: discord.Interaction,
                        time: Graf.RANGE_TYPE = "monthly") -> None:
        await Graf().send(interaction, time)

    @dluhy_group.command(name="zmena", description="📈📉 Zobrazí změnu výšky dluhů za dané období (výchozí je den)")
    @app_commands.describe(horizon="⏱️ Vyberte časové období pro graf")
    async def dluhyzmena(self, interaction: discord.Interaction,
                         horizon: Diff.HORIZON_TYPE = "daily") -> None:
        await Diff().send(interaction, horizon)
