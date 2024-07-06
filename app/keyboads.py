from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

main = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Преподаватель'), KeyboardButton(text='Студент')]],
                           resize_keyboard=True)

space = ReplyKeyboardRemove()

back = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Назад')]],
                           resize_keyboard=True)

edit_personal_data = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text = 'Изменить')]])

info_about_me = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Личная информация')]], resize_keyboard=True)
