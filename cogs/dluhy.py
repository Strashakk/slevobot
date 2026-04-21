import requests
import discord
from discord import app_commands
from discord.ext import commands


async def setup(bot):
    await bot.add_cog(Dluhy(bot))

API_URL = "https://flowernal.dev/debt/api/debts?settled=false"

currencies = {
    "EUR": "€",
    "CZK": "Kč",
    "ILS": "₪",
}


def fetch_debts():
    response = requests.get(API_URL)
    response.raise_for_status()
    return response.json()


def filter_active(debts):
    return [d for d in debts if d["settled"] == 0]


def filter_by_direction(debts, direction):
    return [d for d in debts if d["direction"] == direction]


def sum_by_currency(debts):
    totals = {}
    for d in debts:
        cur = d["currency"]
        totals[cur] = totals.get(cur, 0) + d["amount"]
    return totals


def format_debt(debt):
    symbol = currencies[debt["currency"]]
    desc = f' ({debt["description"]})' if debt.get("description") else ""
    return f'{debt["person"]}: {debt["amount"]:.2f} {symbol} {desc}'


class Dluhy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dluhy", description="Vypíše aktivní dluhy")
    async def dluhy(self, interaction: discord.Interaction):
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

    @app_commands.command(name="dluhycelkem", description="Spočítá celkový dluh v Kč")
    async def dluhycelkem(self, interaction: discord.Interaction):
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
