import asyncio
import os
import time as tim
import logging
from datetime import datetime, time, timedelta, date
import re
from aiogram import Bot
from aiogram import types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import app.keyboads as kb
import app.database.requests as rq
import app.database.add_schedule__to_db_for_students as ass
from dotenv import load_dotenv
from aiogram.types import location
from app.database.models import async_session
from app.database.models import User, Teacher, Student, ScheduleForStudent, ScheduleForTeacher, MainScheduleForTeacher, ListOfPresent, Rang
from sqlalchemy import select, update, delete, and_

router = Router()

attempts = {}


def get_lesson_name(schedule, lesson_number):
    today = date.fromtimestamp(tim.time())
    current_week = (date(today.year, today.month, today.day).isocalendar()[1]) % 2
    if current_week == 1:
        pattern = rf"{lesson_number[0]} {lesson_number[1]} [ПРЛ]+.*? – (.*) – |{lesson_number[0]} .* ▲ [ПРЛ]+ – (.*) – .* ▼|{lesson_number[0]} .* ▲ [ПРЛ]+ – (.*) –"
        match = re.findall(pattern, schedule)
        for i in range(len(match)):
            for lesson in (match[i]):
                if lesson != '':
                    return lesson
        return None
    else:
        pattern = rf"{lesson_number[0]} {lesson_number[1]} [ПРЛ]+.*?– (.*) – |{lesson_number[0]} .* ▼ [ПРЛ]+ – (.*) –"
        match = re.findall(pattern, schedule)
        for i in range(len(match)):
            for lesson in (match[i]):
                if lesson != '':
                    return lesson
        return None


class RegisterForTeachers(StatesGroup):
    initials = State()
    departmend = State()
    verification_code = State()


class RegisterForStudents(StatesGroup):
    initials = State()
    group = State()


class RegisterUsers(StatesGroup):
    status = State()


class RegisterCode(StatesGroup):
    code = State()


class RegisterAsPresent(StatesGroup):
    code = State()
    location = State()


class AddStudents(StatesGroup):
    students = State()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    if (await rq.get_user_status(message.from_user.id) and (
            ((await rq.get_student_group(message.from_user.id) is not None) and (
                    (await rq.get_student_initials(message.from_user.id) is not None)) or (
                     (await rq.get_teachers_initials(message.from_user.id) is not None) and (
                     await rq.get_teachers_department(message.from_user.id) is not None))))):
        if await rq.get_student(message.from_user.id):
            await message.answer('И снова здравствуйте', reply_markup=kb.main_buttuns_for_student)
        elif await rq.get_teacher(message.from_user.id):
            await message.answer('И снова здравствуйте', reply_markup=kb.main_buttuns_for_teachers)
        else:
            await message.answer('Продолжите регистрацию', reply_markup=kb.start_buttons)
    else:
        await rq.set_user(message.from_user.id)
        await state.set_state(RegisterUsers.status)
        await message.answer('Добро пожаловать в бота, который проверяет посещения пар в ГУАПе',
                             reply_markup=kb.start_buttons)


@router.message(F.text == 'Неверный код доступа. Видимо Вы не преподаватель')
async def cmd_start(message: types.Message, state: FSMContext):
    await rq.set_user(message.from_user.id)
    await state.set_state(RegisterUsers.status)
    await message.answer('Добро пожаловать в бота, который проверяет посещения пар в ГУАПе',
                         reply_markup=kb.start_buttons)


@router.message(Command('info'))
async def cmd_info(message: types.Message):
    await message.answer('Im Helping')


@router.message(RegisterUsers.status)
async def register_user(message: types.Message, state: FSMContext):
    if message.text == 'Преподаватель':
        await message.reply('Отлично, теперь необходима пройти регистрацию и подтвердить, что вы преподаватель')
        await message.answer('Введите ваше имя, фамилию и отчество', reply_markup=kb.back)
        await state.set_state(RegisterForTeachers.initials)
        await rq.set_user_status(message.from_user.id, message.text)

    elif message.text == 'Студент':
        await message.reply('Отлично, теперь необходима пройти регистрацию')
        await message.answer('Введите ваше имя, фамилию и отчество', reply_markup=kb.back)
        await state.set_state(RegisterForStudents.initials)
        await rq.set_user_status(message.from_user.id, message.text)

    else:
        await message.reply('Пожалуйста, выберите правильный статус: Преподаватель или Студент',
                            reply_markup=kb.start_buttons)


