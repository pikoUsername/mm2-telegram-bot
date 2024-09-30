from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.declarative import declarative_base


# Путь к базе данных
DATABASE_URL = "sqlite+aiosqlite:///transactions.db"


# Базовый класс для моделей SQLAlchemy
Base = declarative_base()


# Модель для хранения обработанных транзакций
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, nullable=False)


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
async def save_transaction(session, transaction_id):
    async with session() as s:
        async with s.begin():
            new_transaction = Transaction(transaction_id=transaction_id)
            s.add(new_transaction)
            await s.commit()
