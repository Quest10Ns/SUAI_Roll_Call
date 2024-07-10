import asyncio
import os
from aiogram import types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import app.keyboads as kb
import app.database.requests as rq
from dotenv import load_dotenv

router = Router()


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
    if (await rq.get_user_status(message.from_user.id) and (await rq.get_student(message.from_user.id) or await rq.get_teacher(message.from_user.id))):
        if await rq.get_student(message.from_user.id):
            await message.answer('И снова здравствуйте', reply_markup=kb.main_buttuns_for_student)
        else:
            await message.answer('И снова здравствуйте', reply_markup=kb.main_buttuns_for_teachers)
    else:
        await rq.set_user(message.from_user.id)
        await state.set_state(RegisterUsers.status)
        await message.answer('Добро пожаловать в бота, который проверяет посещения пар в ГУАПе',
                             reply_markup=kb.start_buttons)


@router.message(F.text == 'Неверный код доступа. Видимо Вы не преподаватель')
async def cmd_start(message: types.Message, state: FSMContext):
    await rq.set_user(message.from_user.id)
    await state.set_state(RegisterUsers.status)
    await message.answer('Добро пожаловать в бота, который проверяет посещения пар в ГУАПе', reply_markup=kb.start_buttons)


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
        await message.reply('Пожалуйста, выберите правильный статус: Преподаватель или Студент', reply_markup=kb.start_buttons)


@router.message(RegisterForTeachers.initials)
async def register_name_for_teacher(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:', reply_markup=kb.start_buttons)
    else:
        if not await rq.get_teachers_initials(message.from_user.id):
            await state.update_data(initials=message.text)
            await rq.set_student_initials_for_teachers(message.from_user.id, message.text)
            await state.set_state(RegisterForTeachers.departmend)
            await message.answer('Введите вашу кафедру', reply_markup=kb.back)
        else:
            await state.update_data(initials=message.text)
            await rq.set_student_initials_for_teachers(message.from_user.id, message.text)
            await state.clear()
            if await rq.get_teachers_initials(message.from_user.id) == message.text:
                await message.answer(f'ФИО успешно изменено на {message.text}', reply_markup=kb.main_buttuns_for_teachers)
            else:
                await message.answer(f'Изменить не удалось', reply_markup=kb.main_buttuns_for_teachers)


@router.message(RegisterForTeachers.departmend)
async def register_departmend_for_teachers(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:', reply_markup=kb.start_buttons)
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
                await message.answer(f'Кафедра успешно изменена на {message.text}', reply_markup=kb.main_buttuns_for_teachers)
            else:
                await message.answer(f'Изменить не удалось', reply_markup=kb.main_buttuns_for_teachers)


@router.message(RegisterForTeachers.verification_code)
async def register_verification_code(message: types.Message, state: FSMContext):
    load_dotenv()
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:', reply_markup=kb.start_buttons)
    else:
        if message.text == os.getenv('TEACHERS_PASSWORD'):
            await state.update_data(verification_code=message.text)
            data = await state.get_data()
            await message.answer(
                f'Вы успешно зарегистрированы как преподаватель. \n Ваше ФИО: {data["initials"]} \n Кафедра: {data["departmend"]}',
                reply_markup=kb.edit_button)
            await state.clear()
        else:
            await state.set_state(RegisterForTeachers.verification_code)
            await message.answer('Неверный код доступа. Попробуйте еще раз', reply_markup=kb.back)


@router.message(RegisterForStudents.initials)
async def register_name_for_student(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:', reply_markup=kb.start_buttons)
    else:
        if not await rq.get_student_initials(message.from_user.id):
            await state.update_data(initials=message.text)
            await rq.set_student_initials_for_students(message.from_user.id, message.text)
            await state.set_state(RegisterForStudents.group)
            await message.answer('Введите вашу учебную группу', reply_markup=kb.back)
        else:
            await state.update_data(initials=message.text)
            await rq.set_student_initials_for_students(message.from_user.id, message.text)
            await state.clear()
            if await rq.get_student_initials(message.from_user.id) == message.text:
                await message.answer(f'ФИО успешно изменено на {message.text}',reply_markup=kb.main_buttuns_for_student)
            else:
                await message.answer(f'Изменить не удалось', reply_markup=kb.main_buttuns_for_student)


@router.message(RegisterForStudents.group)
async def register_group(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:', reply_markup=kb.start_buttons)
    else:
        if not await rq.get_student_group(message.from_user.id):
            await state.update_data(group=message.text)
            await rq.set_group_for_student(message.from_user.id, message.text)
            data = await state.get_data()
            await message.answer(
                f'Вы успешно зарегистрированы как студент. \n Ваше ФИО: {data["initials"]} \n Ваша учебная группа: {data["group"]}',
                reply_markup=kb.edit_button)
            await state.clear()
        else:
            await state.update_data(group=message.text)
            await rq.set_group_for_student(message.from_user.id, message.text)
            await state.clear()
            if await rq.get_student_group(message.from_user.id) == message.text:
                await message.answer(f'Группа успешно изменена на {message.text}', reply_markup=kb.main_buttuns_for_student)
            else:
                await message.answer(f'Изменить не удалось', reply_markup=kb.main_buttuns_for_student)

@router.callback_query(F.data == 'data_is_right')
async def edit_personal_data(callback: types.CallbackQuery):
    if await rq.get_user_status(callback.from_user.id) == 'Студент':
        await callback.message.answer('Отлично, регистрация успешно пройдена!', reply_markup=kb.main_buttuns_for_student)
    else:
        await callback.message.answer('Отлично, регистрация успешно пройдена!', reply_markup=kb.main_buttuns_for_teachers)
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
    await callback.message.answer('Введите новые ФИО', reply_markup=kb.space)
    await callback.answer()


@router.callback_query(F.data == 'edit_students_initials')
async def edit_initials_for_student_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RegisterForStudents.initials)
    await callback.message.answer('Введите новые ФИО', reply_markup=kb.space)
    await callback.answer()


@router.callback_query(F.data == 'edit_group')
async def edit_group(callback: types.CallbackQuery, state: FSMContext):
    await  state.set_state(RegisterForStudents.group)
    await callback.message.answer('Введите новую группу', reply_markup=kb.space)
    await callback.answer()


@router.callback_query(F.data == 'edit_teachers_department')
async def edit_group(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RegisterForTeachers.departmend)
    await callback.message.answer('Введите новую группу', reply_markup=kb.space)
    await callback.answer()