@router.message(RegisterForTeachers.initials)
async def register_name_for_teacher(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:',
                             reply_markup=kb.start_buttons)
    else:
        if not await rq.get_teachers_initials(message.from_user.id):
            cur_initials = await rq.get_right_initials(message.text)
            if not cur_initials:
                await message.answer(f'Такого преподавателя не существует. Попробуйте еще раз',
                                     reply_markup=kb.main_buttuns_for_teachers)
            else:
                await state.update_data(initials=message.text)
                await rq.set_student_initials_for_teachers(message.from_user.id, message.chat.id, message.text)
                await state.set_state(RegisterForTeachers.departmend)
                await message.answer('Введите вашу кафедру', reply_markup=kb.back)
        else:
            cur_initials = await rq.get_right_initials(message.text)
            if not cur_initials:
                await message.answer(f'Такого преподавателя не существует. Попробуйте еще раз',
                                     reply_markup=kb.main_buttuns_for_teachers)
            else:
                await state.update_data(initials=message.text)
                await rq.set_student_initials_for_teachers(message.from_user.id, message.chat.id, message.text)
                await state.clear()
                if await rq.get_teachers_initials(message.from_user.id) == message.text:
                    await message.answer(f'ФИО успешно изменено на {message.text}',
                                         reply_markup=kb.main_buttuns_for_teachers)
                else:
                    await message.answer(f'Изменить не удалось', reply_markup=kb.main_buttuns_for_teachers)


@router.message(RegisterForTeachers.departmend)
async def register_departmend_for_teachers(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:',
                             reply_markup=kb.start_buttons)
    else:
        if not await rq.get_teachers_department(message.from_user.id):
            await state.update_data(departmend=message.text)
            await rq.set_departmend_for_teachers(message.from_user.id, message.text)
            await state.set_state(RegisterForTeachers.verification_code)
            await message.answer('Введите код для подтверждения статуса преподавателя', reply_markup=kb.back)
        else:
            await state.update_data(departmend=message.text)
            await rq.set_departmend_for_teachers(message.from_user.id, message.text)
            await state.clear()
            if await rq.get_teachers_department(message.from_user.id) == message.text:
                await message.answer(f'Кафедра успешно изменена на {message.text}',
                                     reply_markup=kb.main_buttuns_for_teachers)
            else:
                await message.answer(f'Изменить не удалось', reply_markup=kb.main_buttuns_for_teachers)


@router.message(RegisterForTeachers.verification_code)
async def register_verification_code(message: types.Message, state: FSMContext):
    load_dotenv()
    user_id = message.from_user.id
    if user_id not in attempts:
        attempts[user_id] = {'count': 0, 'cooldown': 0}
    current_time = tim.time()

    if current_time < attempts[user_id]['cooldown']:
        remaining_time = int(attempts[user_id]['cooldown'] - current_time)
        await message.answer(f'Вы превысили количество попыток. Пожалуйста, подождите {remaining_time} секунд.')
        return

    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:',
                             reply_markup=kb.start_buttons)
    else:
        if message.text == os.getenv('TEACHERS_PASSWORD'):
            await state.update_data(verification_code=message.text)
            data = await state.get_data()
            await message.answer(
                f'Вы успешно зарегистрированы как преподаватель. \n Ваше ФИО: {data["initials"]} \n Кафедра: {data["departmend"]}',
                reply_markup=kb.edit_button)
            await state.clear()
            attempts[user_id]['count'] = 0
        else:
            attempts[user_id]['count'] += 1
            if attempts[user_id]['count'] >= 3:
                attempts[user_id]['cooldown'] = current_time + 60
                await message.answer('Неверный код доступа. Попробуйте еще раз через 60 секунд', reply_markup=kb.back)
            else:
                await state.set_state(RegisterForTeachers.verification_code)
                await message.answer(
                    f'Неверный код доступа. Попробуйте еще раз. Осталось попыток: {3 - attempts[user_id]["count"]}',
                    reply_markup=kb.back)


@router.message(RegisterForStudents.initials)
async def register_name_for_student(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:',
                             reply_markup=kb.start_buttons)
    else:
        if not await rq.get_student_initials(message.from_user.id):
            await state.update_data(initials=message.text)
            await rq.set_student_initials_for_students(message.from_user.id, message.chat.id, message.text)
            await state.set_state(RegisterForStudents.group)
            await message.answer('Введите вашу учебную группу', reply_markup=kb.back)
        else:
            await state.update_data(initials=message.text)
            await rq.set_student_initials_for_students(message.from_user.id, message.chat.id, message.text)
            await state.clear()
            if await rq.get_student_initials(message.from_user.id) == message.text:
                await message.answer(f'ФИО успешно изменено на {message.text}',
                                     reply_markup=kb.main_buttuns_for_student)
            else:
                await message.answer(f'Изменить не удалось', reply_markup=kb.main_buttuns_for_student)


@router.message(RegisterForStudents.group)
async def register_group(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:',
                             reply_markup=kb.start_buttons)
    else:
        if not await rq.get_student_group(message.from_user.id):
            cur_group = await rq.get_right_gpoup(message.text)
            if not cur_group:
                await message.answer(f'Такой группы не существует. Попробуйте еще раз',
                                     reply_markup=kb.space)
            else:
                await state.update_data(group=message.text)
                await rq.set_group_for_student(message.from_user.id, message.text)
                data = await state.get_data()
                await message.answer(
                    f'Вы успешно зарегистрированы как студент. \n Ваше ФИО: {data["initials"]} \n Ваша учебная группа: {data["group"]}',
                    reply_markup=kb.edit_button)
                await rq.set_people_in_rang_system(message.from_user.id)
                await message.reply(
                    f'Так же вы были добавлены в ранговую систему, Вам были начислены стартовые 100 очков')
                await state.clear()
        else:
            cur_group = await rq.get_right_gpoup(message.text)
            if not cur_group:
                await message.answer(f'Такой группы не существует. Попробуйте еще раз',
                                     reply_markup=kb.space)
            else:
                await state.update_data(group=message.text)
                await rq.set_group_for_student(message.from_user.id, message.text)
                await state.clear()
                if await rq.get_student_group(message.from_user.id) == message.text:
                    await message.answer(f'Группа успешно изменена на {message.text}',
                                         reply_markup=kb.main_buttuns_for_student)
                else:
                    await message.answer(f'Изменить не удалось', reply_markup=kb.main_buttuns_for_student)


