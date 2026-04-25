from __future__ import annotations
from typing import Literal, TypedDict
import requests
import discord
from discord import app_commands
from discord.ext import commands

RANGE_TYPE = Literal["weekly", "monthly", "3months", "6months", "1year"]

class GraphResponse(TypedDict):
    range: Literal["weekly", "monthly", "3months", "6months", "1year"]
    image_url: str
    image_path: str
    points_used: int

API_PATH = "https://flowernal.dev/debt/api/v2/graphs/debt-total?range={}"

def fetch_graph(window: str = "monthly") -> GraphResponse:
    response = requests.get(f"{API_PATH.format(window)}", timeout=15)
    response.raise_for_status()
    return response.json()

class DluhyGraph(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="dluhy graf", description="📉Zobrazí graf dlhov (predvolene mesiac)")
    @app_commands.describe(time="⏱️Vyberte časové rozpätie pre graf")
    async def dluhygraf(self, interaction: discord.Interaction,
                        time: RANGE_TYPE = "monthly") -> None:
        await interaction.response.defer()

        try:
            graph = fetch_graph(time)
            
            image_url = graph.get("image_url")
            if not image_url:
                await interaction.followup.send("No image found in API response.", ephemeral=True)
                return

            embed = discord.Embed(title="Debt History", color=discord.Color.blue())
            embed.set_image(url=image_url)
            embed.set_footer(text=f"Range: {graph.get('range')}")

            await interaction.followup.send(embed=embed)

        except requests.RequestException as e:
            await interaction.followup.send(f"Failed to fetch graph: {e}", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DluhyGraph(bot))