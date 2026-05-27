import asyncio
import datetime
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo
from time import time
import logging

from discord.ext import commands
from discord import app_commands
import discord


STATE_FILE = Path(__file__).with_name("lockin_state.json")
MAX_LOCKIN_SECONDS = 4 * 7 * 24 * 60 * 60
PRESET_LABELS = (
    "30m",
    "1h",
    "4h",
    "8h",
    "24h",
    "tomorrow",
    "1d",
    "2d",
    "3d",
    "1w",
    "2w",
    "3w",
    "4w",
)


def _is_valid_duration(s: str) -> bool:
    try:
        _parse_duration_value(s)
    except ValueError:
        return False
    return True


def _duration_to_seconds(s: str) -> int:
    try:
        return _parse_duration_value(s)
    except ValueError:
        return 10 ** 12


def _parse_duration_value(duration: str) -> int:
    normalized = duration.lower().strip()
    if not normalized:
        raise ValueError("Duration must not be empty")

    if normalized == "tomorrow":
        return _seconds_until_midnight()

    matches = re.findall(r"(\d+)\s*([smhdw])", normalized)
    if not matches or "".join(f"{amount}{unit}" for amount, unit in matches) != normalized.replace(" ", ""):
        raise ValueError("Invalid duration format")

    total_seconds = 0
    unit_multipliers = {
        "s": 1,
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
        "w": 7 * 24 * 60 * 60,
    }
    for amount, unit in matches:
        total_seconds += int(amount) * unit_multipliers[unit]

    if total_seconds <= 0:
        raise ValueError("Duration must be greater than zero")

    if total_seconds > MAX_LOCKIN_SECONDS:
        raise ValueError("Duration must not exceed 4 weeks")

    return total_seconds


async def _duration_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    del interaction
    current_value = current.lower().strip()

    suggestions: set[str] = {
        preset
        for preset in PRESET_LABELS
        if preset.startswith(current_value)
        and _duration_to_seconds(preset) <= MAX_LOCKIN_SECONDS
    }

    if (
        current_value
        and _is_valid_duration(current_value)
        and _duration_to_seconds(current_value) <= MAX_LOCKIN_SECONDS
    ):
        suggestions.add(current_value)

    return [
        app_commands.Choice(name=value, value=value)
        for value in sorted(suggestions, key=lambda suggestion: (_duration_to_seconds(suggestion), suggestion))[:25]
    ]


async def _member_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:

    choices = []
    guild = interaction.guild

    if guild:
        guild_id = guild.id
        state = await LockinState(STATE_FILE).load_state()
        ids = [s["member_id"] for s in state if s["guild_id"] == guild_id]
        for member_id in ids:
            member = await guild.fetch_member(int(member_id))
            if member:
                label = f"{member.nick} (@{member.name})" if member.nick else f"@{member.name}"

                if current.lower() in label.lower():
                    choices.append(app_commands.Choice(
                        name=label, value=str(member.id)))

    # Discord limits autocomplete to a maximum of 25 choices
    return choices[:25]


