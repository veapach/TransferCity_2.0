from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Перевести points')],
    [KeyboardButton(text='Баланс')],
    [KeyboardButton(text='Место в рейтинге')]
], resize_keyboard=True, input_field_placeholder='Выберите действие')

cancel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Отмена', callback_data='cancel')]
])

transfer_accept = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Да', callback_data='transfer_accepted')],
    [InlineKeyboardButton(text='Нет', callback_data='transfer_declined')],
])