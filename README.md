# SLEVOBOT

## O co jde?
**Slevobot** je Discord bot napsaný v **Pythonu**.

Aktuálně nejzajímavější funkcí bota je scrapování __kupi.cz__ a následné vypsání aktuálních akčních nabídek životně potřebných produktů, jako jsou kuřecí prsní řízky, známé mezi mými kamarády jako `!rizky`

## Spuštění
Je potřeba vytvořit `.env` soubor a do něj vložit svůj **Discord API token** a volitelně také **HOME_CHANNEL_ID** (ID Kanálu pro zasílání informací o stavu bota).
```
DISCORD_TOKEN=TVŮJTOKEN
HOME_CHANNEL_ID=123456789012345678
```
Následně přes vložený soubor `deploy.sh` dojde k dokerizaci a spuštění bota.
