import asyncio
from collections import deque
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

# ==============================================================================
# KONFIGURACE NOTIFIKACÍ V HLAVIČCE SOUBORU
# ==============================================================================
CHANNEL_ID: int = 1267475337923792898  # Společný Discord kanál pro zasílání upozornění

PRAGUE_TZ = ZoneInfo("Europe/Prague")
log = logging.getLogger("slevobot.cogs.pradlo")

CZECH_DAYS = [
    "Pondělí",
    "Úterý",
    "Středa",
    "Čtvrtek",
    "Pátek",
    "Sobota",
    "Neděle",
]

DEFAULT_PICKUP_HOURS: list[tuple[int, int]] = [(7, 12), (13, 17)]

# ==============================================================================
# TERMÍNY VÝMĚNY PRÁDLA
# ==============================================================================
palackeho: list[datetime] = [
    # 09/2026
    datetime(2026, 9, 15),
    datetime(2026, 9, 16),
    datetime(2026, 9, 17),
    # 10/2026
    datetime(2026, 10, 6),
    datetime(2026, 10, 7),
    datetime(2026, 10, 8),
    datetime(2026, 10, 27),
    datetime(2026, 10, 29),  # 28. 10. je státní svátek
    # 11/2026
    datetime(2026, 11, 18),
    datetime(2026, 11, 19),
    # 12/2026
    datetime(2026, 12, 8),
    datetime(2026, 12, 9),
    datetime(2026, 12, 10),
    datetime(2026, 12, 28),
    datetime(2026, 12, 29),
    # 01/2027
    datetime(2027, 1, 4),
    datetime(2027, 1, 5),
    datetime(2027, 1, 19),
    datetime(2027, 1, 20),
    datetime(2027, 1, 21),
    # 02/2027
    datetime(2027, 2, 9),
    datetime(2027, 2, 10),
    datetime(2027, 2, 11),
    # 03/2027
    datetime(2027, 3, 2),
    datetime(2027, 3, 3),
    datetime(2027, 3, 4),
    datetime(2027, 3, 23),
    datetime(2027, 3, 24),
    datetime(2027, 3, 25),
    # 04/2027
    datetime(2027, 4, 13),
    datetime(2027, 4, 14),
    datetime(2027, 4, 15),
    # 05/2027
    datetime(2027, 5, 4),
    datetime(2027, 5, 5),
    datetime(2027, 5, 6),
    datetime(2027, 5, 25),
    datetime(2027, 5, 26),
    datetime(2027, 5, 27),
    # 06/2027
    datetime(2027, 6, 15),
    datetime(2027, 6, 16),
    datetime(2027, 6, 17),
]

# Registr kolejí (každá kolej má vlastní role_id a termíny)
DORMS: dict[str, dict[str, Any]] = {
    "palackeho": {
        "name": "Palackého vrch (PPV)",
        "dates": palackeho,
        "role_id": 1550201435264786472,  # Role pro PPV
        "hours": DEFAULT_PICKUP_HOURS,
    },
}


# ==============================================================================
# UNIVERZÁLNÍ VÝPOČETNÍ FUNKCE
# ==============================================================================
def format_day(target_dt: datetime, now_dt: datetime) -> str:
    """Vrátí lidsky čitelný název dne (např. Dnes, Zítra nebo Čtvrtek 17. 9. 2026)."""
    target_date = target_dt.date()
    now_date = now_dt.date()
    czech_day = CZECH_DAYS[target_dt.weekday()]

    if target_date == now_date:
        return f"Dnes ({czech_day})"
    if target_date == now_date + timedelta(days=1):
        return f"Zítra ({czech_day})"
    return f"{czech_day} {target_dt.strftime('%d. %m. %Y')}"


def get_slots(
    dates: list[datetime],
    hours: list[tuple[int, int]] = DEFAULT_PICKUP_HOURS,
    tz: ZoneInfo = PRAGUE_TZ,
) -> list[tuple[datetime, datetime]]:
    """Univerzální funkce pro vygenerování všech časových slotů (od, do) pro libovolné datumy a hodiny."""
    slots: list[tuple[datetime, datetime]] = []
    for d in sorted(dates):
        for start_h, end_h in hours:
            start_dt = datetime(d.year, d.month, d.day, start_h, 0, tzinfo=tz)
            end_dt = datetime(d.year, d.month, d.day, end_h, 0, tzinfo=tz)
            slots.append((start_dt, end_dt))
    return slots


