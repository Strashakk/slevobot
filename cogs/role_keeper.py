import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, TypedDict, cast

import discord
from discord.ext import commands

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "role_keeper.json"


class Entry(TypedDict):
    member_id: int
    guild_id: int
    role_ids: list[int]


class RoleKeeper(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._log = logging.getLogger("slevobot.cogs.role_keeper")
        self._state_lock = asyncio.Lock()
    @staticmethod
    def save(entry: Entry) -> None:
        entries: list[Entry] = [
            saved
            for saved in RoleKeeper._load_entries()
            if not (
                saved["member_id"] == entry["member_id"]
                and saved["guild_id"] == entry["guild_id"]
            )
        ]
        entries.append(entry)
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    @staticmethod
    def delete(member_id: int, guild_id: int) -> None:
        entries = [
            entry
            for entry in RoleKeeper._load_entries()
            if not (entry["member_id"] == member_id and entry["guild_id"] == guild_id)
        ]
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    @staticmethod
    def find(member_id: int, guild_id: int) -> Optional[Entry]:
        for entry in RoleKeeper._load_entries():
            if entry["member_id"] == member_id and entry["guild_id"] == guild_id:
                return entry
        return None

    @staticmethod
    def _load_entries() -> list[Entry]:
        if not STATE_FILE.exists():
            return []

        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        if not isinstance(data, list):
            return []

        entries: list[Entry] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            if not {"member_id", "guild_id", "role_ids"} <= item.keys():
                continue
            if (
                not isinstance(item["member_id"], int)
                or not isinstance(item["guild_id"], int)
                or not isinstance(item["role_ids"], list)
                or not all(isinstance(role_id, int) for role_id in item["role_ids"])
            ):
                continue
            entries.append(cast(Entry, item))
        return entries

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        entry = RoleKeeper.find(member.id, member.guild.id)
        if entry is None:
            return

        roles = [
            role
            for role in (
                member.guild.get_role(role_id) for role_id in entry["role_ids"]
            )
            if role is not None and role.is_assignable()
        ]
        try:
            if roles:
                self._log.info(
                    f"Restoring {len(roles)} roles for member {member.name} ({member.id}) in guild {member.guild.name} ({member.guild.id})"
                )
                await member.add_roles(*roles, reason="Restoring saved roles")
        finally:
            RoleKeeper.delete(member.id, member.guild.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        member_id = member.id
        guild_id = member.guild.id
        role_ids = [role.id for role in member.roles if role.name != "@everyone"]
        entry: Entry = {
            "member_id": member_id,
            "guild_id": guild_id,
            "role_ids": role_ids,
        }
        if len(role_ids) == 0:
            return
        else:
            try:
                RoleKeeper.save(entry)
            except Exception as e:
                print(e)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleKeeper(bot))
