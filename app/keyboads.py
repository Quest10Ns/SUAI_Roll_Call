from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton

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
    [InlineKeyboardButton(text='➕', callback_data='add'),
     InlineKeyboardButton(text='➖', callback_data='dalete')]])
