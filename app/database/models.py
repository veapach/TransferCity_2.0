import datetime

from sqlalchemy import ForeignKey, String, BigInteger, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, AsyncSession
from decimal import Decimal

from app.database.types import DecimalType

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    balance: Mapped[Decimal] = mapped_column(DecimalType(), default=Decimal('100.00'))
    rating_points: Mapped[int] = mapped_column(Integer, default=100)
    global_rank: Mapped[int] = mapped_column(Integer, default=0)
    last_daily_reward = mapped_column(DateTime, default=datetime.datetime.utcnow)

    # TODO: Реферальная система, премиум подписка


class Transfer(Base):
    __tablename__ = 'transfers'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    receiver_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DecimalType(), nullable=False)
    commission: Mapped[Decimal] = mapped_column(DecimalType(), nullable=False)
    timestamp = mapped_column(DateTime, default=datetime.datetime.utcnow)

    sender = relationship('User', foreign_keys=[sender_id])
    receiver = relationship('User', foreign_keys=[receiver_id])


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
