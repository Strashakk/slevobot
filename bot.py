import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Inicializace bota a nastavení práv pro čtení zpráv
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} byl úspěšně spuštěn!')

@bot.command()
async def rizky(ctx):
    url = "https://www.kupi.cz/sleva/kureci-prsni-rizky/"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Najdi všechny řádky se slevami
        discount_rows = soup.find_all('div', class_='discount_row')

        if not discount_rows:
            await ctx.send("Nebyly nalezeny žádné akce na kuřecí prsní řízky.")
            return

        # Deduplikace podle ID slev (stejná sleva se může objevit ve více sekcích)
        seen_ids = set()
        vysledky = []

        for row in discount_rows:
            discount_id = row.get('id', '')
            if discount_id in seen_ids:
                continue
            seen_ids.add(discount_id)

            # Název obchodu
            shop_span = row.find('span', class_='discounts_shop_name')
            nazev = ''
            if shop_span:
                link = shop_span.find('a', class_='product_link_history')
                if link:
                    nazev = link.get('title', '').strip()

            # Cena
            price_tag = row.find('strong', class_='discount_price_value')
            cena = price_tag.get_text(strip=True).replace('\xa0', ' ') if price_tag else 'neuvedeno'

            # Sleva v procentech
            pct_tag = row.find('div', class_='discount_percentage')
            sleva = pct_tag.get_text(strip=True).replace('\xa0', ' ') if pct_tag else ''

            # Platnost
            validity_div = row.find('div', class_='discounts_validity')
            platnost = ''
            if validity_div:
                platnost = validity_div.get_text(strip=True).replace('\xa0', ' ')

            # Pokud je "dnes končí", nahraď dnešním datem
            if 'dnes končí' in platnost.lower():
                dnes = datetime.now().strftime('%d. %m. %Y')
                platnost = f"končí dnes ({dnes})"

            vysledky.append({
                'obchod': nazev,
                'cena': cena,
                'sleva': sleva,
                'platnost': platnost,
            })

        if not vysledky:
            await ctx.send("Nebyly nalezeny žádné akce na kuřecí prsní řízky.")
            return

        # Sestavení zprávy
        zprava = f"🐔 **Kuřecí prsní řízky – nalezeno {len(vysledky)} akci(í):**\n\n"
        for i, v in enumerate(vysledky, 1):
            zprava += (
                f"**{i}. {v['obchod']}**\n"
                f"   💰 Cena: **{v['cena']}** {v['sleva']}\n"
                f"   📅 Platnost: {v['platnost']}\n\n"
            )

        # Discord má limit 2000 znaků na zprávu
        if len(zprava) <= 2000:
            await ctx.send(zprava)
        else:
            # Rozděl na více zpráv
            casti = [zprava[i:i+1990] for i in range(0, len(zprava), 1990)]
            for cast in casti:
                await ctx.send(cast)

    except Exception as e:
        await ctx.send(f"Došlo k chybě při stahování dat: {e}")

# Spuštění bota