@dataclass
class TimeslotBlock:
    dorm_key: str
    dates: list[datetime]
    start_time: datetime
    end_time: datetime
    slots: list[tuple[datetime, datetime]]

    @property
    def id(self) -> str:
        first_d = self.dates[0].strftime("%Y-%m-%d")
        last_d = self.dates[-1].strftime("%Y-%m-%d")
        return f"{self.dorm_key}:{first_d}_{last_d}"

    @property
    def has_holiday_gap(self) -> bool:
        for i in range(len(self.dates) - 1):
            if (self.dates[i + 1].date() - self.dates[i].date()).days > 1:
                return True
        return False


def get_timeslot_blocks(
    dates: list[datetime],
    dorm_key: str = "palackeho",
    hours: list[tuple[int, int]] = DEFAULT_PICKUP_HOURS,
    tz: ZoneInfo = PRAGUE_TZ,
    max_gap_days: int = 1,
) -> list[TimeslotBlock]:
    """Seskupí jednotlivé dny do souvislých bloků.

    Umožňuje mezeru o velikosti `max_gap_days` (ve výchozím stavu 1 den pro státní svátky).
    """
    if not dates:
        return []

    unique_dates = sorted({d.replace(hour=0, minute=0, second=0, microsecond=0) for d in dates})
    current_group: list[datetime] = [unique_dates[0]]
    blocks: list[TimeslotBlock] = []

    for d in unique_dates[1:]:
        prev_d = current_group[-1]
        diff_days = (d.date() - prev_d.date()).days
        # diff_days == 1: po sobě jdoucí dny
        # diff_days == 2: 1 den mezera (např. 27. a 29. října kvůli svátku 28. 10.)
        if diff_days <= max_gap_days + 1:
            current_group.append(d)
        else:
            block_slots = get_slots(current_group, hours=hours, tz=tz)
            blocks.append(
                TimeslotBlock(
                    dorm_key=dorm_key,
                    dates=current_group,
                    start_time=block_slots[0][0],
                    end_time=block_slots[-1][1],
                    slots=block_slots,
                )
            )
            current_group = [d]

    if current_group:
        block_slots = get_slots(current_group, hours=hours, tz=tz)
        blocks.append(
            TimeslotBlock(
                dorm_key=dorm_key,
                dates=current_group,
                start_time=block_slots[0][0],
                end_time=block_slots[-1][1],
                slots=block_slots,
            )
        )

    return blocks


def get_pickup_status(
    slots: list[tuple[datetime, datetime]],
    now: datetime | None = None,
    tz: ZoneInfo = PRAGUE_TZ,
) -> tuple[bool, tuple[datetime, datetime] | None, tuple[datetime, datetime] | None]:
    """Zkontroluje, zda výdej prádla právě probíhá a jaký je nejbližší termín."""
    if now is None:
        now = datetime.now(tz)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)

    current_slot: tuple[datetime, datetime] | None = None
    next_slot: tuple[datetime, datetime] | None = None

    for start, end in slots:
        if start <= now < end:
            current_slot = (start, end)
        elif start > now:
            next_slot = (start, end)
            break

    return (current_slot is not None, current_slot, next_slot)


def build_dorm_queue(
    dorm_key: str,
    dorm_info: dict[str, Any],
    now: datetime,
) -> deque[tuple[datetime, TimeslotBlock]]:
    """Vytvoří seřazenou frontu nadcházejících notifikací pro konkrétní kolej (den před začátkem v poledne)."""
    events: list[tuple[datetime, TimeslotBlock]] = []

    blocks = get_timeslot_blocks(
        dates=dorm_info["dates"],
        dorm_key=dorm_key,
        hours=dorm_info.get("hours", DEFAULT_PICKUP_HOURS),
        tz=PRAGUE_TZ,
        max_gap_days=1,
    )
    for block in blocks:
        first_date = block.dates[0].date()
        day_before = first_date - timedelta(days=1)
        notify_dt = datetime(
            day_before.year,
            day_before.month,
            day_before.day,
            12,
            0,
            0,
            tzinfo=PRAGUE_TZ,
        )
        if notify_dt > now:
            events.append((notify_dt, block))

    events.sort(key=lambda x: x[0])
    return deque(events)


