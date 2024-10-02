import os.path
from decimal import Decimal, InvalidOperation

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart

from app.database.models import engine
from app.database.requests import set_user, perform_transfer, get_user_by_id, get_user_by_username, get_top_10
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import app.keyboards as kb

router = Router()

balance_photo = FSInputFile(os.path.join(os.path.dirname(__file__), '../img/balance.jpg'))
rating_photo = FSInputFile(os.path.join(os.path.dirname(__file__), '../img/rating.jpg'))

class Transfer(StatesGroup):
    receiver_id = State()
    amount = State()
    confirm = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await set_user(message.from_user.id, message.from_user.username)
    await message.answer(f"👋 Привет, <b>{user.username}</b>!\n\n"
        "Добро пожаловать в <b>TransferCity</b> – место, где вы можете переводить points другим игрокам, "
        "повышать свой рейтинг и получать бонусы за активность. 🏅\n\n"
        "<b>🔹 Основные возможности:</b>\n"
        "<b>🔹 Перевод points друзьям и другим игрокам</b>\n"
        "<b>🔹 Поднятие в глобальном рейтинге</b>\n"
        "<b>🔹 Скоро откроется магазин points для покупки и продажи</b>\n\n"
        "Начните прямо сейчас! Выберите действие ниже ⬇️", reply_markup=kb.main)
    await state.clear()

@router.callback_query(F.data == 'cancel')
async def cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer(cache_time=1)
    await state.clear()
    await callback.message.answer('🚫 Операция отменена', reply_markup=kb.main)

@router.message(F.text == '🔄 Перевести points')
async def transfer_points(message: Message, state: FSMContext):
    await state.set_state(Transfer.receiver_id)
    await message.answer('✉️ Напишите <b>username</b>(без @) кому хотите перевести', reply_markup=kb.cancel)

@router.message(Transfer.receiver_id)
async def get_receiver_id(message: Message, state: FSMContext):
    receiver = await get_user_by_username(message.text)
    user = await get_user_by_username(message.from_user.username)
    if receiver:
        if message.text == message.from_user.username:
            await state.set_state(Transfer.receiver_id)
            await message.answer(f'❌ <b>Вы не можете переводить самому себе!</b>\nУкажите другой юзернейм', reply_markup=kb.cancel)
        else:
            await state.update_data(receiver_id=receiver.id)
            await state.set_state(Transfer.amount)
            await message.answer(f'💼 Перевод пользователю @{receiver.username}\n💰 Сколько вы хотите перевести?\n'
                                 f'<code>(мин. - 10, макс. - 100)</code>\n\n'
                                 f'🪙 Комиссия - <b>5%</b>\n\nВаш баланс - <b>{user.balance:.2f}</b> поинтов', reply_markup=kb.cancel)
    else:
        await message.answer(f'❌ Пользователь @{message.text} не найден, либо не зарегистрирован в нашей игре!\nПопробуйте еще раз',
                             reply_markup=kb.cancel)
        await state.set_state(Transfer.receiver_id)

@router.message(Transfer.amount)
async def get_transfer_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    user = await get_user_by_username(message.from_user.username)
    receiver = await get_user_by_id(data['receiver_id'])
    user_input = message.text.replace(',', '.').strip()

    try:
        amount = Decimal(user_input).quantize(Decimal('0.01'))
        if 10 <= amount <= 100 and amount <= user.balance:
            await state.update_data(amount=amount)
            await state.set_state(Transfer.confirm)
            await message.answer(f'✅ Вы собираетесь перевести пользователю @{receiver.username} <b>{amount}</b> points\n'
                                 f'💸 Итого с вашего баланса будет снято <b>{(amount + (amount * Decimal("0.05"))):.2f}</b> с комиссией 5%\n'
                                 f'⭐ За перевод вы получите <b>{int(amount/10)}</b> рейтинговых очков\n\n'
                                 f'<i>Подтверждаете?</i>', reply_markup=kb.transfer_accept)
        else:
            await message.answer('🛑 Вы ввели неверное значение\n<code>(мин. - 10, макс. - 100)</code>\n\nИли у вас недостаточно баланса'
                                 f'\n<code>(Ваш баланс - {user.balance})</code>\n\n'
                                 'попробуйте еще раз отправить сумму', reply_markup=kb.cancel)
            await state.set_state(Transfer.amount)
    except InvalidOperation:
        await message.answer('🛑 Неверный формат суммы. Пожалуйста, введите корректное число', reply_markup=kb.cancel)
        await state.set_state(Transfer.amount)

