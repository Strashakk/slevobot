import json
import logging
import re
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

URL = "https://www.ikea.com/cz/cs/cat/kolekce-alptall-700810/"
# Set this to the Discord channel ID for IKEA notifications.
CHANNEL_ID = 1353499570285580441
STATE_FILE = Path(__file__).resolve().parent.parent / \
    "data" / "ikea_state.json"
BASE_URL = "https://www.ikea.com"
PRODUCT_ID_PATTERN = re.compile(r"(?:-|/)(\d{6,10})(?:/|$|[?#])")

log = logging.getLogger("slevobot.cogs.ikea")


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    url: str


def _product_id(value: str) -> str | None:
    match = PRODUCT_ID_PATTERN.search(value)
    return match.group(1) if match else None


def _canonical_url(value: str) -> str:
    return urljoin(BASE_URL, value).split("?", 1)[0].rstrip("/") + "/"


def _iter_json(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_json(child)


def _products_from_json(value: Any) -> Iterator[Product]:
    for item in _iter_json(value):
        product_id = str(item.get("productId") or item.get("id") or "")
        name = item.get("productName") or item.get("name") or item.get("title")
        raw_url = item.get("productUrl") or item.get("url") or item.get("link")
        if not isinstance(raw_url, str) or "/p/" not in urlparse(raw_url).path:
            continue
        if not product_id and isinstance(raw_url, str):
            product_id = _product_id(raw_url) or ""
        if not product_id or not isinstance(name, str):
            continue
        if not product_id.isdigit():
            continue
        yield Product(product_id, " ".join(name.split()), _canonical_url(raw_url))


def _script_json(script: str) -> Iterator[Any]:
    try:
        yield json.loads(script)
    except json.JSONDecodeError:
        return


def parse_products(html: bytes | str) -> tuple[Product, ...]:
    soup = BeautifulSoup(html, "html.parser")
    products: dict[str, Product] = {}

    for script in soup.find_all("script"):
        for value in _script_json(script.string or script.get_text()):
            for product in _products_from_json(value):
                products.setdefault(product.product_id, product)

    for link in soup.select('a[href*="/p/"]'):
        href = link.get("href")
        if not isinstance(href, str):
            continue
        product_id = _product_id(href)
        name = link.get_text(" ", strip=True)
        if product_id and name:
            products.setdefault(product_id, Product(
                product_id, name, _canonical_url(href)))

    if not products:
        page_text = soup.get_text(" ", strip=True).lower()
        valid_collection_markers = (
            "seznam výsledků",
            "počet položek:",
            "výsledný počet výrobků:",
        )
        if (
            "kolekce alptall" not in page_text
            or not any(marker in page_text for marker in valid_collection_markers)
        ):
            raise ValueError(
                "Response does not look like the IKEA collection page")

    return tuple(sorted(products.values(), key=lambda product: product.product_id))


def fetch_products() -> tuple[Product, ...]:
    response = requests.get(URL, timeout=30)
    
    response.raise_for_status()
    return parse_products(response.content)


def new_products(previous: set[str], current: tuple[Product, ...]) -> tuple[Product, ...]:
    return tuple(product for product in current if product.product_id not in previous)


def _load_state() -> dict[str, dict[str, str]]:
    if not STATE_FILE.exists():
        return {}
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("IKEA state must be a JSON object")
    return data


def _save_state(products: tuple[Product, ...]) -> None:
    state = {
        product.product_id: {"name": product.name, "url": product.url}
        for product in products
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(
        state, ensure_ascii=False, indent=2), encoding="utf-8")


def split_message_chunks(message: str, size: int = 2000) -> Iterator[str]:
    for start in range(0, len(message), size):
        yield message[start:start + size]


def format_check_result(previous_count: int, current_count: int) -> str:
    return (
        f"IKEA ALPTALL kontrola\n"
        f"URL: {URL}\n"
        f"Starý počet produktů: {previous_count}\n"
        f"Nový počet produktů: {current_count}"
    )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ikea(bot))


class Ikea(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.check.start()

    async def cog_unload(self) -> None:
        self.check.cancel()

    @tasks.loop(time=time(9, 0, tzinfo=ZoneInfo("Europe/Prague")))
    async def check(self) -> None:
        try:
            current = fetch_products()
        except (requests.RequestException, ValueError, json.JSONDecodeError) as error:
            log.warning("Nepodařilo se načíst IKEA kolekci: %s", error)
            return

        state_exists = STATE_FILE.exists()
        try:
            previous_state = _load_state()
        except (OSError, ValueError, json.JSONDecodeError) as error:
            log.warning("Nepodařilo se načíst IKEA stav: %s", error)
            previous_state = {}

        state_changed = set(previous_state) != {
            product.product_id for product in current
        }
        if state_exists and state_changed:
            if not CHANNEL_ID:
                log.warning("CHANNEL_ID pro IKEA upozornění není nastavený.")
                return
            channel = self.bot.get_channel(CHANNEL_ID)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(CHANNEL_ID)
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    log.exception(
                        "Kanál %s pro IKEA upozornění není dostupný.", CHANNEL_ID)
                    return
            if not isinstance(channel, discord.abc.Messageable):
                log.warning("Kanál %s není messageable.", CHANNEL_ID)
                return
            message = format_check_result(len(previous_state), len(current))
            for chunk in split_message_chunks(message):
                await channel.send(chunk)

        try:
            _save_state(current)
        except OSError:
            log.exception("Nepodařilo se uložit IKEA stav.")

    @check.before_loop
    async def initialize_state(self) -> None:
        await self.bot.wait_until_ready()
        if STATE_FILE.exists():
            return

        try:
            current = fetch_products()
            _save_state(current)
            log.info("IKEA stav byl vytvořen při spuštění (%s produktů).", len(current))
        except (OSError, requests.RequestException, ValueError, json.JSONDecodeError) as error:
            log.warning("Při spuštění se nepodařilo vytvořit IKEA stav: %s", error)
