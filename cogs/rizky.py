import requests
from discord.ext import commands
from bs4 import BeautifulSoup
from datetime import datetime

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

async def setup(bot):
    await bot.add_cog(Rizky(bot))


class Rizky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _scrape_discounts(self, url):
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=15)
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
            sleva = pct_tag.get_text(strip=True).replace("\xa0", " ") if pct_tag else ""

            validity_div = row.find("div", class_="discounts_validity")
            platnost = ""
            if validity_div:
                platnost = validity_div.get_text(strip=True).replace("\xa0", " ")

            if "dnes končí" in platnost.lower():
                dnes = datetime.now().strftime("%d. %m. %Y")
                platnost = f"končí dnes ({dnes})"

            vysledky.append(
                {
                    "obchod": nazev,
                    "cena": cena,
                    "sleva": sleva,
                    "platnost": platnost,
                }
            )

        return vysledky

    @staticmethod
    def _build_message(title, emoji, vysledky):
        zprava = f"{emoji} **{title} - nalezeno {len(vysledky)} akcí:**\n"
        for i, v in enumerate(vysledky, 1):
            zprava += (
                f"**{i}. {v['obchod']}**"
                f"   💰 Cena: **{v['cena']}** {v['sleva']}\n"
                f"   📅 Platnost: {v['platnost']}\n\n"
            )
        return zprava

    @staticmethod
    def _chunk_text(text, max_len=1990):
        return [text[i : i + max_len] for i in range(0, len(text), max_len)]

    async def _send_discounts(self, ctx, *, title, empty_text, error_text, url, emoji):
        try:
            vysledky = self._scrape_discounts(url)
            if not vysledky:
                await ctx.send(empty_text)
                return

            zprava = self._build_message(title, emoji, vysledky)
            if len(zprava) <= 2000:
                await ctx.send(zprava)
                return

            for cast in self._chunk_text(zprava):
                await ctx.send(cast)
        except Exception as e:
            await ctx.send(f"{error_text}: {e}")

    @commands.command(name="rizky")
    async def rizky(self, ctx):
        await self._send_discounts(
            ctx,
            title="Kuřecí prsní řízky",
            empty_text="Nebyly nalezeny žádné akce na kuřecí prsní řízky.",
            error_text="Došlo k chybě při stahování akcí na kuřecí prsní řízky",
            url="https://www.kupi.cz/sleva/kureci-prsni-rizky/",
            emoji="🐔",
        )

    @commands.command(name="monster", aliases=["monter", "mosnter", "energitak", ])
    async def monster(self, ctx):
        await self._send_discounts(
            ctx,
            title="Monster",
            empty_text="Nebyly nalezeny žádné akce na Monster.",
            error_text="Došlo k chybě při stahování akcí na Monster",
            url="https://www.kupi.cz/sleva/energeticky-napoj-monster-energy/",
            emoji="⚡",
        )