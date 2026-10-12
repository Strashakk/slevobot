import json
import logging
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands, tasks

URL = "https://www.fit.vut.cz/study/course/TIN/public/"
CHANNEL_ID = 1267475337923792898
STATE_FILE = Path(__file__).with_name("tinalert_state.json")

log = logging.getLogger("slevobot.cogs.tinalert")


def fetch_upozorneni(html: bytes | str | None = None) -> str:
    """Vrátí text obsahu <ul> po nadpisu 'Aktuální upozornění'.

    get_text() ignoruje HTML komentáře, takže změna jen v komentáři
    se nepočítá jako změna. Testy můžou předat `html` místo stažení.
    """
    if html is None:
        html = requests.get(URL, timeout=30).content
    soup = BeautifulSoup(html, "html.parser")
    h2 = next(
        h for h in soup.find_all("h2")
        if "aktuální upozornění" in h.get_text(strip=True).lower()
    )
    ul = h2.find_next("ul")
    if ul is None:
        raise AttributeError("ul za 'Aktuální upozornění' nenalezeno")
    return ul.get_text("\n", strip=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TinAlert(bot))


class TinAlert(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.check.start()

    @tasks.loop(time=time(9, 0, tzinfo=ZoneInfo("Europe/Prague")))
    async def check(self) -> None:
        await self.bot.wait_until_ready()
        try:
            current = fetch_upozorneni()
        except (requests.RequestException, StopIteration, AttributeError) as e:
            log.warning("Nepodařilo se stáhnout aktuální upozornění TIN: %s", e)
            return

        try:
            if STATE_FILE.exists():
                previous = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                if current != previous:
                    message = f"TIN: Aktuální upozornění se změnila:\n\n{current or '(prázdné)'}"
                    channel = self.bot.get_channel(CHANNEL_ID)
                    if isinstance(channel, discord.abc.Messageable):
                        for i in range(0, len(message), 2000):
                            await channel.send(message[i:i + 2000])

            STATE_FILE.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        except Exception:
            log.exception("TinAlert check selhal")
