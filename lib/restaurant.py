import re
from typing import Literal, TypeAlias, TypedDict

from bs4 import BeautifulSoup
from cachetools.func import ttl_cache
import requests

class MenuItem(TypedDict):
    name: str
    price: float


class MenuItems(TypedDict):
    soup: MenuItem | None
    items: list[MenuItem]


DayOfWeek: TypeAlias = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WeeklyMenu: TypeAlias = dict[DayOfWeek, MenuItems]

DAY_MAPPING: dict[str, DayOfWeek] = {
    "monday": "Monday",
    "pondělí": "Monday",
    "pondeli": "Monday",
    "tuesday": "Tuesday",
    "úterý": "Tuesday",
    "utery": "Tuesday",
    "wednesday": "Wednesday",
    "středa": "Wednesday",
    "streda": "Wednesday",
    "thursday": "Thursday",
    "čtvrtek": "Thursday",
    "ctvrtek": "Thursday",
    "friday": "Friday",
    "pátek": "Friday",
    "patek": "Friday",
    "saturday": "Saturday",
    "sobota": "Saturday",
    "sunday": "Sunday",
    "neděle": "Sunday",
    "nedele": "Sunday",
}

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class RestaurantScraper:
    @staticmethod
    @ttl_cache(ttl=3600)
    def nepal(url: str = "https://nepalbrno.cz/NepalBrno/poledni.php") -> WeeklyMenu:
        headers = {"User-Agent": user_agent}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        weekly_menu: WeeklyMenu = {}

        day_sections = soup.find_all("div", class_="day-section")
        for section in day_sections:
            title_elem = section.find(class_="day-title")
            if not title_elem:
                continue

            title_text = title_elem.get_text().strip().lower()
            day_name: DayOfWeek | None = None
            for key, day in DAY_MAPPING.items():
                if key in title_text:
                    day_name = day
                    break

            if not day_name:
                continue

            soup_item: MenuItem | None = None
            raw_items: list[tuple[int, MenuItem]] = []
            for item_elem in section.find_all("div", class_="menu-item"):
                name_elem = item_elem.find(["h3", "h4"])
                if not name_elem:
                    continue

                name = re.sub(r"\s+", " ", name_elem.get_text().replace("\xa0", " ")).strip()
                if not name:
                    continue

                price_elem = item_elem.find("span")
                price = 0.0
                if price_elem:
                    price_text = price_elem.get_text().replace("\xa0", " ").strip()
                    price_match = re.search(r"(\d+(?:[.,]\d+)?)", price_text)
                    if price_match:
                        price = float(price_match.group(1).replace(",", "."))

                if "polévka" in name.lower() or "soup" in name.lower():
                    clean_soup_name = re.sub(r"^polévka:\s*", "", name, flags=re.IGNORECASE).strip()
                    soup_item = {"name": clean_soup_name, "price": price}
                    continue

                number_match = re.match(r"^(\d+)[.)\s:-]+\s*(.*)$", name)
                if number_match:
                    order_num = int(number_match.group(1))
                    clean_name = number_match.group(2).strip()
                else:
                    order_num = 999
                    clean_name = name

                raw_items.append((order_num, {"name": clean_name, "price": price}))

            raw_items.sort(key=lambda x: x[0])
            weekly_menu[day_name] = {
                "soup": soup_item,
                "items": [item for _, item in raw_items],
            }

        return weekly_menu

    nepal_today = nepal
