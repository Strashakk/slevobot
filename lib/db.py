from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Boolean
from sqlalchemy import String
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

if TYPE_CHECKING:
    from discord.ext import commands


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "data" / "slevobot.sqlite3"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Cog(Base):
    __tablename__ = "cogs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    module: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"Cog(name={self.name!r}, module={self.module!r}, {'enabled' if self.enabled else 'disabled'})"


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def sync_cogs_from_bot(bot: "commands.Bot", excluded_modules: Iterable[str] = ()) -> None:
    await create_tables()
    excluded = set(excluded_modules)

    async with SessionLocal() as session:
        existing_rows = await session.scalars(select(Cog))
        existing_by_name = {row.name: row for row in existing_rows.all()}

        for cog_name, cog in bot.cogs.items():
            module_name = cog.__module__
            if module_name in excluded:
                continue

            existing = existing_by_name.get(cog_name)
            if existing is None:
                session.add(
                    Cog(name=cog_name, module=module_name, enabled=True))
            else:
                existing.module = module_name

        await session.commit()


async def list_cog_names() -> list[str]:
    await create_tables()

    async with SessionLocal() as session:
        rows = await session.scalars(select(Cog.name).order_by(Cog.name))
        return list(rows.all())


async def list_cogs() -> list[Cog]:
    await create_tables()

    async with SessionLocal() as session:
        rows = await session.scalars(select(Cog).order_by(Cog.name))
        return list(rows.all())


async def list_enabled_cog_names() -> list[str]:
    await create_tables()

    async with SessionLocal() as session:
        rows = await session.scalars(
            select(Cog.name).where(Cog.enabled.is_(True)).order_by(Cog.name)
        )
        return list(rows.all())


async def list_disabled_cog_names() -> list[str]:
    await create_tables()

    async with SessionLocal() as session:
        rows = await session.scalars(
            select(Cog.name).where(Cog.enabled.is_(False)).order_by(Cog.name)
        )
        return list(rows.all())


async def get_enabled_modules() -> set[str]:
    await create_tables()

    async with SessionLocal() as session:
        enabled_rows = await session.scalars(select(Cog.module).where(Cog.enabled.is_(True)))
        return set(enabled_rows.all())


async def get_cog(name: str) -> Cog | None:
    await create_tables()

    async with SessionLocal() as session:
        return await session.scalar(select(Cog).where(Cog.name == name))


async def get_cog_by_module(module: str) -> Cog | None:
    await create_tables()

    async with SessionLocal() as session:
        return await session.scalar(select(Cog).where(Cog.module == module))


async def set_cog_enabled(name: str, enabled: bool, module: str | None = None) -> Cog:
    await create_tables()

    async with SessionLocal() as session:
        cog = await session.scalar(select(Cog).where(Cog.name == name))
        if cog is None:
            if module is None:
                raise ValueError(f"Unknown module for cog {name!r}")
            cog = Cog(name=name, enabled=enabled)
            cog.module = module
            session.add(cog)
        else:
            cog.enabled = enabled
            if module is not None:
                cog.module = module

        await session.commit()
        await session.refresh(cog)
        return cog
