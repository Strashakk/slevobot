from __future__ import annotations

import os
from typing import Any
from typing import Callable
from typing import TypeVar

import discord
from discord import app_commands
from discord.ext import commands


CommandT = TypeVar("CommandT")


def _get_dev_server_id() -> int | None:
    raw_value = os.getenv("DEV_SERVER")
    if raw_value is None or not raw_value.strip():
        return None

    try:
        return int(raw_value.strip())
    except ValueError:
        return None


def _guild_id_from_target(target: Any) -> int | None:
    guild = getattr(target, "guild", None)
    if guild is not None:
        return getattr(guild, "id", None)

    interaction_guild = getattr(target, "guild_id", None)
    if interaction_guild is not None:
        return interaction_guild

    return None


async def _dev_server_predicate(target: commands.Context | discord.Interaction) -> bool:
    dev_server_id = _get_dev_server_id()
    if dev_server_id is None:
        return True

    return _guild_id_from_target(target) == dev_server_id


def _dev_server_check() -> Callable[[commands.Context | discord.Interaction], Any]:
    async def predicate(target: commands.Context | discord.Interaction) -> bool:
        return await _dev_server_predicate(target)

    return predicate


def dev_server_only(command: CommandT) -> CommandT:
    if isinstance(command, commands.Command):
        command.checks.append(_dev_server_check())
        return command

    if isinstance(command, app_commands.Command):
        command.checks.append(_dev_server_check())
        return command

    return command
