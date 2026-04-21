# SLEVOBOT

## O co jde?
**Slevobot** je Discord bot napsaný v **Pythonu** jako můj testovací projekt, sloužící k naučení Pythonu či funckí Gitu.

Aktuálně nejzajímavější funkcí bota je scrapování __kupi.cz__ a následné vypsání aktuálních akčních nabídek životně potřebných produktů, jako jsou kuřecí prsní řízky, známé mezi mými kamarády jako `!rizky`

## Spuštění
Je potřeba vytvořit `.env` soubor a do něj vložit svůj **Discord API token** a volitelně také **DISCORD_GUILD_ID** (ID serveru pro rychlé guild sync slash commandů).
```
DISCORD_TOKEN=TVŮJTOKEN
DISCORD_GUILD_ID=123456789012345678
```
Následně přes vložený soubor `deploy.sh` dojde k dokerizaci a spuštění bota.