@router.callback_query(F.data == 'data_is_right')
async def edit_personal_data(callback: types.CallbackQuery):
    if await rq.get_user_status(callback.from_user.id) == 'Студент':
        await callback.message.answer('Отлично, регистрация успешно пройдена!',
                                      reply_markup=kb.main_buttuns_for_student)
    else:
        await rq.set_schedule_for_certain_teacher(callback.from_user.id)
        await callback.message.answer('Отлично, регистрация успешно пройдена!',
                                      reply_markup=kb.main_buttuns_for_teachers)
    await callback.answer()


@router.callback_query(F.data == 'editor')
async def edit_personal_data(callback: types.CallbackQuery):
    status = await rq.get_user_status(callback.from_user.id)
    if status == 'Студент':
        await callback.message.reply('Выберите, что Вы хотите изменить', reply_markup=kb.edit_personal_data_student)
    else:
        await callback.message.reply('Выберите, что Вы хотите изменить', reply_markup=kb.edit_personal_data_teacher)


@router.callback_query(F.data == 'edit_teachers_initials')
async def edit_initials_for_teachers_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RegisterForTeachers.initials)
    await callback.answer('Вы выбрали изменить ФИО')
    await callback.message.answer('Введите новые ФИО', reply_markup=kb.space)


@router.callback_query(F.data == 'edit_students_initials')
async def edit_initials_for_student_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RegisterForStudents.initials)
    await callback.answer('Вы выбрали изменить ФИО')
    await callback.message.answer('Введите новые ФИО', reply_markup=kb.space)


@router.callback_query(F.data == 'edit_group')
async def edit_group(callback: types.CallbackQuery, state: FSMContext):
    await  state.set_state(RegisterForStudents.group)
    await callback.answer('Вы выбрали изменить группу')
    await callback.message.answer('Введите новую группу', reply_markup=kb.space)


@router.callback_query(F.data == 'edit_teachers_department')
async def edit_group(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RegisterForTeachers.departmend)
    await callback.answer('Вы выбрали изменить кафедру')
    await callback.message.answer('Введите новую кафедру', reply_markup=kb.space)


@router.message(F.text == 'ⓘЛичная информация')
async def main_personal_data(message: types.Message):
    if await rq.get_user_status(message.from_user.id) == 'Студент':
        await message.answer(
            f'Ваши данные: \n Ваш статус: Студент \n Ваше ФИО: {await rq.get_student_initials(message.from_user.id)} \n Ваша учебная группа: {await rq.get_student_group(message.from_user.id)}',
            reply_markup=kb.edit_main_buttons)
    else:
        await message.answer(
            f'Ваши данные: \n Ваш статус: Преподаватель \n Ваше ФИО: {await rq.get_teachers_initials(message.from_user.id)} \n Кафедра: {await rq.get_teachers_department(message.from_user.id)}',
            reply_markup=kb.edit_main_buttons)


@router.callback_query(F.data == 'accept')
async def acceppted_personal_data(callback: types.CallbackQuery):
    await callback.answer('Успешно!')
    await callback.message.answer('✅')


@router.callback_query(F.data == 'edit')
async def edit_main_persoanl_data(callback: types.CallbackQuery):
    status = await rq.get_user_status(callback.from_user.id)
    if status == 'Студент':
        await callback.message.edit_text('Выберите, что Вы хотите изменить', reply_markup=kb.edit_personal_data_student)
    else:
        await callback.message.edit_text('Выберите, что Вы хотите изменить', reply_markup=kb.edit_personal_data_teacher)


@router.callback_query(F.data == 'backF')
async def edit_back(callback: types.CallbackQuery):
    await callback.answer('Вы вернулись назад')
    status = rq.get_user_status(callback.from_user.id)
    if status == 'Студент':
        await callback.message.edit_text(
            f'Ваши данные: \n Ваш статус: Студент \n Ваше ФИО: {await rq.get_student_initials(callback.from_user.id)} \n Ваша учебная группа: {await rq.get_student_group(callback.from_user.id)}',
            reply_markup=kb.edit_main_buttons)
    else:
        await callback.message.edit_text(
            f'Ваши данные: \n Ваш статус: Преподаватель \n Ваше ФИО: {await rq.get_teachers_initials(callback.from_user.id)} \n Кафедра: {await rq.get_teachers_department(callback.from_user.id)}',
            reply_markup=kb.edit_main_buttons)


