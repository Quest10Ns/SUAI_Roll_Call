import asyncio
import os
import time
import logging
from datetime import datetime, time, date
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
from app.database.models import async_session
from app.database.models import User, Teacher, Student, ScheduleForStudent, ScheduleForTeacher, MainScheduleForTeacher
from sqlalchemy import select, update, delete

router = Router()

attempts = {}

class RegisterForTeachers(StatesGroup):
    initials = State()
    departmend = State()
    verification_code = State()


class RegisterForStudents(StatesGroup):
    initials = State()
    group = State()


class RegisterUsers(StatesGroup):
    status = State()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    if (await rq.get_user_status(message.from_user.id) and (
            ((await rq.get_student_group(message.from_user.id) is not None) and (
                    (await rq.get_student_initials(message.from_user.id) is not None)) or (
                    (await rq.get_teachers_initials(message.from_user.id) is not None) and (await rq.get_teachers_department(message.from_user.id) is not None))))):
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
    current_time = time.time()

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
                await message.answer(f'Неверный код доступа. Попробуйте еще раз. Осталось попыток: {3 - attempts[user_id]["count"]}',
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
            await rq.set_student_initials_for_students(message.from_user.id, message.text)
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
            cur_group = await rq.get_right_gpoup(message.text)  # Добавляем await здесь
            if not cur_group:
                await message.answer(f'Такой группы не существует. Попробуйте еще раз', reply_markup=kb.main_buttuns_for_student)
            else:
                await state.update_data(group=message.text)
                await rq.set_group_for_student(message.from_user.id, message.text)
                data = await state.get_data()
                await message.answer(
                    f'Вы успешно зарегистрированы как студент. \n Ваше ФИО: {data["initials"]} \n Ваша учебная группа: {data["group"]}',
                    reply_markup=kb.edit_button)
                await state.clear()
        else:
            cur_group = await rq.get_right_gpoup(message.text)  # Добавляем await здесь
            if not cur_group:
                await message.answer(f'Такой группы не существует. Попробуйте еще раз', reply_markup=kb.main_buttuns_for_student)
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
        await callback.message.edit_text(f'Ваши данные: \n Ваш статус: Студент \n Ваше ФИО: {await rq.get_student_initials(callback.from_user.id)} \n Ваша учебная группа: {await rq.get_student_group(callback.from_user.id)}',
                                         reply_markup=kb.edit_main_buttons)
    else:
        await callback.message.edit_text(
            f'Ваши данные: \n Ваш статус: Преподаватель \n Ваше ФИО: {await rq.get_teachers_initials(callback.from_user.id)} \n Кафедра: {await rq.get_teachers_department(callback.from_user.id)}',
            reply_markup=kb.edit_main_buttons)

@router.message(F.text == '📅Расписание')
async def main_schedule(message: types.Message):
    if await rq.get_user_status(message.from_user.id) == 'Студент':
        schedule = await rq.get_schedule(message.from_user.id)
        await message.answer(
            f'Ваше расписание: \n\n'
            f'Понедельник: \n\n{ schedule.Monday if schedule.Monday else " Пар нет \n"}\n'
            f'Вторник: \n\n{ schedule.Tuesday if schedule.Tuesday else " Пар нет \n"}\n'
            f'Среда: \n\n{schedule.Wednesday if schedule.Wednesday else " Пар нет \n"}\n'
            f'Четверг: \n\n{ schedule.Thursday if schedule.Thursday else " Пар нет \n"}\n'
            f'Пятница: \n\n{ schedule.Friday if schedule.Friday else " Пар нет \n"}\n'
            f'Суббота: \n\n{ schedule.Saturday if schedule.Saturday else " Пар нет \n"}\n'
            f'Ваша учебная группа: {await rq.get_student_group(message.from_user.id)}'
        )
    else:
        schedule = await rq.get_schedule_for_certain_teacher(message.from_user.id)
        await message.answer(
            f'Ваше расписание: \n\n'
            f'Понедельник: \n\n{ schedule.Monday if schedule.Monday else " Пар нет \n"}\n'
            f'Вторник: \n\n{ schedule.Tuesday if schedule.Tuesday else " Пар нет \n"}\n'
            f'Среда: \n\n{schedule.Wednesday if schedule.Wednesday else " Пар нет \n"}\n'
            f'Четверг: \n\n{ schedule.Thursday if schedule.Thursday else " Пар нет \n"}\n'
            f'Пятница: \n\n{ schedule.Friday if schedule.Friday else " Пар нет \n"}\n'
            f'Суббота: \n\n{ schedule.Saturday if schedule.Saturday else " Пар нет \n"}\n'
            f'Ваше ФИО: {await rq.get_teachers_initials(message.from_user.id)}')

async def check_pair_and_send_message(bot: Bot):
    async with async_session() as session:
        today = datetime.now().weekday()
        now = datetime.now().time()
        start_timeFirst = time(9, 15)
        end_timeFirst = time(10, 0)
        start_timeSecond = time(10, 55)
        end_timeSecond = time(11, 20)
        start_timeThird = time(12, 45)
        end_timeThird = time(13, 0)
        start_timeFourth = time(14, 45)
        end_timeFourth = time(15, 0)
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
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит первая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Monday is not None) and ('2 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит вторая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Monday is not None) and ('3 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит третья пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Monday is not None) and ('4 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит четвертая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Monday is not None) and ('5 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит пятая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Monday is not None) and ('6 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит шестая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Monday is not None) and ('7 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит седьмая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 1:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Tuesday is not None) and ('1 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит первая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Tuesday is not None) and ('2 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит вторая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Tuesday is not None) and ('3 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит третья пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Tuesday is not None) and ('4 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит четвертая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Tuesday is not None) and ('5 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит пятая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Tuesday is not None) and ('6 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит шестая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Tuesday is not None) and ('7 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит седьмая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 2:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Wednesday is not None) and ('1 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит первая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Wednesday is not None) and ('2 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит вторая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Wednesday is not None) and ('3 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит третья пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Wednesday is not None) and ('4 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит четвертая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Wednesday is not None) and ('5 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит пятая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Wednesday is not None) and ('6 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит шестая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Wednesday is not None) and ('7 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит седьмая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 3:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Thursday is not None) and ('1 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит первая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Thursday is not None) and ('2 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит вторая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Thursday is not None) and ('3 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит третья пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Thursday is not None) and ('4 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит четвертая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Thursday is not None) and ('5 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит пятая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Thursday is not None) and ('6 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит шестая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Thursday is not None) and ('7 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит седьмая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 4:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Friday is not None) and ('1 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит первая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Friday is not None) and ('2 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит вторая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Friday is not None) and ('3 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит третья пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Friday is not None) and ('4 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит четвертая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Friday is not None) and ('5 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит пятая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Friday is not None) and ('6 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит шестая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Friday is not None) and ('7 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит седьмая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                elif today == 5:
                    if start_timeFirst <= now <= end_timeFirst:
                        if (shed.Saturday is not None) and ('1 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит первая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSecond <= now <= end_timeSecond:
                        if (shed.Saturday is not None) and ('2 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит вторая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeThird <= now <= end_timeThird:
                        if (shed.Saturday is not None) and ('3 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит третья пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFourth <= now <= end_timeFourth:
                        if (shed.Saturday is not None) and ('4 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит четвертая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeFifth <= now <= end_timeFifth:
                        if (shed.Saturday is not None) and ('5 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит пятая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSix <= now <= end_timeSix:
                        if (shed.Saturday is not None) and ('6 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит шестая пара.\n Она будет?',
                                                   reply_markup=kb.accept_pair_for_teacher)
                    elif start_timeSeven <= now <= end_timeSeven:
                        if (shed.Saturday is not None) and ('7 пара' in shed.Monday):
                            teacher = await session.scalar(select(Teacher).filter(Teacher.user_id == shed.teacher_id))
                            await bot.send_message(chat_id=teacher.chat_id,
                                                   text='По расписанию стоит седьмая пара.\n Она будет?',
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
        today1 = date.fromtimestamp(time.time())
        current_week = (date(today1.year, today1.month, today1.day).isocalendar()[1]) % 2
        start_timeFirst = time(9, 15)
        end_timeFirst = time(10, 0)
        start_timeSecond = time(10, 55)
        end_timeSecond = time(11, 20)
        start_timeThird = time(12, 45)
        end_timeThird = time(13, 0)
        start_timeFourth = time(14, 45)
        end_timeFourth = time(15, 0)
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
        await callback.answer('Вы подтвердили начало пары', reply_markup = kb.code_generation)
        await callback.message.answer('✅')


@router.callback_query(F.data == 'cancel_pair')
async def pair_accepted(callback: types.CallbackQuery, bot: Bot):
    async with async_session() as session:
        teacher = await rq.get_teacher(callback.from_user.id)
        schedule = await rq.get_schedule_for_certain_teacher(callback.from_user.id)
        now = datetime.now().time()
        today = datetime.now().weekday()
        today1 = date.fromtimestamp(time.time())
        current_week = (date(today1.year, today1.month, today1.day).isocalendar()[1]) % 2
        start_timeFirst = time(9, 15)
        end_timeFirst = time(10, 0)
        start_timeSecond = time(10, 55)
        end_timeSecond = time(11, 20)
        start_timeThird = time(12, 45)
        end_timeThird = time(13, 0)
        start_timeFourth = time(14, 45)
        end_timeFourth = time(15, 0)
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|1 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|1 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"1 пара \(9:30–11:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара \(9:30–11:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|1 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|2 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|2 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"2 пара \(11:10–12:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара \(11:10–12:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|2 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|3 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|3 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"3 пара \(13:00–14:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара \(13:00–14:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|3 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|4 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|4 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"4 пара \(15:00–16:30\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара \(15:00–16:30\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|4 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|5 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|5 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"5 пара \(16:40–18:10\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара \(16:40–18:10\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|5 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|6 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|6 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"6 пара \(18:30–20:00\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара \(18:30–20:00\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|6 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) ▼|7 пара .* ▲.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*) \n|7 пара .* ▲.* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*) \n"
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
                    pattern = r"7 пара \(20:10–21:40\) [ПРЛ]* .*?Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара \(20:10–21:40\) [ПРЛ]* .*?Группы: (([A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼.* Группа: ([A-ZА-Я]?\d+[A-ZА-Я]*)|7 пара .* ▼ .* Группы: ((?:[A-ZА-Я]?\d+[A-ZА-Я]* ; )*[A-ZА-Я]?\d+[A-ZА-Я]*)"
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
        await callback.answer('Вы отменили пару', reply_markup=kb.code_generation)
        await callback.message.answer('❌')



@router.callback_query(F.data == 'generate_code')
async def generate_code(callback: types.CallbackQuery):
    teacher = await rq.get_teacher(callback.from_user.id)
    schedule = await rq.get_schedule_for_certain_teacher(callback.from_user.id)
    await callback.answer('In progress')
    await callback.message.answer('✅')