@router.callback_query(F.data == 'transfer_accepted')
async def transfer_accepted(callback: CallbackQuery, state: FSMContext):
    await callback.answer(cache_time=1)
    data = await state.get_data()
    sender = await get_user_by_username(callback.from_user.username)
    receiver = await get_user_by_id(data['receiver_id'])

    if not sender or not receiver:
        await callback.message.answer('🛑 Произошла ошибка при получении данных пользователей')
        await state.clear()
        return

    amount = data['amount']
    commission = amount * Decimal('0.05')
    total_deduction = amount + commission
    if sender.balance < total_deduction:
        await callback.message.answer('🛑 Недостаточно баланса для выполнения перевода с учетом комиссии')
        await state.clear()
        return

    success = await perform_transfer(sender.id, receiver.id, amount, commission)
    if success:
        await callback.message.answer(
            f'Перевод успешно выполнен!✅\n\n'
            f'💸 Вы перевели <b>{amount}</b> points пользователю @{receiver.username} 💸'
            f'\nКомиссия: <i>{commission:.2f}</i> points'
            f'\nВаш баланс - <b>{(sender.balance - total_deduction):.2f}</b>', reply_markup=kb.main
        )
        await callback.bot.send_message(
            chat_id=receiver.tg_id,
            text=(
                f'🎉 Вам перевели <b>{amount - commission:.2f}</b> points от пользователя @{sender.username}'
                f'\nВаш текущий баланс - <b>{receiver.balance + amount:.2f}</b>'
            )
        )
    else:
        await callback.message.answer('🛑 Произошла ошибка при выполнении перевода. Попробуйте позже')

    await state.clear()

@router.callback_query(F.data == 'transfer_declined')
async def transfer_declined(callback: CallbackQuery, state: FSMContext):
    await callback.answer(cache_time=1)
    await state.clear()
    await callback.message.answer('Операция перевода отменена')

@router.message(F.text == '💰 Баланс')
async def get_balance(message: Message):
    user = await get_user_by_username(message.from_user.username)
    if user:
        await message.answer_photo(photo=balance_photo, caption=f'💰 Ваш баланс: <b>{user.balance:.2f}</b> поинтов')
    else:
        await message.answer('Вы не зарегистрированы в нашей игре, напишите команду /start')

@router.message(F.text == '🏅 Рейтинг')
async def get_global_rank(message: Message):
    user = await get_user_by_username(message.from_user.username)
    if user:
        await message.answer_photo(photo=rating_photo, caption=f'🥇 Ваше место в рейтинге - <b>{user.global_rank}</b>\n'
                             f'⭐ У вас <b>{user.rating_points}</b> рейтинговых очков\n\n'
                             f'📈 Переводите points другим игрокам, чтобы заработать больше рейтинга!')
    else:
        await message.answer('Вы не зарегистрированы в нашей игре, напишите команду /start')

@router.message(F.text == '📩 Связаться с поддержкой')
async def contact_with_admin(message: Message):
    await message.answer('Контакт для связи - @veapach')

@router.message(F.text == '🔝 Топ-10')
async def result_top_10(message: Message):
    top_users = await get_top_10()
    if top_users:
        top_list = '\n'.join(
            [f'{rank + 1}. @{user.username} - {user.rating_points} очков' for rank, user in enumerate(top_users)]
        )
        await message.answer('🏆 <b>Топ-10 пользователей по рейтингу:</b>\n' + top_list)
    else:
        await message.answer("❌ Топ-10 пользователей не найдено.")