@router.message(F.text == '📅Расписание')
async def main_schedule(message: types.Message):
    if await rq.get_user_status(message.from_user.id) == 'Студент':
        schedule = await rq.get_schedule(message.from_user.id)
        schedule_string = (
            f'Ваше расписание: \n\n'
            f'Понедельник: \n\n{schedule.Monday if schedule.Monday else " Пар нет \n"}\n'
            f'Вторник: \n\n{schedule.Tuesday if schedule.Tuesday else " Пар нет \n"}\n'
            f'Среда: \n\n{schedule.Wednesday if schedule.Wednesday else " Пар нет \n"}\n'
            f'Четверг: \n\n{schedule.Thursday if schedule.Thursday else " Пар нет \n"}\n'
            f'Пятница: \n\n{schedule.Friday if schedule.Friday else " Пар нет \n"}\n'
            f'Суббота: \n\n{schedule.Saturday if schedule.Saturday else " Пар нет \n"}\n'
            f'Ваша учебная группа: {await rq.get_student_group(message.from_user.id)}'
        )
    else:
        schedule = await rq.get_schedule_for_certain_teacher(message.from_user.id)
        schedule_string = (
            f'Ваше расписание: \n\n'
            f'Понедельник: \n\n{schedule.Monday if schedule.Monday else " Пар нет \n"}\n'
            f'Вторник: \n\n{schedule.Tuesday if schedule.Tuesday else " Пар нет \n"}\n'
            f'Среда: \n\n{schedule.Wednesday if schedule.Wednesday else " Пар нет \n"}\n'
            f'Четверг: \n\n{schedule.Thursday if schedule.Thursday else " Пар нет \n"}\n'
            f'Пятница: \n\n{schedule.Friday if schedule.Friday else " Пар нет \n"}\n'
            f'Суббота: \n\n{schedule.Saturday if schedule.Saturday else " Пар нет \n"}\n'
            f'Ваше ФИО: {await rq.get_teachers_initials(message.from_user.id)}'
        )
    if len(schedule_string) > 4096:
        messages = [schedule_string[i:i+4096] for i in range(0, len(schedule_string), 4096)]
        for msg in messages:
            await message.answer(msg)
    else:
        await message.answer(schedule_string)



