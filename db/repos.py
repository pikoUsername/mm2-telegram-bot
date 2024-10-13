from datetime import timedelta, datetime
from typing import Sequence
import re

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from db.models import Transaction, Set, ItemEntity, SetItem, Alias


async def is_transaction_processed(session, transaction_id):
    result = await session.execute(select(Transaction).filter_by(transaction_id=transaction_id))
    return result.scalar() is not None


# Функция для сохранения нового transaction_id в базе данных
async def save_transaction(session: AsyncSession, transaction: Transaction):
    async with session.begin():
        session.add(transaction)
        await session.commit()


async def get_all_sets(session: AsyncSession, start: int = 0, end: int = 10) -> Sequence[Set]:
    stmt = select(Set).offset(start).limit(end)
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def add_set_command(session: AsyncSession, message: str) -> str:
    # Регулярное выражение для парсинга команды
    set_pattern = r"/add_set ([\w\s]+) \(([\w\s]+) x(\d+)\)(?:; \(([\w\s]+) x(\d+)\))*"
    match = re.match(set_pattern, message)

    if not match:
        return "Неверный формат команды. Пример: /add_set Blue set (Red seer x1); (Fire fox x2)"

    set_name = match.group(1)
    item_1_name = match.group(2)
    item_1_amount = int(match.group(3))

    # Проверяем, есть ли второй предмет (он необязателен)
    item_2_name = match.group(4) if match.group(4) else None
    item_2_amount = int(match.group(5)) if match.group(5) else None

    # Проверка: существует ли сет с таким названием
    existing_set = await session.execute(select(Set).where(Set.set_name == set_name))
    existing_set = existing_set.scalars().first()

    if existing_set:
        return f"Сет с названием '{set_name}' уже существует."

    # Создаем новый сет
    new_set = Set(set_name=set_name)

    # Добавляем предметы в сет
    set_items = [SetItem(item_name=item_1_name, amount=item_1_amount, set=new_set)]

    if item_2_name:
        set_items.append(SetItem(item_name=item_2_name, amount=item_2_amount, set=new_set))

    # Добавляем сет и его предметы в базу
    session.add(new_set)
    session.add_all(set_items)
    await session.commit()

    return f"Сет '{set_name}' успешно добавлен с предметами: {item_1_name} x{item_1_amount}" + (
        f", {item_2_name} x{item_2_amount}" if item_2_name else "")


async def search_sets(session: AsyncSession, name: str) -> Set | None:
    stmt = select(Set).where(Set.set_name == name)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_set_by_name(session: AsyncSession, set_name: str) -> Set | None:
    # Поиск сета по названию
    result = await session.execute(select(Set).where(Set.set_name == set_name))
    return result.scalars().first()


async def get_analytics(session: AsyncSession):
    now = datetime.utcnow()

    # Аналитика за последнюю неделю
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Запросы для аналитики
    week_transactions = await session.execute(
        select(func.count(Transaction.id)).filter(Transaction.timestamp >= week_ago)
    )
    month_transactions = await session.execute(
        select(func.count(Transaction.id)).filter(Transaction.timestamp >= month_ago)
    )
    total_transactions = await session.execute(
        select(func.count(Transaction.id))
    )

    # Подсчет потраченных средств
    week_spent = await session.execute(
        select(func.sum(Transaction.total_price)).where(Transaction.timestamp >= week_ago)
    )
    month_spent = await session.execute(
        select(func.sum(Transaction.total_price)).where(Transaction.timestamp >= month_ago)
    )
    total_spent = await session.execute(
        select(func.sum(Transaction.total_price))
    )

    return {
        'week_transactions': week_transactions.scalar(),
        'month_transactions': month_transactions.scalar(),
        'total_transactions': total_transactions.scalar(),
        'week_spent': week_spent.scalar() or 0,
        'month_spent': month_spent.scalar() or 0,
        'total_spent': total_spent.scalar() or 0
    }


async def get_items_report(session: AsyncSession):
    # Группировка по типам предметов и подсчет общего количества
    items_report = await session.execute(
        select(
            ItemEntity.item_name,
            func.count(ItemEntity.item_name),
            func.sum(ItemEntity.amount)
        ).group_by(ItemEntity.item_name)
    )

    return items_report.all()


async def get_recent_transactions(session: AsyncSession, start: int = 0, limit: int = 10):
    # Получение транзакций с заданным смещением (start) и лимитом (limit)
    query = (
        select(Transaction)
        .options(joinedload(Transaction.items))  # Загрузка связанных предметов
        .order_by(Transaction.timestamp.desc())  # Сортировка по времени
        .offset(start)  # Смещение от начала
        .limit(limit)  # Лимит на количество транзакций
    )

    result = await session.execute(query)
    transactions = result.scalars().unique().all()

    return transactions


async def get_aliases(session: AsyncSession, start: int = 0, limit: int = 10) -> Sequence[Alias]:
    query = (
        select(Alias)
        .offset(start)  # Смещение от начала
        .limit(limit)  # Лимит на количество транзакций
    )

    result = await session.execute(query)
    aliases = result.scalars().unique().all()

    return aliases


async def get_alias(session: AsyncSession, origin_name: str) -> Alias | None:
    result = await session.execute(select(Alias).where(Alias.origin_name == origin_name))
    existing_alias = result.scalars().first()

    return existing_alias


async def add_alias(session: AsyncSession, alias: Alias) -> int:
    session.add(alias)
    await session.commit()
    await session.refresh(alias)

    return alias.id


async def remove_alias(session: AsyncSession, alias_name: str) -> int | None:
    alias = await get_alias(session, alias_name)
    if not alias:
        return
    await session.delete(alias)
    await session.commit()

    return alias.id
