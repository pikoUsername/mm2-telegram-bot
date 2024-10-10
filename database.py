from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import Column, Integer, String, select, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped

from schemas import TransactionStatus

# Путь к базе данных
DATABASE_URL = "sqlite+aiosqlite:///transactions.db"


# Базовый класс для моделей SQLAlchemy
Base = declarative_base()


class Item(Base):
    __tablename__ = "item_transaction"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(ForeignKey('transactions.id'))
    amount = Column(Integer)  # Количество предметов
    item_name = Column(String)  # Название предмета
    unit_price = Column(Float)  # Цена за единицу

    @property
    def total_price(self) -> float:
        return float(self.unit_price * self.amount)


# Модель для хранения обработанных транзакций
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, nullable=False)
    roblox_name = Column(String)
    total_price = Column(Float)  # Общая стоимость
    # status = Column(String, default=TransactionStatus.sent, nullable=True)
    items: Mapped[list[Item]] = relationship("Item")
    timestamp = Column(DateTime, default=datetime.utcnow)  # Время транзакции


class Set(Base):
    __tablename__ = "sets"

    id = Column(Integer, primary_key=True, index=True)
    set_name = Column(String, unique=True, nullable=False)
    items: Mapped[list["SetItem"]] = relationship("SetItem", back_populates="set")


class SetItem(Base):
    __tablename__ = "set_items"

    id = Column(Integer, primary_key=True, index=True)
    set_id = Column(ForeignKey('sets.id'))
    item_name = Column(String)
    amount = Column(Integer)  # Количество предметов в сете

    set: Mapped["Set"] = relationship("Set", back_populates="items")


# Инициализация движка базы данных
engine = create_async_engine(DATABASE_URL, echo=False)
# Инициализация сессий
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Функция для создания таблиц в базе данных
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Функция для проверки, обработан ли transaction_id
async def is_transaction_processed(session, transaction_id):
    async with session() as s:
        result = await s.execute(select(Transaction).filter_by(transaction_id=transaction_id))
        return result.scalar() is not None


# Функция для сохранения нового transaction_id в базе данных
async def save_transaction(session, transaction: Transaction):
    async with session() as s:
        async with s.begin():
            s.add(transaction)
            await s.commit()
