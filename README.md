# Slevobot/Veverička

Discord bot v Pythonu pro trackování slev, dluhů přes API a lockin Discord command.

## 🧠Co umí

- Vyhledává akce na [kupi.cz](https://www.kupi.cz) pro vybrané produkty (Řízky, vajíčka, mleté, monstery..).
- Zobrazuje všechny dluhy v Flowernal API.
- Dočasný "lockin" na Discordu - timeout a odstranění rolí.
- Fetak - AI vyhodnocení, jestli uživatel nemluví o touze si dát drogy, a případný hodinový timeout.
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
- `/bezlepkovy_chlebik` - Pan Blanco chlebik 
- `/pepsi` - 2L, 2.25L a 2.5L PET
- `/kofola` - 2L, 2.25L a 2.5L PET

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
- `/lockin_list` - Zobrazí seznam zamčených lidí

### 📑Logy
**Výpis logů bota**
- `/logs` - vrátí posledních N řádků logu, admin-only.

### 📝Shrnutí chatu
**Shrnutí posledních zpráv v aktuálním kanálu**
- `/zhrnuti [pocet_zprav]` - shrne posledních X textových zpráv od uživatelů (bez botů).

### 🧪Fetak
**Vyhodnocení, jestli se uživatel nebaví o drogách**
- `/fetak [user]` - projede poslední hodinu zpráv uživatele a přes AI vyhodnotí, jestli se bavil o drogách. Pokud ano, dostane hodinový timeout.
  - `user` je **volitelný** – pokud se nezadá, kontroluje se defaultní uživatel (id `279344155149467648`).

### 🌐Socials
**Automaticky upravuje odkazy ze sociálních sítí**
- Přepisuje odkazy z Instagramu, X a TikToku na alternativní embed-friendly domény.
- U původní zprávy potlačí embed a pošle upravený odkaz jako odpověď.
- Funguje automaticky bez další konfigurace.

### Reakce
- při 5 📌 reakcích připne zprávu v kanálu.

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
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
# volitelné (výchozí je OpenAI endpoint):
# AI_SUMMARY_API_URL=https://api.openai.com/v1/chat/completions
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
- `cogs/pin.py` - připínání zpráv uživateli
- `cogs/zhrnuti.py` - shrnutí posledních zpráv v kanálu
- `cogs/fetak.py` - AI vyhodnocení tématu drog/fetu u uživatele + hodinový timeout
- `cogs/socials.py` - automatická úprava odkazů ze sociálních sítí
- `cogs/sync.py` - sync a unsync slash commandů
- `lib/scraper.py` - scraper pro kupi.cz