# ==============================================================================
# GENEROVÁNÍ EMBEDŮ
# ==============================================================================
def create_pradlo_embed(
    dorm_key: str = "palackeho",
    now: datetime | None = None,
    tz: ZoneInfo = PRAGUE_TZ,
) -> discord.Embed:
    dorm_info = DORMS.get(dorm_key, DORMS["palackeho"])
    dorm_name = dorm_info["name"]
    slots = get_slots(dorm_info["dates"], hours=dorm_info.get("hours", DEFAULT_PICKUP_HOURS), tz=tz)

    if now is None:
        effective_now = datetime.now(tz)
    elif now.tzinfo is None:
        effective_now = now.replace(tzinfo=tz)
    else:
        effective_now = now.astimezone(tz)

    is_available, current_slot, next_slot = get_pickup_status(slots=slots, now=effective_now, tz=tz)

    if is_available and current_slot:
        _, cur_end = current_slot
        embed = discord.Embed(
            title=f"🧺 Výdej ložního prádla – {dorm_name}",
            color=discord.Color.green(),
            description=(
                f"🟢 **Výdej prádla je právě dostupný!**\n"
                f"Můžeš si jít vyměnit prádlo dnes do **{cur_end.strftime('%H:%M')}** "
                f"({discord.utils.format_dt(cur_end, style='R')})."
            ),
        )
        if next_slot:
            next_start, next_end = next_slot
            day_text = format_day(next_start, effective_now)
            embed.add_field(
                name="📅 Následující termín výdeje",
                value=(
                    f"**{day_text}**\n"
                    f"⏰ {next_start.strftime('%H:%M')} – {next_end.strftime('%H:%M')} "
                    f"({discord.utils.format_dt(next_start, style='R')})"
                ),
                inline=False,
            )
    else:
        embed = discord.Embed(
            title=f"🧺 Výdej ložního prádla – {dorm_name}",
            color=discord.Color.orange(),
        )
        if next_slot:
            next_start, next_end = next_slot
            day_text = format_day(next_start, effective_now)
            embed.description = "🔴 **Výdej prádla momentálně neprobíhá.**"
            embed.add_field(
                name="📅 Nejbližší termín výdeje",
                value=(
                    f"**{day_text}**\n"
                    f"⏰ {next_start.strftime('%H:%M')} – {next_end.strftime('%H:%M')} "
                    f"({discord.utils.format_dt(next_start, style='R')})"
                ),
                inline=False,
            )
        else:
            embed.description = (
                "🔴 **Výdej prádla momentálně neprobíhá.**\n"
                "Žádné další vypsané termíny výdeje nebyly nalezeny."
            )

    embed.timestamp = effective_now
    return embed


def create_block_alert_embed(
    block: TimeslotBlock,
    dorm_name: str,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"🧺 Výměna ložního prádla – {dorm_name}",
        color=discord.Color.blue(),
        description="⚠️ **Zítra začíná další blok výměny ložního prádla!**",
    )

    days_lines = [
        f"• **{CZECH_DAYS[d.weekday()]} {d.strftime('%d. %m. %Y')}**"
        for d in block.dates
    ]
    days_text = "\n".join(days_lines)
    if block.has_holiday_gap:
        days_text += "\n*(Upozornění: Mezi termíny je 1 den pauza – státní svátek.)*"

    embed.add_field(name="📅 Dny výdeje v tomto bloku", value=days_text, inline=False)
    embed.add_field(
        name="⏰ Výdejní doba v jednotlivé dny",
        value="• Dopoledne: **07:00 – 12:00**\n• Odpoledne: **13:00 – 17:00**",
        inline=False,
    )
    embed.add_field(
        name="⏳ Otevření výdeje",
        value=f"{discord.utils.format_dt(block.start_time, style='F')} ({discord.utils.format_dt(block.start_time, style='R')})",
        inline=False,
    )
    embed.add_field(
        name="🏁 Konec tohoto bloku",
        value=f"{discord.utils.format_dt(block.end_time, style='F')} ({discord.utils.format_dt(block.end_time, style='R')})",
        inline=False,
    )
    embed.timestamp = datetime.now(PRAGUE_TZ)
    return embed


