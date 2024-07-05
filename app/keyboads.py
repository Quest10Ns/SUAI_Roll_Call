from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

main = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Преподаватель'), KeyboardButton(text='Студент')]],
                           resize_keyboard=True)

space = ReplyKeyboardRemove()

back = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Назад')]],
                           resize_keyboard=True)

info_about_me = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Личная информация')]], resize_keyboard=True)