def _seconds_until_midnight() -> int:
    tz = ZoneInfo("Europe/Prague")
    now = datetime.datetime.now(tz)
    next_midnight = (now + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((next_midnight - now).total_seconds())


class LockinState:
    def __init__(self, state_file: Path = STATE_FILE) -> None:
        self._state_file = state_file
        self._lock = asyncio.Lock()

    async def load_state(self) -> list[dict[str, int | float | bool]]:
        if not self._state_file.exists():
            return []

        try:
            return json.loads(self._state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    async def save_state(self, entries: list[dict[str, int | float | bool]]) -> None:
        self._state_file.write_text(json.dumps(
            entries, indent=2), encoding="utf-8")

    async def remove_entry(self, guild_id: int, member_id: int) -> None:
        async with self._lock:
            entries = await self.load_state()
            entries = [
                entry
                for entry in entries
                if not (
                    entry["guild_id"] == guild_id and entry["member_id"] == member_id
                )
            ]
            await self.save_state(entries)

    async def store_entry(
        self,
        guild_id: int,
        member_id: int,
        role_ids: list[int],
        restore_at: float,
    ) -> None:
        async with self._lock:
            entries = await self.load_state()
            entries = [
                entry
                for entry in entries
                if not (
                    entry["guild_id"] == guild_id and entry["member_id"] == member_id
                )
            ]
            entries.append(
                {
                    "guild_id": guild_id,
                    "member_id": member_id,
                    "role_ids": role_ids,
                    "restore_at": restore_at,
                }
            )
            await self.save_state(entries)

    async def pop_entries(self, guild_id: int, member_id: int) -> list[dict]:
        async with self._lock:
            entries = await self.load_state()
            popped = [e for e in entries if e["guild_id"]
                      == guild_id and e["member_id"] == member_id]
            remaining = [e for e in entries if not (
                e["guild_id"] == guild_id and e["member_id"] == member_id)]
            await self.save_state(remaining)
            return popped

    async def has_entry(self, guild_id: int, member_id: int) -> bool:
        async with self._lock:
            entries = await self.load_state()
            return any(
                entry["guild_id"] == guild_id and entry["member_id"] == member_id
                for entry in entries
            )


async def setup(bot: commands.Bot) -> None:
    if bot.user.bot:
        cog = LockIn(bot)
        await bot.add_cog(cog)
        await cog.resume_pending_restores()


class LockIn(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.state = LockinState()
        self._log = logging.getLogger("slevobot.cogs.lockin")

    async def _restore_role_after_timeout(
        self,
        guild_id: int,
        member_id: int,
        role_ids: list[int],
        restore_at: float,
    ) -> None:
        await self.bot.wait_until_ready()

        wait_seconds = max(0.0, restore_at - time())
        if wait_seconds:
            await asyncio.sleep(wait_seconds)

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            await self.state.remove_entry(guild_id, member_id)
            return

        member = guild.get_member(member_id)
        if member is None:
            try:
                member = await guild.fetch_member(member_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                member = None

        roles_to_add = []
        for rid in role_ids:
            role = guild.get_role(rid)
            if member is not None and role is not None and role not in member.roles:
                roles_to_add.append(role)

        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Lockin timeout expired")
        finally:
            await self.state.remove_entry(guild_id, member_id)

    async def resume_pending_restores(self) -> None:
        entries = await self.state.load_state()
        for entry in entries:
            asyncio.create_task(
                self._restore_role_after_timeout(**entry)
            )

    async def _start_lockin_for_member(
        self,
        guild: discord.Guild,
        target: discord.Member,
        restore_delay_seconds: int,
        invoker: discord.Member | str,
    ) -> tuple[list[int], str]:
        """Remove all roles the bot can remove from `target`, apply timeout, and schedule restore.

        Returns (removed_role_ids, timeout_notice)
        """
        # determine removable roles: not @everyone, not managed, and lower than bot's top role
        bot_member = guild.get_member(
            self.bot.user.id) if self.bot.user else None
        if bot_member is None:
            try:
                bot_member = await guild.fetch_member(self.bot.user.id)
            except (discord.NotFound, discord.HTTPException):
                bot_member = None

        bot_top_pos = max((r.position for r in bot_member.roles),
                          default=0) if bot_member else 0

        removable = []
        for r in list(target.roles):
            if r.id == guild.id:
                continue
            if getattr(r, "managed", False):
                continue
            # role position check
            if bot_member and r.position >= bot_top_pos:
                continue
            removable.append(r)

        removed_ids: list[int] = []
        timeout_notice = ""

        if removable:
            try:
                await target.remove_roles(*removable, reason=f"Lockin triggered by {invoker}")
                removed_ids = [r.id for r in removable]
            except (discord.Forbidden, discord.HTTPException):
                # if we can't remove roles, treat as no-op
                removed_ids = []
        # log what we tried to remove
        try:
            self._log.info("_start_lockin_for_member: invoker=%s target=%s removed_ids=%s", getattr(
                invoker, 'id', invoker), getattr(target, 'id', None), removed_ids)
        except Exception:
            pass
        # Always attempt to apply a timeout (works as a pure timeout even if no roles were removable)
        timeout_failed = False
        try:
            await target.timeout(datetime.timedelta(seconds=restore_delay_seconds), reason=f"Lockin triggered by {invoker}")
        except (discord.Forbidden, discord.HTTPException):
            timeout_failed = True
            timeout_notice = " I could not apply the timeout (missing perms or API error)."
        else:
            try:
                self._log.info("_start_lockin_for_member: timeout_applied invoker=%s target=%s seconds=%s", getattr(
                    invoker, 'id', invoker), getattr(target, 'id', None), restore_delay_seconds)
            except Exception:
                pass

        # Persist the entry and schedule restoration if we removed roles or the timeout was applied successfully
        if removed_ids or not timeout_failed:
            restore_at = time() + restore_delay_seconds
            await self.state.store_entry(guild.id, target.id, removed_ids, restore_at)
            asyncio.create_task(self._restore_role_after_timeout(
                guild.id, target.id, removed_ids, restore_at))

        return removed_ids, timeout_notice

    def _parse_duration(self, duration: str) -> int:
        return _parse_duration_value(duration)

    @app_commands.command(name="lockin", description="🔐 Je čas zamknout se dovnitř")
    @app_commands.describe(duration="Po jakou dobu zamknout dovnitř? Např. 8h, 1d, 1w (maximum 4 týdny)")
    @app_commands.checks.bot_has_permissions(manage_roles=True, moderate_members=True)
    @app_commands.autocomplete(duration=_duration_autocomplete)
    @app_commands.guild_only()
    async def _self(
        self,
        interaction: discord.Interaction,
        duration: str,
    ) -> None:
        member = interaction.user
        await interaction.response.defer(thinking=True)
        try:
            restore_delay_seconds = self._parse_duration(duration)
        except ValueError:
            await interaction.followup.send(
                "Špatná doba trvání! Zkus např. 8h, 1d, 1w (maximum 4 týdny)",
                ephemeral=True,
            )
            return

        try:
            removed_ids, timeout_notice = await self._start_lockin_for_member(
                interaction.guild, member, restore_delay_seconds, interaction.user
            )
        except RuntimeError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        # If we neither removed roles nor applied a timeout, treat as error
        if not removed_ids and timeout_notice:
            await interaction.followup.send(
                "Žádné odstranitelné role nebyly nalezeny, nebo jejich odstranění selhalo.",
                ephemeral=True,
            )
            return

        restore_at = int(time() + restore_delay_seconds)
        restore_time = datetime.datetime.fromtimestamp(
            restore_at, tz=datetime.timezone.utc)
        no_ping_mentions = discord.AllowedMentions(
            users=False, roles=False, everyone=False)
        member_mention = member.mention
        await interaction.followup.send(
            f"{member_mention} se zamknul dovnitř do "
            + discord.utils.format_dt(restore_time, style="F")
            + " ("
            + discord.utils.format_dt(restore_time, style="R")
            + ")",
            allowed_mentions=no_ping_mentions,
            ephemeral=False,
        )

    @app_commands.command(name="lockin_remove", description="👑🔐Admin: předčasně zruší uživatelův lockin a obnoví jejich role")
    @app_commands.checks.bot_has_permissions(manage_roles=True, moderate_members=True)
    @app_commands.check(lambda inter: getattr(inter.user, "guild_permissions", None) and inter.user.guild_permissions.administrator)
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(member_id=_member_autocomplete)
    @app_commands.guild_only()
    async def remove(self, interaction: discord.Interaction, member_id: str) -> None:
        # runtime admin check to avoid app_commands check raising and sending automatic errors
        member_user = interaction.user
        await interaction.response.defer(thinking=True)
        member = await interaction.guild.fetch_member(member_id)
        if not isinstance(member_user, discord.Member):
            member_user = interaction.guild.get_member(interaction.user.id)
            if member_user is None:
                try:
                    member_user = await interaction.guild.fetch_member(interaction.user.id)
                except Exception:
                    member_user = None
        is_admin = bool(member_user and getattr(
            member_user, 'guild_permissions', None) and member_user.guild_permissions.administrator)
        try:
            self._log.info("lockin.remove invoked by id=%s name=%s is_admin=%s target=%s", interaction.user.id, getattr(
                interaction.user, 'name', None), is_admin, getattr(member, 'id', None))
        except Exception:
            pass
        if not is_admin:
            await interaction.followup.send(
                "Nemáš oprávnění — pouze administrátoři mohou použít tento příkaz.",
                ephemeral=True,
            )
            return
        no_ping_mentions = discord.AllowedMentions(
            users=False, roles=False, everyone=False)
        member_mention = member.mention

        # Pop persisted entries for this member (may include multiple entries)
        popped = await self.state.pop_entries(interaction.guild.id, member.id)
        role_ids = []
        for e in popped:
            role_ids.extend(e.get("role_ids", []))

        note_parts: list[str] = []

        # Try to restore roles immediately
        target = interaction.guild.get_member(member.id)
        if target is None:
            try:
                target = await interaction.guild.fetch_member(member.id)
            except (discord.NotFound, discord.HTTPException):
                target = None

        if target is not None and role_ids:
            roles_to_add = []
            for rid in set(role_ids):
                r = interaction.guild.get_role(rid)
                if r is not None and r not in target.roles:
                    roles_to_add.append(r)

            if roles_to_add:
                try:
                    await target.add_roles(*roles_to_add, reason=f"Admin {interaction.user} cancelled lockin")
                except (discord.Forbidden, discord.HTTPException):
                    note_parts.append(
                        "Could not add some roles (missing permissions or API error).")

        # Try to clear timeout if present
        if target is not None:
            try:
                await target.timeout(None, reason=f"Admin {interaction.user} cancelled lockin")
                note_parts.append("Timeout removed.")
            except (discord.Forbidden, discord.HTTPException):
                note_parts.append(
                    "Could not remove timeout (missing permissions or API error).")

        has_error = any(part.startswith("Could not") for part in note_parts)

        if has_error:
            await interaction.followup.send("; ".join(note_parts), ephemeral=True)
        else:
            await interaction.followup.send(f"{member_mention} byl odemčen ven", allowed_mentions=no_ping_mentions)

    @app_commands.command(name="lockin_apply", description="👑🔐Admin: Zamkni dovnitř jiného uživatele")
    @app_commands.describe(duration="Po jakou dobu odebrat role? Např. 8h, 1d, 1w (maximum 4 týdny)")
    @app_commands.checks.bot_has_permissions(manage_roles=True, moderate_members=True)
    @app_commands.check(lambda inter: getattr(inter.user, "guild_permissions", None) and inter.user.guild_permissions.administrator)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def apply(self, interaction: discord.Interaction, member: discord.Member, duration: str = '8h') -> None:
        # runtime admin check
        member_user = interaction.user
        await interaction.response.defer(thinking=True)
        if not isinstance(member_user, discord.Member):
            member_user = interaction.guild.get_member(interaction.user.id)
            if member_user is None:
                try:
                    member_user = await interaction.guild.fetch_member(interaction.user.id)
                except Exception:
                    member_user = None
        is_admin = bool(member_user and getattr(
            member_user, 'guild_permissions', None) and member_user.guild_permissions.administrator)
        try:
            self._log.info("lockin.apply invoked by id=%s name=%s is_admin=%s target=%s duration=%s", interaction.user.id, getattr(
                interaction.user, 'name', None), is_admin, getattr(member, 'id', None), duration)
        except Exception:
            pass
        if not is_admin:
            await interaction.followup.send(
                "Nemáš oprávnění — pouze administrátoři mohou použít tento příkaz.",
                ephemeral=True,
            )
            return
        no_ping_mentions = discord.AllowedMentions(
            users=False, roles=False, everyone=False)
        member_mention = member.mention

        try:
            restore_delay_seconds = self._parse_duration(duration)
        except ValueError:
            await interaction.followup.send(
                "Špatná doba trvání! Zkus např. 8h, 1d, 1w (maximum 4 týdny)",
                ephemeral=True,
            )
            return

        if await self.state.has_entry(interaction.guild.id, member.id):
            await interaction.followup.send(f"{member_mention} je už zamčený dovnitř! 🐐", allowed_mentions=no_ping_mentions, ephemeral=True)
            return

        # cancel any existing pending restore for that member
        await self.state.remove_entry(interaction.guild.id, member.id)

        try:
            _, timeout_notice = await self._start_lockin_for_member(
                interaction.guild, member, restore_delay_seconds, interaction.user
            )
        except RuntimeError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        # Success (roles removed or timeout applied)
        restore_at = int(time() + restore_delay_seconds)
        restore_time = datetime.datetime.fromtimestamp(
            restore_at, tz=datetime.timezone.utc)
        await interaction.followup.send(
            f"{member_mention} byl zamčen dovnitř do "
            + discord.utils.format_dt(restore_time, style="F")
            + " ("
            + discord.utils.format_dt(restore_time, style="R")
            + ")",
            allowed_mentions=no_ping_mentions,
            ephemeral=bool(timeout_notice),
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        # Provide a consistent, ephemeral message for permission/check failures
        if isinstance(error, app_commands.CheckFailure):
            msg = "Nemáš oprávnění — pouze administrátoři mohou použít tento příkaz."
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
            except Exception:
                # ignore any send errors
                pass
            return
        if isinstance(error, app_commands.BotMissingPermissions):
            msg = "Mám nedostatečná oprávnění k provedení této akce."
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
            except Exception:
                pass
            return
        # Re-raise other errors so they can be logged by the bot
        raise error
