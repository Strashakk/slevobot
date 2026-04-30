import requests
import discord
from discord import app_commands
from discord.ext import commands
from typing import TypedDict, Literal
from dataclasses import dataclass

# Structure of a debt record


class Debt(TypedDict):
    id: int
    person: str
    amount: float | int
    currency: str
    description: str
    direction: str
    settled: int
    created_at: str
    updated_at: str


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Dluhy(bot))

DEBT_API_URL = "https://flowernal.dev/debt/api/v2/debts?settled=false"

currencies = {
    "EUR": "€",
    "CZK": "Kč",
    "ILS": "₪",
}

RANGE_TYPE = Literal["weekly", "monthly", "3months", "6months", "1year"]

HORIZON_TYPE = Literal["daily", "weekly", "monthly"]

class GraphResponse(TypedDict):
    range: Literal["weekly", "monthly", "3months", "6months", "1year"]
    image_url: str
    image_path: str
    points_used: int

@dataclass
class DiffResponse(TypedDict):
    current: float
    previous: float
    change: float
    change_percent: float
    horizon: HORIZON_TYPE

class DebtResponse(TypedDict):
    debts: list[Debt]
    debt_totals_by_currency: dict[str,int]
    debt_total_eur: float
    conversion: dict[str,int]
    currency_format: str

GRAPH_API_PATH = "https://flowernal.dev/debt/api/v2/graphs/debt-total?range={}"

DIFF_API_PATH = "https://flowernal.dev/debt/api/v2/debt-diff?horizon={}"

def fetch_diff(horizon: str = "daily") -> DiffResponse:
    response = requests.get(f"{DIFF_API_PATH.format(horizon)}", timeout=15)
    response.raise_for_status()
    return response.json()

def construct_diff_message(diff_response: DiffResponse) -> str:
    msg = "### 📈📉💸 změna ve Flowernalových dluzích"
    horizon = diff_response["horizon"] 
    match horizon:
        case "daily":
            msg += " za den\n"
        case "weekly":
            msg += " za týden\n"
        case "monthly":
            msg += " za měsíc\n"
    msg += f"⏪ Dluh původně: {diff_response['previous']}{currencies['EUR']}\n"
    msg += f"⚡ Dluh nyní: {diff_response['current']}{currencies['EUR']}\n"
    debt_delta = float(diff_response["change"])
    msg += "Změna: "
    if int(debt_delta) == 0:
        msg += "beze změny"
        return msg
    elif debt_delta > 0:
        msg += f"📈 nárůst o {debt_delta}{currencies['EUR']}\n"
    else:
        msg += f"📉 pokles o {abs(debt_delta)}{currencies['EUR']}\n"
    msg += "Změna (v procentech): "
    debt_delta_percent = float(diff_response["change_percent"])
    if debt_delta_percent > 0:
        msg += f"📈 nárůst o {debt_delta_percent}%"
    else:
        msg += f"📉 pokles o {abs(debt_delta_percent)}%"  
    return msg

def fetch_graph(window: str = "monthly") -> GraphResponse:
    response = requests.get(f"{GRAPH_API_PATH.format(window)}", timeout=15)
    response.raise_for_status()
    return response.json()


def fetch_debts() -> DebtResponse:
    response = requests.get(DEBT_API_URL,timeout=15)
    response.raise_for_status()
    return response.json()


def filter_active(debts: DebtResponse) -> list[Debt]:
    return [d for d in debts["debts"] if d["settled"] == 0]


def filter_by_direction(debts: list[Debt], direction: str) -> list[Debt]:
    return [d for d in debts if d["direction"] == direction]


def sum_by_currency(debts: list[Debt]) -> dict[str, float | int]:
    totals = {}
    for d in debts:
        cur = d["currency"]
        totals[cur] = totals.get(cur, 0) + d["amount"]
    return totals


def format_debt(debt: Debt) -> str:
    symbol = currencies[debt["currency"]]
    desc = f' ({debt["description"]})' if debt.get("description") else ""
    return f'{debt["person"]}: {debt["amount"]:.2f} {symbol} {desc}'


class Dluhy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    dluhy_group = app_commands.Group(name="dluhy",description="Příkazy související s dluhy")

    @dluhy_group.command(name="seznam", description="💸Vypíše aktivní dluhy")
    async def dluhy(self, interaction: discord.Interaction) -> None:
        debts = fetch_debts()
        active = filter_active(debts)

        zprava = f"### 👀💰💸 Flowernal dluhy \n**nalezeno {len(active)} aktivních dluhů:**\n\n"
        for d in filter_by_direction(active, "i_owe"):
            zprava += f"🤑 {format_debt(d)}\n"

        zprava += "\n"
        zprava += "Celkový dluh:\n"
        total = sum_by_currency(active)
        for cur, total_amount in total.items():
            zprava += f"🔥✍ {cur}: {total_amount:.2f}\n"

        await interaction.response.send_message(zprava)

    @dluhy_group.command(name="celkem", description="💰Spočítá celkový dluh v Kč")
    async def dluhycelkem(self, interaction: discord.Interaction) -> None:
        debts = fetch_debts()
        active = filter_active(debts)
        total = sum_by_currency(active)
        zprava = "### 🧾💐 Flowernalův Celkový dluh:\n"
        total_debt = 0
        for cur, total_amount in total.items():
            if cur == "EUR":
                total_amount *= 24.3
            elif cur == "ILS":
                total_amount *= 6.8
            total_debt += total_amount

        zprava += f"🔥✍ Celkem: {total_debt:.2f} Kč 💸💸\n"

        await interaction.response.send_message(zprava)

    @dluhy_group.command(name="graf", description="📉 Zobrazí graf dluhů (výchozí je měsíc)")
    @app_commands.describe(time="⏱️ Vyberte časové období pro graf")
    async def dluhygraf(self, interaction: discord.Interaction,
                        time: RANGE_TYPE = "monthly") -> None:
        await interaction.response.defer()

        try:
            graph = fetch_graph(time)

            image_url = graph.get("image_url")
            if not image_url:
                await interaction.followup.send("No image found in API response.", ephemeral=True)
                return

            embed = discord.Embed(title="Debt History",
                                  color=discord.Color.blue())
            embed.set_image(url=image_url)
            embed.set_footer(text=f"Range: {graph.get('range')}")

            await interaction.followup.send(embed=embed)

        except requests.RequestException as e:
            await interaction.followup.send(f"Failed to fetch graph: {e}", ephemeral=True)
    @dluhy_group.command(name="zmena", description="📈📉 Zobrazí změnu výšky dluhů za dané období (výchozí je den)")
    @app_commands.describe(horizon="⏱️ Vyberte časové období pro graf")
    async def dluhyzmena(self, interaction: discord.Interaction,
                         horizon: HORIZON_TYPE = "daily") -> None:
        try:
            diff_response = DiffResponse(**fetch_diff(horizon))
            reply_msg = construct_diff_message(diff_response)
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
        except ValueError as e:
            await interaction.followup.send(
                f"There was an error when creating the response: {e}",
                ephemeral=True
            )

