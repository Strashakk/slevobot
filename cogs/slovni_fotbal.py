import asyncio
import logging
import re

import discord
from discord.ext import commands

log = logging.getLogger("slevobot.cogs.slovni_fotbal")

# ==============================================================================
# KONFIGURACE V HLAVIČCE SOUBORU
# ==============================================================================
CHANNEL_ID: int = 1559164009033236490  # ID Discord kanálu, ve kterém se hraje slovní fotbal

# "ch" se počítá jako jedno písmeno
DIGRAPHS = ("ch",)

# Najde souvislé běhy písmen (funguje i pro českou diakritiku)
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

HINT_DELETE_AFTER_SECONDS = 10
# Kolik posledních zpráv prohlédnout pro nalezení nejnovějšího slova
# (přeskočí se případné zprávy bota, příkazy nebo zprávy bez písmen)
LAST_MESSAGE_LOOKUP_LIMIT = 10


def first_letter(text: str) -> str | None:
    """Vrátí první písmeno textu ('ch' počítá jako jedno písmeno)."""
    match = WORD_RE.search(text)
    if match is None:
        return None
    word = match.group(0).lower()
    for digraph in DIGRAPHS:
        if word.startswith(digraph):
            return digraph
    return word[0]


def last_letter(text: str) -> str | None:
    """Vrátí poslední písmeno textu ('ch' počítá jako jedno písmeno)."""
    words = WORD_RE.findall(text)
    if not words:
        return None
    word = words[-1].lower()
    for digraph in DIGRAPHS:
        if word.endswith(digraph):
            return digraph
    return word[-1]


class SlovniFotbal(commands.Cog):
    """Slovní fotbal – další slovo musí začínat písmenem, kterým končí předchozí.

    Na sebe ale nesmí navazovat tentýž hráč a chybná slova se mažou.
    Stav se při startu cogu načte živě z historie kanálu (žádná perzistence).
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_word: str | None = None
        self.last_letter: str | None = None
        self.last_message_id: int | None = None
        self.last_author_id: int | None = None
        self.init_task: asyncio.Task[None] | None = None

    async def cog_load(self) -> None:
        self.init_task = asyncio.create_task(self._init_state())

    async def cog_unload(self) -> None:
        if self.init_task is not None:
            self.init_task.cancel()

    async def _init_state(self) -> None:
        await self.bot.wait_until_ready()
        await self._seed_from_history()

    async def _seed_from_history(self) -> None:
        """Načte stav řetězu živě z kanálu – vezme poslední platnou zprávu."""
        self.last_word = None
        self.last_letter = None
        self.last_message_id = None
        self.last_author_id = None

        if not CHANNEL_ID:
            log.info("CHANNEL_ID pro slovní fotbal není nastavený, slovní fotbal je neaktivní.")
            return

        channel = self.bot.get_channel(CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(CHANNEL_ID)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                log.warning("Nepodařilo se načíst kanál %s pro slovní fotbal: %s", CHANNEL_ID, e)
                return

        if not isinstance(channel, discord.abc.Messageable) or not isinstance(channel, discord.TextChannel):
            log.warning("Kanál %s není textový kanál.", CHANNEL_ID)
            return

        try:
            # Historie je od nejnovějších zpráv – bereme první (nejnovější) platnou
            async for message in channel.history(limit=LAST_MESSAGE_LOOKUP_LIMIT):
                if message.author.bot or not message.content:
                    continue
                if message.content.startswith("!"):
                    continue
                if first_letter(message.content) is None:
                    continue
                self._accept(message)
                break
        except (discord.Forbidden, discord.HTTPException):
            log.warning("Nepodařilo se načíst historii kanálu pro slovní fotbal.")
            return

        if self.last_word is not None:
            log.info("Řetěz slovního fotbalu načten z kanálu: '%s'.", self.last_word)
        else:
            log.info("Kanál neobsahuje žádné platné slovo, řetěz začíná od nuly.")

    def _accept(self, message: discord.Message) -> None:
        """Přijme zprávu jako nové platné slovo a aktualizuje stav řetězu."""
        words = WORD_RE.findall(message.content)
        self.last_word = words[-1]
        self.last_letter = last_letter(message.content)
        self.last_message_id = message.id
        self.last_author_id = message.author.id

    def _is_valid(self, message: discord.Message) -> bool:
        """Zkontroluje, zda zpráva navazuje na řetěz (písmeno i jiný hráč)."""
        if self.last_letter is None:
            return True
        if message.author.id == self.last_author_id:
            return False
        return first_letter(message.content) == self.last_letter

    # ==================================================================
    # LISTENER
    # ==================================================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not CHANNEL_ID or message.channel.id != CHANNEL_ID:
            return
        if message.author.bot:
            return
        if message.content.startswith("!"):
            return
        if first_letter(message.content) is None:
            # zpráva bez písmen (obrázek, emoji, čísla…) – ignorujeme
            return

        if not self._is_valid(message):
            await self._reject_message(message)
            return

        self._accept(message)

    async def _reject_message(self, message: discord.Message) -> None:
        """Smaže chybnou zprávu a dá uživateli krátký pokyn."""
        if message.author.id == self.last_author_id:
            hint_text = (
                f"⚽ {message.author.mention} na sebe nemůžeš navazovat, "
                f"počkej na někoho jiného!"
            )
        else:
            hint_text = (
                f"⚽ {message.author.mention} musíš začít slovem na **{self.last_letter}**! "
                f"(poslední slovo: **{self.last_word}**)"
            )

        try:
            await message.delete()
        except discord.Forbidden:
            log.warning("Chybí oprávnění mazat zprávy v kanálu %s.", message.channel.id)
            return
        except discord.NotFound:
            return
        except discord.HTTPException:
            log.exception("Nepodařilo se smazat chybnou zprávu v kanálu %s.", message.channel.id)
            return

        hint = await message.channel.send(hint_text)
        asyncio.create_task(self._delete_later(hint))

    @staticmethod
    async def _delete_later(message: discord.Message) -> None:
        await asyncio.sleep(HINT_DELETE_AFTER_SECONDS)
        try:
            await message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SlovniFotbal(bot))
