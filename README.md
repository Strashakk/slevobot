# Slevobot/Veverička

Discord bot v Pythonu pro trackování slev, dluhů přes API a lockin Discord command.

## 🧠Co umí

- Vyhledává akce na [kupi.cz](https://www.kupi.cz) pro vybrané produkty (Řízky, vajíčka, mleté, monstery..).
- Zobrazuje všechny dluhy v Flowernal API.
- Dočasný "lockin" na discordu - timeout a odstranění rolí.
- Výpis logů na Discord pomocí příkazu.

## 🌟Hvězdná historie

<a href="https://www.star-history.com/?repos=strashakk%2Fslevobot&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=strashakk/slevobot&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=strashakk/slevobot&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=strashakk/slevobot&type=date&legend=top-left" />
 </picture>
</a>

## 🤖Příkazy

### 🔥✍Textové příkazy

- `!rizky` - slevy na kuřecí prsní řízky, legacy verze commandu pro zachování "running-joku".
- `!sync` - znovunačte extensiony a synchronizuje slash commandy.
- `!unsync` - smaže registrované slash commandy.

### ⚔ Slash commandy
💸**Slevové commandy** - vypíší aktuální slevy na dané produkty
- `/rizky`
- `/monster`
- `/vejce` - pouze velikost M a L
- `/mlete_veprove`
- `/branik` - pouze 2L PET

### 📈📉Dluhy
**Vypisují Flowernalovy dluhy z API**
- `/dluhy seznam` - všechny aktivní dluhy
- `/dluhy celkem` - spočítá celkový dluh v Kč.
- `/dluhy graf` - zobrazí graf dluhů - generovaný přímo API, ne lokálně.
- `/dluhy zmena` - zobrazí změnu dluhů za zvolené období.

### 🔐Lockin
**"Zamkne dovnitř" uživatele na Discordu**
- `/lockin` - zamkne uživatele po daný čas.
- `/lockin_remove` - Admin příkaz pro předčasné zrušení lockinu.
- `/lockin_apply` - Admin příkaz pro zamknutí jiného uživatele.

### 📑Logy
**Výpis logů bota**
- `/logs` - vrátí posledních N řádků logu, admin-only.

## 📚 Požadavky

- Python 3.12.3 nebo novější kompatibilní verze.
- Discord bot token.
- Pro synchronizaci slash commandů volitelně `DISCORD_GUILD_ID`.
- Pro startup zprávu volitelně `HOME_CHANNEL_ID`.

## 📝 Konfigurace

Vytvoř soubor `.env` v rootu repa a doplň do něj alespoň token:

```env
DISCORD_TOKEN=TVUJ_TOKEN
HOME_CHANNEL_ID=123456789012345678
DISCORD_GUILD_ID=123456789012345678
```

`HOME_CHANNEL_ID` a `DISCORD_GUILD_ID` jsou volitelné. Pokud je `HOME_CHANNEL_ID` nastavený, bot po startu pošle zprávu do daného kanálu. `DISCORD_GUILD_ID` se používá pro rychlejší sync slash commandů, není však potřeba.

## 🐋Spuštění přes Docker (**__Doporučeno__**)

Nejjednodušší je použít dodaný `deploy.sh`, který stáhne aktuální stav z `origin/main`, vyčistí pracovní strom a znovu sestaví Docker image.

```bash
./deploy.sh
```

Alternativně lze použít `docker compose` přímo:

```bash
docker compose up -d --build
```

## Spuštění lokálně

Projekt používá `uv`.

```bash
uv sync
uv run python bot.py
```


## 📕Struktura repa

- `bot.py` - hlavní vstupní bod a konfigurace bota
- `cogs/akce.py` - výpis scraperu kupi.cz
- `cogs/dluhy.py` - příkazy pro dluhy
- `cogs/lockin.py` - lockin režim
- `cogs/logger.py` - výpis logů
- `cogs/sync.py` - sync a unsync slash commandů
- `lib/scraper.py` - scraper pro kupi.cz