async def check_pair_and_send_message(bot: Bot):
    async with async_session() as session:
        today = datetime.now().weekday()
        now = datetime.now().time()
        start_timeFirst = time(9, 15)
        end_timeFirst = time(9, 40)
        start_timeSecond = time(10, 55)
        end_timeSecond = time(11, 20)
        start_timeThird = time(12, 45)
        end_timeThird = time(13, 0)
        start_timeFourth = time(14, 45)
        end_timeFourth = time(23, 50)
        start_timeFifth = time(16, 25)
        end_timeFifth = time(16, 40)
        start_timeSix = time(18, 15)
        end_timeSix = time(18, 30)
        start_timeSeven = time(19, 55)
        end_timeSeven = time(20, 10)
        if today == 6:
            pass
        else:
            schedule_check = await session.execute(select(MainScheduleForTeacher))
            for shed in schedule_check.scalars():
                if today == 0:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Monday is not None) and ('1 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.telegram_id))
                            lesson_name = get_lesson_name(shed.Monday, ['1 пара', '(9:30-11:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит первая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Monday is not None) and ('2 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Monday, ['2 пара', '(11:10-12:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит вторая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Monday is not None) and ('3 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Monday, ['3 пара', '(13:00-14:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит третья пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Monday is not None) and ('4 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Monday, ['4 пара', '(15:00-16:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит четвертая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Monday is not None) and ('5 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Monday, ['5 пара', '(16:40-18:10)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит пятая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Monday is not None) and ('6 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Monday, ['6 пара', '(18:30-20:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит шестая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Monday is not None) and ('7 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Monday, ['7 пара', '(20:10-21:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит седьмая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 1:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Tuesday is not None) and ('1 пара' in shed.Tuesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Tuesday, ['1 пара', '(9:30-11:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит первая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Tuesday is not None) and ('2 пара' in shed.Tuesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Tuesday, ['2 пара', '(11:10-12:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит вторая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Tuesday is not None) and ('3 пара' in shed.Tuesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Tuesday, ['3 пара', '(13:00-14:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит третья пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Tuesday is not None) and ('4 пара' in shed.Tuesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Tuesday, ['4 пара', '(15:00-16:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит четвертая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Tuesday is not None) and ('5 пара' in shed.Tuesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Tuesday, ['5 пара', '(16:40-18:10)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит пятая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Tuesday is not None) and ('6 пара' in shed.Tuesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Tuesday, ['6 пара', '(18:30-20:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит шестая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Tuesday is not None) and ('7 пара' in shed.Tuesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Tuesday, ['7 пара', '(20:10-21:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит седьмая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 2:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Wednesday is not None) and ('1 пара' in shed.Wednesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Wednesday, ['1 пара', '(9:30-11:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит первая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Wednesday is not None) and ('2 пара' in shed.Wednesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Wednesday, ['2 пара', '(11:10-12:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит вторая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Wednesday is not None) and ('3 пара' in shed.Wednesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Wednesday, ['3 пара', '(13:00-14:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит третья пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Wednesday is not None) and ('4 пара' in shed.Wednesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Wednesday, ['4 пара', '(15:00-16:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит четвертая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Wednesday is not None) and ('5 пара' in shed.Wednesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Wednesday, ['5 пара', '(16:40-18:10)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит пятая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Wednesday is not None) and ('6 пара' in shed.Wednesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Wednesday, ['6 пара', '(18:30-20:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит шестая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Wednesday is not None) and ('7 пара' in shed.Wednesday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Wednesday, ['7 пара', '(20:10-21:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит седьмая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 3:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Thursday is not None) and ('1 пара' in shed.Thursday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Thursday, ['1 пара', '(9:30-11:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит первая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Thursday is not None) and ('2 пара' in shed.Thursday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Thursday, ['2 пара', '(11:10-12:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит вторая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Thursday is not None) and ('3 пара' in shed.Thursday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Thursday, ['3 пара', '(13:00-14:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит третья пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Thursday is not None) and ('4 пара' in shed.Thursday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Thursday, ['4 пара', '(15:00-16:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит четвертая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Thursday is not None) and ('5 пара' in shed.Thursday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Thursday, ['5 пара', '(16:40-18:10)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит пятая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Thursday is not None) and ('6 пара' in shed.Thursday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Thursday, ['6 пара', '(18:30-20:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит шестая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Thursday is not None) and ('7 пара' in shed.Thursday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Thursday, ['7 пара', '(20:10-21:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит седьмая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 4:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Friday is not None) and ('1 пара' in shed.Friday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Friday, ['1 пара', '(9:30-11:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит первая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Friday is not None) and ('2 пара' in shed.Friday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Friday, ['2 пара', '(11:10-12:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит вторая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Friday is not None) and ('3 пара' in shed.Friday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Friday, ['3 пара', '(13:00-14:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит третья пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Friday is not None) and ('4 пара' in shed.Friday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Friday, ['4 пара', '(15:00-16:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит четвертая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Friday is not None) and ('5 пара' in shed.Friday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Friday, ['5 пара', '(16:40-18:10)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит пятая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Friday is not None) and ('6 пара' in shed.Friday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Friday, ['6 пара', '(18:30-20:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит шестая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Friday is not None) and ('7 пара' in shed.Friday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Friday, ['7 пара', '(20:10-21:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит седьмая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 5:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Saturday is not None) and ('1 пара' in shed.Saturday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Saturday, ['1 пара', '(9:30-11:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит первая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Saturday is not None) and ('2 пара' in shed.Saturday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Saturday, ['2 пара', '(11:10-12:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит вторая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Saturday is not None) and ('3 пара' in shed.Saturday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Saturday, ['3 пара', '(13:00-14:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит третья пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Saturday is not None) and ('4 пара' in shed.Saturday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Saturday, ['4 пара', '(15:00-16:30)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит четвертая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Saturday is not None) and ('5 пара' in shed.Saturday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Saturday, ['5 пара', '(16:40-18:10)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит пятая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Saturday is not None) and ('6 пара' in shed.Saturday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Saturday, ['6 пара', '(18:30-20:00)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит шестая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Saturday is not None) and ('7 пара' in shed.Saturday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            lesson_name = get_lesson_name(shed.Saturday, ['7 пара', '(20:10-21:40)'])
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text=f'По расписанию стоит седьмая пара: {lesson_name}.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)


async def approve_message_for_students(bot: Bot, student: Student, message: str):
    await bot.send_message(chat_id=student.chat_id, text=message)


@router.callback_query(F.data == 'accept_pair')
async def pair_accepted(callback: types.CallbackQuery, bot: Bot):
    async with async_session() as session:
        teacher = await rq.get_teacher(callback.from_user.id)
        schedule = await rq.get_schedule_for_certain_teacher(callback.from_user.id)
        now = datetime.now().time()
        today = datetime.now().weekday()
        today1 = date.fromtimestamp(tim.time())
        current_week = (date(today1.year, today1.month, today1.day).isocalendar()[1]) % 2
        start_timeFirst = time(9, 15)
        end_timeFirst = time(9, 40)
        start_timeSecond = time(10, 55)
        end_timeSecond = time(11, 20)
        start_timeThird = time(12, 45)
        end_timeThird = time(13, 0)
        start_timeFourth = time(14, 45)
        end_timeFourth = time(23, 50)
        start_timeFifth = time(16, 25)
        end_timeFifth = time(16, 40)
        start_timeSix = time(18, 15)
        end_timeSix = time(18, 30)
        start_timeSeven = time(19, 55)
        end_timeSeven = time(20, 10)
        if today == 0:
            schedule_string = schedule.Monday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
        if today == 1:
            schedule_string = schedule.Tuesday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
        if today == 2:
            schedule_string = schedule.Wednesday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
        if today == 3:
            schedule_string = schedule.Thursday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
        if today == 4:
            schedule_string = schedule.Friday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
        if today == 5:
            schedule_string = schedule.Saturday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара состоится")
        await callback.answer('✅')
        await callback.message.answer(
            'Вы подтвердили начало пары.\nРассчитайте время так, чтобы перекличка закончилась до конца пары',
            reply_markup=kb.code_generation)


@router.callback_query(F.data == 'cancel_pair')
async def pair_accepted(callback: types.CallbackQuery, bot: Bot):
    async with async_session() as session:
        teacher = await rq.get_teacher(callback.from_user.id)
        schedule = await rq.get_schedule_for_certain_teacher(callback.from_user.id)
        now = datetime.now().time()
        today = datetime.now().weekday()
        today1 = date.fromtimestamp(tim.time())
        current_week = (date(today1.year, today1.month, today1.day).isocalendar()[1]) % 2
        start_timeFirst = time(9, 15)
        end_timeFirst = time(9, 40)
        start_timeSecond = time(10, 55)
        end_timeSecond = time(11, 20)
        start_timeThird = time(12, 45)
        end_timeThird = time(13, 0)
        start_timeFourth = time(14, 45)
        end_timeFourth = time(23, 50)
        start_timeFifth = time(16, 25)
        end_timeFifth = time(16, 40)
        start_timeSix = time(18, 15)
        end_timeSix = time(18, 30)
        start_timeSeven = time(19, 55)
        end_timeSeven = time(20, 10)
        if today == 0:
            schedule_string = schedule.Monday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
        elif today == 1:
            schedule_string = schedule.Tuesday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
        elif today == 2:
            schedule_string = schedule.Wednesday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
        elif today == 3:
            schedule_string = schedule.Thursday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
        elif today == 4:
            schedule_string = schedule.Friday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
        elif today == 5:
            schedule_string = schedule.Saturday
            students = await session.execute(select(Student))
            if start_timeFirst <= now <= end_timeFirst:
                if current_week == 1:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSecond <= now <= end_timeSecond:
                if current_week == 1:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeThird <= now <= end_timeThird:
                if current_week == 1:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFourth <= now <= end_timeFourth:
                if current_week == 1:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeFifth <= now <= end_timeFifth:
                if current_week == 1:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSix <= now <= end_timeSix:
                if current_week == 1:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
            elif start_timeSeven <= now <= end_timeSeven:
                if current_week == 1:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
                else:
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
                    matches1 = re.findall(pattern, schedule_string)
                    result = []
                    for i in range(len(matches1[0])):
                        if len(matches1[0][i]) > 0:
                            result.append((matches1[0][i]).split(' ; '))
                    groups = []
                    for i in range(len(result)):
                        for j in range(len(result[i])):
                            if result[i][j] not in groups and result[i][j] != '':
                                groups.append(result[i][j])
                    for student in students.scalars():
                        if student.group in groups:
                            await approve_message_for_students(bot, student, "Пара не состоится")
        await callback.answer('❌')
        await callback.message.answer('Вы отменили пару')


@router.callback_query(F.data == 'generate_code')
async def generate_code(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RegisterCode.code)
    await callback.answer('In progress')
    await callback.message.answer('Введите код для подтверждения присутсвия студентами')


async def approve_message_for_students_roll(bot: Bot, student: Student, message: str):
    sent_message = await bot.send_message(chat_id=student.chat_id, text=message, reply_markup=kb.accept_roll)
    return sent_message


async def message_about_end_of_roll_call(bot: Bot, message: types.Message):
    await message.edit_text("Перекличка окончена")


async def close_list(listOfpresent_id, bot: Bot):
    async with async_session() as session:
        listOfpresent = await session.scalar(select(ListOfPresent).filter(ListOfPresent.id == listOfpresent_id))
        listOfpresent.status = 'preclose'
        teacher = await session.scalar(select(Teacher).filter(Teacher.id == listOfpresent.teacher_id))
        students = listOfpresent.students
        await bot.send_message(chat_id=teacher.chat_id, text=f'Перекличка окончена. Список студентов:\n{students}',
                               reply_markup=kb.add_or_delete)
        await session.commit()


@router.message(RegisterCode.code)
async def generate_code_main_state(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(code=message.text)
    await rq.set_data_for_listOfPresent(message.from_user.id, message.text)
    ten_minutes_later = datetime.now() + timedelta(minutes=10)
    time_string = ten_minutes_later.strftime("%H:%M")
    async with async_session() as session:
        teacher = await rq.get_teacher(message.from_user.id)
        schedule = await rq.get_schedule_for_certain_teacher(message.from_user.id)
        listOfpresent = await session.scalar(
            select(ListOfPresent).filter(and_(ListOfPresent.teacher_id == teacher.id, ListOfPresent.status == 'open')))
        now = datetime.now().time()
        students = await session.execute(select(Student))
        pattern = listOfpresent.group
        for student in students.scalars():
            if student.group in pattern:
                sent_message = await approve_message_for_students_roll(bot, student, "Преподаватель начал перекличку")
    await message.reply(
        f'Код успешно создан у студентов есть 10 минут, чтобы пройти перекличку. То есть до {time_string}.')
    await state.clear()
    await asyncio.create_task(asyncio.sleep(15))
    await asyncio.create_task(close_list(listOfpresent.id, bot))
    await asyncio.create_task(message_about_end_of_roll_call(bot, sent_message))


@router.callback_query(F.data == 'accept__roll')
async def generate_code(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RegisterAsPresent.code)
    await callback.answer('Rdy')
    await callback.message.answer('Введите код, чтобы подтвердить присутствие')


@router.message(RegisterAsPresent.code)
async def generate_code_main_state(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text)
    try:
        async with async_session() as session:
            student = await rq.get_student(message.from_user.id)
            open_list_of_presents = await session.scalars(select(ListOfPresent).filter(ListOfPresent.status == 'open'))
            for present in open_list_of_presents:
                if student.group in present.group:
                    if message.text == present.code:
                        await message.answer('Код верен')
                        await message.answer('Теперь необходимо подтвердить геопозицию', reply_markup=kb.share_location)
                        break
                    else:
                        await state.set_state(RegisterAsPresent.code)
                        await message.answer(
                            f'Неверный код доступа. Попробуйте еще раз.', reply_markup=kb.accept_roll)
                        break
            else:
                await message.answer('Перекличка уже закночилась')
            await state.clear()
    except Exception as e:
        await message.answer(f'Произошла ошибка: {str(e)}')


def is_inside_polygon(latitude, longitude, polygon_coords):
    n = len(polygon_coords)
    inside = False
    for i in range(n):
        j = (i + 1) % n
        xi, yi = polygon_coords[i]
        xj, yj = polygon_coords[j]
        intersect = ((yi > longitude) != (yj > longitude)) and (
                latitude < (xj - xi) * (longitude - yi) / (yj - yi) + xi)
        if intersect:
            inside = not inside
    return inside


@router.message(F.location)
async def process_share_location(message: types.location):
    location = message.location
    print(f'Received location: Latitude={location.latitude}, Longitude={location.longitude}')
    async with async_session() as session:
        latitude = location.latitude
        longitude = location.longitude
        Gasta = [(59.858010040200654, 30.326201291447138), (59.858064005983664, 30.329355569248644),
                 (59.85650975627057, 30.329205365543828), (59.85671483505771, 30.326673360233766)]
        Lensa = [(59.8562561044372, 30.329784722691038), (59.85623451695752, 30.33173737085389),
                 (59.85519830140582, 30.329956384067984), (59.855133536858695, 30.33184465921447)]
        BM = [(59.930930489256866, 30.29282265918946), (59.93179203162438, 30.296513378793964),
              (59.92858267235224, 30.295311749155285), (59.93002584560677, 30.298487484628925)]
        student = await rq.get_student(message.from_user.id)
        open_list_of_presents = await session.scalars(select(ListOfPresent).filter(ListOfPresent.status == 'open'))
        # Gasta = [(59.83838293879409, 30.48435492476775), (59.84842554032725, 30.499394938317884),
        #          (59.82435066905143, 30.51281974665993), (59.836967483643015, 30.54097221248025)]
        if is_inside_polygon(latitude, longitude, Gasta):
            for present in open_list_of_presents:
                if student.group in present.group:
                    students = present.students
                    if students:
                        students += f", {student.initials}"
                    else:
                        students = student.initials
                    present.students = students
                    await message.answer('Вы подтвердили свое присутствие', reply_markup=kb.main_buttuns_for_student)
                    await rq.set_new_rating(message.from_user.id)
                    rank = await rq.get_rating_for_current_student(message.from_user.id)
                    await message.reply(f'Вам начисленно 100 рейтинговых очков, сейчас у Вас {rank.mmr}', reply_markup=kb.main_buttuns_for_student)
                    await session.commit()
                    break
        elif is_inside_polygon(latitude, longitude, Lensa):
            for present in open_list_of_presents:
                if student.group in present.group:
                    students = present.students
                    if students:
                        students += f", {student.initials}"
                    else:
                        students = student.initials
                    present.students = students
                    await message.answer('Вы подтвердили свое присутствие', reply_markup=kb.main_buttuns_for_student)
                    await rq.set_new_rating(message.from_user.id)
                    rank = await rq.get_rating_for_current_student(message.from_user.id)
                    await message.reply(f'Вам начисленно 100 рейтинговых очков, сейчас у Вас {rank.mmr}', reply_markup=kb.main_buttuns_for_student)
                    await session.commit()
                    break
        elif is_inside_polygon(latitude, longitude, BM):
            for present in open_list_of_presents:
                if student.group in present.group:
                    students = present.students
                    if students:
                        students += f", {student.initials}"
                    else:
                        students = student.initials
                    present.students = students
                    await message.answer('Вы подтвердили свое присутствие', reply_markup=kb.main_buttuns_for_student)
                    await rq.set_new_rating(message.from_user.id)
                    rank = await rq.get_rating_for_current_student(message.from_user.id)
                    await message.reply(f'Вам начисленно 100 рейтинговых очков, сейчас у Вас {rank.mmr}', reply_markup=kb.main_buttuns_for_student)
                    await session.commit()
                    break
        else:
            await message.answer('Вы находитесь не в ГУАПЕ', reply_markup=kb.main_buttuns_for_student)


@router.callback_query(F.data == 'is_right')
async def accept_list_of_present(callback: types.CallbackQuery):
    async with async_session() as session:
        teacher = await rq.get_teacher(callback.from_user.id)
        listOfpresent = await session.scalar(select(ListOfPresent).filter(
            and_(ListOfPresent.teacher_id == teacher.id, ListOfPresent.status == 'preclose')))
        listOfpresent.status = 'close'
        await callback.message.answer(
            f'Перекличка закрыта, финальная версия списка присутсвущих:\n{listOfpresent.students}')
        await session.commit()


@router.callback_query(F.data == 'add')
async def accept_list_of_present(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(f'Введите ФИО студентов которых хотите добавить')
    await state.set_state(AddStudents.students)


@router.message(AddStudents.students)
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(students=message.text)
    async with async_session() as session:
        teacher = await rq.get_teacher(message.from_user.id)
        listOfpresent = await session.scalar(select(ListOfPresent).filter(
            and_(ListOfPresent.teacher_id == teacher.id, ListOfPresent.status == 'preclose')))
        students = listOfpresent.students
        if students:
            students += f", {message.text}"
        else:
            students = message.text
        listOfpresent.students = students
        await message.answer(
            f'Перекличка закрыта, финальная версия списка присутсвущих:\n{listOfpresent.students}', reply_markup=kb.add_or_delete)
        await session.commit()

@router.message(F.text == '✅Мое посещение')
async def check_lessons(message: types.Message):
    await message.answer('Выберите нужный Вам формат', reply_markup=kb.short_and_full_lessons)

@router.message(F.text == '✅Посещение')
async def check_lesson_for_teacher(message: types.Message):
    teacher = await rq.get_teachers_initials(message.from_user.id)
    await message.answer('Выберите интересующую вас дату:', reply_markup=await kb.data_pair(teacher))

@router.callback_query(F.data.startswith('pair_'))
async def current_data_pair(callback: types.CallbackQuery):
    teacher = await rq.get_teachers_initials(callback.from_user.id)
    await callback.message.edit_text('Выберите интересующую вас пару',
                                     reply_markup=await kb.number_pair(callback.data.split('_')[1], teacher))

@router.callback_query(F.data.startswith('numPair_'))
async def current_info_for_pair(callback: types.CallbackQuery):
    info = await rq.get_info_for_pair(int(callback.data.split('_')[1]))
    result = f'{info.Pair}\nГруппы: {info.group}:\n{info.students}'
    await callback.message.answer(result, reply_markup=kb.main_buttuns_for_teachers)

@router.callback_query(F.data == 'full_lessons')
async def check_full_lessons(callback: types.CallbackQuery):
    student = await rq.get_student_initials(callback.from_user.id)
    group = await rq.get_student_group(callback.from_user.id)
    lessons = await rq.check_lessons(group, student)
    result = 'Ваши посещения:\n'
    for lesson in lessons:
        result += f'{lesson[0]} {lesson[1]}\n'
    await callback.answer('Ваши посещения')
    await callback.message.answer(result)
    await callback.message.reply('Если вы не увидели посещенную вами пару, то списки посещения обновлются каждый день в 22:00',
                         reply_markup=kb.main_buttuns_for_student)

@router.callback_query(F.data == 'short_lessons')
async def check_short_lessons(callback: types.CallbackQuery):
    student = await rq.get_student_initials(callback.from_user.id)
    group = await rq.get_student_group(callback.from_user.id)
    lessons = await rq.check_lessons(group, student)
    result_tmp = {}
    for lesson in lessons:
        result_tmp[lesson[1]] = result_tmp.get(lesson[1], 0) + 1
    result = 'Ваши посещения:\n'
    for lesson, count in result_tmp.items():
        result += f'{lesson}: {count}\n'
    await callback.answer('Ваши посещения')
    await callback.message.answer(result)
    await callback.message.reply('Если вы не увидели посещенную вами пару, то списки посещения обновлются каждый день в 22:00',
                         reply_markup=kb.main_buttuns_for_student)

@router.message(F.text == '🏆Рейтинг')
async def check_lessons(message: types.Message):
    async with async_session() as session:
        ranks = await session.scalars(select(Rang).order_by(Rang.mmr.desc()).limit(20))
        ranked_list = []
        for rank in ranks:
            rankOnStep = [rank.student_name, rank.mmr]
            ranked_list.append(rankOnStep)
            print(f"Rank: {rank.student_name}, MMR: {rank.mmr}")
        ranked_string = '\n'.join([f'{i + 1}. {rank[0]} - {rank[1]}' for i, rank in enumerate(ranked_list)])
        await message.answer(f'Топ 15:\n{ranked_string}')


@router.message(F.text == '😎Мое место')
async def check_lessons(message: types.Message):
    rank = await rq.get_rating_for_current_student(message.from_user.id)
    pos = await rq.get_rating_for_current_student_personal(message.from_user.id)
    await message.answer(f'Ваше место в рейтинге:\n{pos}  {rank.student_name}  {rank.mmr}')








