from datetime import datetime

from sqlalchemy import Integer, Column, ForeignKey, Float, String, DateTime, func
from sqlalchemy.orm import relationship, Mapped

from db.base import Base


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.now, server_default=func.now())


class ItemEntity(BaseModel):
    __tablename__ = "item_transaction"

    transaction_id = Column(ForeignKey('transactions.id'))
    amount = Column(Integer)  # Количество предметов
    item_name = Column(String)  # Название предмета
    unit_price = Column(Float)  # Цена за единицу

    @property
    def total_price(self) -> float:
        return float(self.unit_price * self.amount)


# Модель для хранения обработанных транзакций
class Transaction(BaseModel):
    __tablename__ = "transactions"

    transaction_id = Column(String, unique=True, nullable=False)
    roblox_name = Column(String)
    total_price = Column(Float)  # Общая стоимость
    # status = Column(String, default=TransactionStatus.sent, nullable=True)
    items: Mapped[list[ItemEntity]] = relationship("ItemEntity", lazy="joined")
    timestamp = Column(DateTime, default=datetime.utcnow, server_default=func.now())  # Время транзакции


class Set(BaseModel):
    __tablename__ = "sets"

    set_name = Column(String, unique=True, nullable=False)
    items: Mapped[list["SetItem"]] = relationship("SetItem", lazy="joined")


class SetItem(BaseModel):
    __tablename__ = "set_items"

    set_id = Column(ForeignKey('sets.id'))
    item_name = Column(String)
    amount = Column(Integer)  # Количество предметов в сете

    set: Mapped["Set"] = relationship("Set", back_populates="items")


class Alias(BaseModel):
    __tablename__ = "aliases"

    origin_name = Column(String, index=True)
    alias_name = Column(String)
