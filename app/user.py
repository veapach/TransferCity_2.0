from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from app.database.requests import set_user, perform_transfer, get_user_by_id, get_user_by_username
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import app.keyboards as kb

router = Router()

class Transfer(StatesGroup):
    receiver_id = State()
    amount = State()
    confirm = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await set_user(message.from_user.id, message.from_user.username)
    if user:
        await message.answer(f'Доброго времени суток, {user.name}!', reply_markup=kb.main)
        await state.clear()
    else:
        user = await get_user_by_username(message.from_user.username)
        await message.answer(f'Здравствуйте, добро пожаловать в TransferCity, {user.name}!', reply_markup=kb.main)

@router.callback_query(F.data == 'cancel')
async def cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer(cache_time=1)
    await state.clear()
    await callback.message.answer('Операция отменена')

@router.message(F.text == 'Перевести points')
async def transfer_points(message: Message, state: FSMContext):
    await state.set_state(Transfer.receiver_id)
    await message.answer('Напишите username(без @) кому хотите перевести', reply_markup=kb.cancel)

@router.message(Transfer.receiver_id)
async def get_receiver_id(message: Message, state: FSMContext):
    receiver = await get_user_by_username(message.text)
    user = await get_user_by_username(message.from_user.username)
    if receiver:
        await state.update_data(receiver_id=receiver.id)
        await state.set_state(Transfer.amount)
        await message.answer(f'Перевод пользователю @{receiver.name}\nСколько вы хотите перевести?\n(мин. - 10, макс. - 100)\n\n'
                             f'Комиссия - 5%\n\nВаш баланс - {user.balance}')
    else:
        await message.answer(f'Пользователь @{message.text} не найден, либо не зарегистрирован в нашей игре!\nПопробуйте еще раз',
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
            await message.answer(f'Вы собираетесь перевести пользователю @{receiver.name}\n{amount} points\n'
                                 f'Итого с вашего баланса будет снято {(amount + (amount * Decimal('0.05'))):.2f} с комиссией 5%\n\n'
                                 f'Подтверждаете?', reply_markup=kb.transfer_accept)
        else:
            await message.answer('Вы ввели неверное значение\n(мин. - 10, макс. - 100)\n\nИли у вас недостаточно баланса'
                                 f'\n(Ваш баланс - {user.balance})\n\n'
                                 'попробуйте еще раз отправить сумму', reply_markup=kb.cancel)
            await state.set_state(Transfer.amount)
    except InvalidOperation:
        await message.answer('Неферный формат суммы. Пожалуйста, введите корректное число', reply_markup=kb.cancel)
        await state.set_state(Transfer.amount)

@router.callback_query(F.data == 'transfer_accepted')
async def transfer_accepted(callback: CallbackQuery, state: FSMContext):
    await callback.answer(cache_time=1)
    data = await state.get_data()
    sender = await get_user_by_username(callback.from_user.username)
    receiver = await get_user_by_id(data['receiver_id'])

    if not sender or not receiver:
        await callback.message.answer('Произошла ошибка при получении данных пользователей')
        await state.clear()
        return

    amount = data['amount']
    commission = amount * Decimal('0.05')
    total_deduction = amount + commission
    if sender.balance < total_deduction:
        await callback.message.answer('Недостаточно баланса для выполнения перевода с учетом комиссии')
        await state.clear()
        return

    success = await perform_transfer(sender.id, receiver.id, amount, commission)
    if success:
        await callback.message.answer(
            f'Перевод успешно выполнен!\nВы перевели {amount:.2f} points пользователю @{receiver.name}.\nКомиссия: {commission:.2f} points'
            f'\nВаш баланс - {(sender.balance - total_deduction):.2f}', reply_markup=kb.main
        )
    else:
        await callback.message.answer('Произошла ошибка при выполнении перевода. Попробуйте позже')

    await state.clear()

@router.callback_query(F.data == 'transfer_declined')
async def transfer_declined(callback: CallbackQuery, state: FSMContext):
    await callback.answer(cache_time=1)
    await state.clear()
    await callback.message.answer('Операция перевода отменена')

@router.message(F.text == 'Баланс')
async def get_balance(message: Message):
    user = await get_user_by_username(message.from_user.username)
    if user:
        await message.answer(f'Ваш баланс - {user.balance}')
    else:
        await message.answer('Вы не зарегистрированы в нашей игре, напишите команду /start')

