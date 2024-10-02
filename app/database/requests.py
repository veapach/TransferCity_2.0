from app.database.models import async_session
from app.database.models import User, Transfer
from sqlalchemy import select, update
from decimal import Decimal

def connection(func):
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            return await func(session, *args, **kwargs)
    return wrapper

@connection
async def set_user(session, tg_id, username):
    user = await session.scalar(select(User).where(User.tg_id == tg_id))

    if not user:
        new_user = User(tg_id=tg_id, name=username)
        session.add(new_user)
        await session.commit()
        return new_user
    else:
        return user

@connection
async def get_user_by_username(session, username):
    user = await session.scalar(select(User).where(User.name == username))
    return user if user else None

@connection
async def get_user_by_id(session, user_id):
    user = await session.scalar(select(User).where(User.id == user_id))
    return user if user else None

@connection
async def perform_transfer(session, sender_id, receiver_id, amount, commission):
    try:
        sender = await session.get(User, sender_id)
        receiver = await session.get(User, receiver_id)

        if sender.balance < (amount + commission):
            return False

        sender.balance -= (amount + commission)
        receiver.balance += amount

        transfer = Transfer(
            sender_id=sender_id,
            receiver_id=receiver_id,
            amount=Decimal(amount),
            commission=Decimal(commission)
        )
        session.add(transfer)
        await session.commit()
        return True
    except Exception as e:
        await session.rollback()
        print(f'Ошибка при переводе:\n\n{e}')
        return False