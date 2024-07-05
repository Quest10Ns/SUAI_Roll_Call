import asyncio
from aiogram import types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import app.keyboads as kb
import app.database.requests as rq

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
    await rq.set_user(message.from_user.id)
    await state.set_state(RegisterUsers.status)
    await message.answer('Добро пожаловать в бота, который проверяет посещения пар в ГУАПе', reply_markup=kb.main)



@router.message(Command('info'))
async def cmd_info(message: types.Message):
    await message.answer('Im Helping')


@router.message(RegisterUsers.status)
async def register_user(message: types.Message, state: FSMContext):
    if message.text == 'Преподаватель':
        await message.reply('Отлично, теперь необходима пройти регистрацию и подтвердить, что вы преподаватель')
        await state.set_state(RegisterForTeachers.initials)
        await rq.set_user_status(message.from_user.id, message.text)
        await message.answer('Введите ваше имя, фамилию и отчество')
    elif message.text == 'Студент':
        await message.reply('Отлично, теперь необходима пройти регистрацию')
        await state.set_state(RegisterForStudents.initials)
        await rq.set_user_status(message.from_user.id, message.text)
        await message.answer('Введите ваше имя, фамилию и отчество')

@router.message(RegisterForTeachers.initials)
async def register_name_for_teacher(message: types.Message, state: FSMContext):
    await state.update_data(initials=message.text)
    await rq.set_student_initials_for_teachers(message.from_user.id, message.text)
    await state.set_state(RegisterForTeachers.departmend)
    await message.answer('Введите вашу кафедру')

@router.message(RegisterForTeachers.departmend)
async def register_departmend_for_teachers(message: types.Message, state: FSMContext):
    await state.update_data(departmend=message.text)
    await rq.set_departmend_for_teachers(message.from_user.id, message.text)
    await state.set_state(RegisterForTeachers.verification_code)
    await message.answer('Введите код для подтверждения статуса преподавателя')

@router.message(RegisterForTeachers.verification_code)
async def register_verification_code(message: types.Message, state: FSMContext):
    await state.update_data(verification_code=message.text)
    data = await state.get_data()
    await message.answer(
        f'Вы успешно зарегистрированы как преподаватель. \n Ваше ФИО: {data["initials"]} \n Кафедра: {data["departmend"]} \n Код подтверждения: {data["verification_code"]}')
    await state.clear()


@router.message(RegisterForStudents.initials)
async def register_name_for_student(message: types.Message, state: FSMContext):
    await state.update_data(initials=message.text)
    await rq.set_student_initials_for_students(message.from_user.id, message.text)
    await state.set_state(RegisterForStudents.group)
    await message.answer('Введите вашу учебную группу')


@router.message(RegisterForStudents.group)
async def register_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    await rq.set_group_for_student(message.from_user.id, message.text)
    data = await state.get_data()
    await message.answer(
        f'Вы успешно зарегистрированы как студент. \n Ваше ФИО: {data["initials"]} \n Ваша учебная группа: {data["group"]}')
    await state.clear()
