from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton

main = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Преподаватель'), KeyboardButton(text='Студент')]],
                           resize_keyboard=True)

space = ReplyKeyboardRemove()

back = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Назад')]],
                           resize_keyboard=True)

edit_button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✏️Изменить', callback_data='editor')]])

edit_personal_data_student = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='🎓ФИО', callback_data="edit_students_initials"),
                      InlineKeyboardButton(text='Группа', callback_data="edit_group")]])

edit_personal_data_teacher = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='💼ФИО', callback_data="edit_teachers_initials"),
                      InlineKeyboardButton(text='Кафедра', callback_data="edit_teachers_department")]])

info_about_me = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Личная информация')]], resize_keyboard=True)
