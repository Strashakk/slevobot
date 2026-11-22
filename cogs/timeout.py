import datetime
import logging
import re

import discord
from discord.ext import commands

from cogs.lockin import _parse_duration_value

DEFAULT_TIMEOUT = "1h"
DEFAULT_REASON = "Důvod nebyl uveden"
USAGE = "Použití: `!timeout @user [doba] [důvod]` — např. `!timeout @user 30m spamuje` (výchozí doba je 1h)"
# Stejná gramatika jako parser v lockin (číslo + jednotka s/m/h/d/w), plus speciální "tomorrow"
_DURATION_SHAPE_RE = re.compile(r"^(?:(?:\d+\s*[smhdw]\s*)+|tomorrow)$", re.IGNORECASE)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TimeoutCog(bot))


class TimeoutCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._log = logging.getLogger("slevobot.cogs.timeout")

    @commands.command(
        name="timeout",
        help="Dá uživateli timeout. Použití: !timeout @user [doba] [důvod]. "
        "Výchozí doba je 1h, maximálně 4 týdny (např. 30m, 1h30m, 1d, 1w).",
    )
    @commands.guild_only()
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        args: str = "",
    ) -> None:
        guild = ctx.guild
        invoker = ctx.author
        if guild is None or not isinstance(invoker, discord.Member):
            await ctx.send("Tento příkaz funguje jen na serveru.")
            return

        try:
            seconds, reason = self._parse_args(args)
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        reason = reason or DEFAULT_REASON

        hierarchy_error = self._check_hierarchy(guild, invoker, member)
        if hierarchy_error:
            await ctx.send(hierarchy_error)
            return

        duration = datetime.timedelta(seconds=seconds)
        until = discord.utils.utcnow() + duration

        try:
            await member.timeout(
                duration,
                reason=f"!timeout od {invoker} (ID {invoker.id}): {reason}",
            )
        except discord.Forbidden:
            self._log.info(
                "timeout: chybí oprávnění — invoker=%s target=%s", invoker.id, member.id
            )
            await ctx.send(
                "Nemám oprávnění dát tomuto uživateli timeout "
                "(pravděpodobně má vyšší roli než já)."
            )
            return
        except discord.HTTPException:
            self._log.exception("timeout: HTTP chyba — target=%s", member.id)
            await ctx.send(
                "Při dávaní timeoutu nastala chyba na straně Discordu, zkus to prosím znovu."
            )
            return

        self._log.info(
            "timeout: invoker=%s target=%s seconds=%s reason=%r",
            invoker.id,
            member.id,
            seconds,
            reason,
        )

        await self._dm_member(member, guild, reason, until)

        # replied_user=False zajistí, že odpověď nepinguje autora původního příkazu
        no_ping_mentions = discord.AllowedMentions(
            users=False, roles=False, everyone=False, replied_user=False
        )
        await ctx.reply(
            f"{member.mention} dostal timeout do "
            + discord.utils.format_dt(until, style="F")
            + " ("
            + discord.utils.format_dt(until, style="R")
            + f"). Důvod: {reason}",
            allowed_mentions=no_ping_mentions,
        )

    @staticmethod
    def _parse_args(args: str) -> tuple[int, str]:
        """Vrátí (doba_v_sekundách, důvod).

        Doba je nepovinná (výchozí 1h). Benevolentní parsování: pokud první slovo
        nevypadá jako zápis doby, považuje se celý zbytek za důvod. Pokud ale
        zápis doby vypadá (např. `5w`, `0m`) a je neplatný, vyhodí ValueError
        s českou chybovou hláškou pro uživatele.
        """
        parts = args.strip().split(maxsplit=1)
        if not parts:
            return _parse_duration_value(DEFAULT_TIMEOUT), ""

        first = parts[0]
        if _DURATION_SHAPE_RE.match(first):
            try:
                seconds = _parse_duration_value(first)
            except ValueError as exc:
                raise ValueError(f"Špatná doba trvání ({first})! Zkus např. 30m, 1h, 1d, 1w (maximum 4 týdny).") from exc
            reason = parts[1].strip() if len(parts) > 1 else ""
            return seconds, reason

        return _parse_duration_value(DEFAULT_TIMEOUT), args.strip()

    def _check_hierarchy(
        self,
        guild: discord.Guild,
        invoker: discord.Member,
        target: discord.Member,
    ) -> str | None:
        if self.bot.user and target.id == self.bot.user.id:
            return "Nemohu dát timeout sám sobě."
        if target.id == invoker.id:
            return "Nemůžeš dát timeout sám sobě."
        if target.id == guild.owner_id:
            return "Nemůžeš dát timeout majiteli serveru."
        if not invoker.guild_permissions.administrator and target.top_role >= invoker.top_role:
            return "Nemůžeš dát timeout uživateli s vyšší nebo stejnou nejvyšší rolí."
        return None

    async def _dm_member(
        self,
        member: discord.Member,
        guild: discord.Guild,
        reason: str,
        until: datetime.datetime,
    ) -> None:
        try:
            await member.send(
                f"Dostal jsi timeout na serveru **{guild.name}** do "
                + discord.utils.format_dt(until, style="F")
                + " ("
                + discord.utils.format_dt(until, style="R")
                + f").\nDůvod: {reason}"
            )
        except (discord.Forbidden, discord.HTTPException):
            self._log.info("Nepodařilo se poslat DM o timeoutu uživateli %s", member.id)

    @timeout.error
    async def timeout_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            msg = USAGE
        elif isinstance(error, commands.MissingPermissions):
            msg = "Nemáš oprávnění dávat timeouty."
        elif isinstance(error, commands.BotMissingPermissions):
            msg = "Nemám oprávnění dávat timeouty (chybí mi oprávnění „Časový limit členů“)."
        elif isinstance(error, commands.MemberNotFound):
            msg = f"Uživatel nenalezen. {USAGE}"
        elif isinstance(error, commands.NoPrivateMessage):
            msg = "Tento příkaz funguje jen na serveru."
        elif isinstance(error, commands.BadArgument):
            msg = f"Neplatný argument. {USAGE}"
        else:
            self._log.error("Neočekávaná chyba v příkazu timeout: %r", error)
            msg = "Došlo k neočekávané chybě, zkus to prosím znovu."
        await ctx.send(msg)
