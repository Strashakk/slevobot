import requests
from bs4 import BeautifulSoup
from typing import TypeAlias, Literal
from datetime import datetime
import re

SCRAPED_PRODUCTS: TypeAlias = list[dict[str, str]]
LOCATIONS: TypeAlias = Literal["Brno"]


class Scraper:
    def __init__(self, location: LOCATIONS | None = None):
        location_ids = {"Brno": "9415260"}

        self.base_url = "https://www.kupi.cz/sleva/{}/"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.cookies = (
            {"user_locality": location_ids[location]}
            if location in location_ids
            else {}
        )

    def _scrape_discounts(self, name: str | bytes) -> SCRAPED_PRODUCTS:
        headers = {"User-Agent": self.user_agent}
        response = requests.get(self.base_url.format(
            name), headers=headers, cookies=self.cookies, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        discount_rows = soup.find_all("div", class_="discount_row")

        seen_ids = set()
        vysledky = []

        for row in discount_rows:
            discount_id = row.get("id", "")
            if discount_id and discount_id in seen_ids:
                continue
            if discount_id:
                seen_ids.add(discount_id)

            shop_span = row.find("span", class_="discounts_shop_name")
            nazev = ""
            if shop_span:
                link = shop_span.find("a", class_="product_link_history")
                if link:
                    nazev = link.get("title", "").strip()

            price_tag = row.find("strong", class_="discount_price_value")
            cena = (
                price_tag.get_text(strip=True).replace("\xa0", " ")
                if price_tag
                else "neuvedeno"
            )

            pct_tag = row.find("div", class_="discount_percentage")
            sleva = pct_tag.get_text(strip=True).replace(
                "\xa0", " ") if pct_tag else ""

            validity_div = row.find("div", class_="discounts_validity")
            platnost = ""
            if validity_div:
                platnost = validity_div.get_text(
                    strip=True).replace("\xa0", " ")

            if "dnes končí" in platnost.lower():
                ted = datetime.now()
                platnost = f"končí dnes {ted.day}. {ted.month}."

            # Skip vysledek if sleva already neexistuje
            date_matches = re.findall(
                r"(\d{1,2})\.\s*(\d{1,2})\.(?:\s*(\d{4}))?", platnost)
            if date_matches:
                # Use the last date in the string as the end date (covers ranges like "1. 5. – 7. 5.")
                day_str, month_str, year_str = date_matches[-1]
                day = int(day_str)
                month = int(month_str)
                today = datetime.now().date()
                year = int(year_str) if year_str else today.year
                try:
                    end_date = datetime(year, month, day).date()
                except ValueError:
                    continue
                # Year rollover: if the date appears expired and we're in Q4 while the
                # date is in Q1, it likely belongs to next year (e.g. "2. 1." in December)
                if not year_str and end_date < today and today.month >= 10 and month <= 3:
                    try:
                        end_date = datetime(year + 1, month, day).date()
                    except ValueError:
                        continue
                if end_date < today:
                    continue

            vysledky.append(
                {
                    "obchod": nazev,
                    "cena": cena,
                    "sleva": sleva,
                    "platnost": platnost,
                }
            )

        return vysledky
