from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton

from app.database.requests import get_data_pair, get_teachers_initials, get_number_pair_by_data

from aiogram.utils.keyboard import InlineKeyboardBuilder

import datetime

start_buttons = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Преподаватель'), KeyboardButton(text='Студент')]],
                                    resize_keyboard=True)

space = ReplyKeyboardRemove()

back = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Назад')]],
                           resize_keyboard=True)

edit_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅Подтвердить', callback_data='data_is_right'),
     InlineKeyboardButton(text='✏️Изменить', callback_data='editor')]])


edit_main_buttons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅', callback_data='accept'),
     InlineKeyboardButton(text='✏️', callback_data='edit')]])


edit_personal_data_student = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='🎓ФИО', callback_data="edit_students_initials"),
                      InlineKeyboardButton(text='Группа', callback_data="edit_group")],
                     [InlineKeyboardButton(text='↩️Назад', callback_data="backF")]])

edit_personal_data_teacher = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='💼ФИО', callback_data="edit_teachers_initials"),
                      InlineKeyboardButton(text='Кафедра', callback_data="edit_teachers_department")],
                     [InlineKeyboardButton(text='↩️Назад', callback_data="backF")]])

info_about_me = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Личная информация')]], resize_keyboard=True)

main_buttuns_for_student = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='📅Расписание'), KeyboardButton(text='✅Мое посещение')],
              [KeyboardButton(text='🏆Рейтинг'), KeyboardButton(text='😎Мое место')],
              [KeyboardButton(text='ⓘЛичная информация')]], resize_keyboard=True)

main_buttuns_for_teachers = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='📅Расписание'), KeyboardButton(text='✅Посещение')],
              [KeyboardButton(text='🏆Рейтинг')],
              [KeyboardButton(text='ⓘЛичная информация')]], resize_keyboard=True)

accept_pair_for_teacher = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅', callback_data='accept_pair'),
     InlineKeyboardButton(text='❌', callback_data='cancel_pair')]])

code_generation = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Сгенерировать код присутствия', callback_data='generate_code')]])

accept_roll = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Подтвердить присутствие', callback_data='accept__roll')]])

share_location = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='📌 Поделиться геопозицией', request_location=True)]], resize_keyboard=True)

add_or_delete = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅', callback_data='is_right'),
     InlineKeyboardButton(text='➕', callback_data='add')]])

short_and_full_lessons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Полный список', callback_data='full_lessons'),
     InlineKeyboardButton(text='Сокращенный список', callback_data='short_lessons')]])

async def data_pair(teacher):
    all_pair = await get_data_pair(get_teachers_initials(teacher))
    keyboard = InlineKeyboardBuilder()
    all_date_pair = []
    for pair in all_pair:
        if pair.date not in all_date_pair:
            all_date_pair.append(pair.date)
    for date in all_date_pair:
        keyboard.add(InlineKeyboardButton(text=date, callback_data=f'pair_{date}'))
    keyboard.add(InlineKeyboardButton(text='Вернуться назад', callback_data='to_main'))
    return keyboard.adjust(3).as_markup()

async def number_pair(data_id, teacher):
    date_object = datetime.datetime.strptime(data_id, '%Y-%m-%d').date()
    all_number_pair = await get_number_pair_by_data(date_object, teacher)
    keyboard = InlineKeyboardBuilder()
    for num_pair in all_number_pair:
        keyboard.add(InlineKeyboardButton(text=num_pair.Number_pair, callback_data=f'numPair_{num_pair.id}'))
    keyboard.add(InlineKeyboardButton(text='Вернуться назад', callback_data='to_main'))
    return keyboard.adjust(2).as_markup()