# ==============================================================================
# DISCORD COG
# ==============================================================================
class Pradlo(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.dorm_queues: dict[str, deque[tuple[datetime, TimeslotBlock]]] = {}
        self.dorm_tasks: dict[str, asyncio.Task[None]] = {}
        self.init_task: asyncio.Task[None] | None = None

    async def cog_load(self) -> None:
        """Při načtení cogu inicializuje fronty a naplánuje první notifikaci pro každou kolej."""
        self.init_task = asyncio.create_task(self._init_all_dorms())

    async def cog_unload(self) -> None:
        if self.init_task is not None:
            self.init_task.cancel()
        for task in self.dorm_tasks.values():
            task.cancel()
        self.dorm_tasks.clear()
        self.dorm_queues.clear()

    async def _init_all_dorms(self) -> None:
        await self.bot.wait_until_ready()
        now = datetime.now(PRAGUE_TZ)
        for dorm_key, dorm_info in DORMS.items():
            self.dorm_queues[dorm_key] = build_dorm_queue(dorm_key, dorm_info, now)
            self._load_next_dorm_notification(dorm_key)

    def _load_next_dorm_notification(self, dorm_key: str) -> None:
        """Načte další notifikaci z fronty dané koleje a spustí čekání."""
        queue = self.dorm_queues.get(dorm_key)
        if not queue:
            log.info("Fronta notifikací pro kolej '%s' je prázdná.", dorm_key)
            return

        next_item = queue.popleft()
        self.dorm_tasks[dorm_key] = asyncio.create_task(
            self._wait_and_fire_dorm_notification(dorm_key, next_item)
        )

    async def _wait_and_fire_dorm_notification(
        self, dorm_key: str, item: tuple[datetime, TimeslotBlock]
    ) -> None:
        """Čeká do poledne dne předem pro danou kolej, odešle notifikaci a poté načte další položku z fronty této koleje."""
        target_dt, block = item
        dorm_info = DORMS[dorm_key]
        dorm_name = dorm_info["name"]
        role_id = dorm_info.get("role_id", 0)

        delay = (target_dt - datetime.now(PRAGUE_TZ)).total_seconds()
        log.info(
            "Načtena notifikace pro kolej '%s' na %s (za %.1f hod.).",
            dorm_name,
            target_dt.strftime("%d. %m. %Y v %H:%M"),
            delay / 3600,
        )

        try:
            while True:
                remaining = (target_dt - datetime.now(PRAGUE_TZ)).total_seconds()
                if remaining <= 0:
                    break
                await asyncio.sleep(min(remaining, 86400))

            # Odpálení notifikace pro danou kolej
            await self._send_block_alert(block, dorm_name, role_id)

            # Odpálení notifikace načte další notifikaci z fronty této koleje
            self._load_next_dorm_notification(dorm_key)

        except asyncio.CancelledError:
            log.info("Úloha notifikace pro kolej '%s' byla zrušena.", dorm_name)

    async def _send_block_alert(self, block: TimeslotBlock, dorm_name: str, role_id: int) -> None:
        if not CHANNEL_ID or not role_id:
            log.warning(
                "CHANNEL_ID nebo role_id pro kolej '%s' není nastaveno, nelze odeslat upozornění.",
                dorm_name,
            )
            return

        channel = self.bot.get_channel(CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(CHANNEL_ID)
            except Exception as e:
                log.warning("Nepodařilo se načíst kanál %s pro notifikace prádla: %s", CHANNEL_ID, e)
                return

        if not isinstance(channel, discord.abc.Messageable):
            log.warning("Kanál %s není zprávový (messageable).", CHANNEL_ID)
            return

        embed = create_block_alert_embed(block, dorm_name)
        mention_str = f"<@&{role_id}>"
        try:
            await channel.send(
                content=f"🧺 {mention_str} **Zítra začíná termín výměny ložního prádla na kolejích {dorm_name}!**",
                embed=embed,
            )
            log.info("Odesláno upozornění pro blok %s do kanálu %s", block.id, CHANNEL_ID)
        except Exception as e:
            log.exception("Chyba při odesílání upozornění pro %s: %s", dorm_name, e)

    pradlo_group = app_commands.Group(name="pradlo", description="Výměna ložního prádla na kolejích")

    @pradlo_group.command(name="palackeho", description="Najde nejbližší termín výměny prádla na kolejích PPV")
    async def palackeho(self, interaction: discord.Interaction) -> None:
        embed = create_pradlo_embed(dorm_key="palackeho")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pradlo(bot))
