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
        await message.answer('Введите ваше имя, фамилию и отчество', reply_markup=kb.back)
        await state.set_state(RegisterForTeachers.initials)
        await rq.set_user_status(message.from_user.id, message.text)

    elif message.text == 'Студент':
        await message.reply('Отлично, теперь необходима пройти регистрацию')
        await message.answer('Введите ваше имя, фамилию и отчество', reply_markup=kb.back)
        await state.set_state(RegisterForStudents.initials)
        await rq.set_user_status(message.from_user.id, message.text)

    else:
        await message.reply('Пожалуйста, выберите правильный статус: Преподаватель или Студент', reply_markup=kb.main)



@router.message(RegisterForTeachers.initials)
async def register_name_for_teacher(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:', reply_markup=kb.main)
    else:
        await state.update_data(initials=message.text)
        await state.set_state(RegisterForTeachers.verification_code)
        await message.answer('Введите код для подтверждения статуса преподавателя', reply_markup=kb.back)


@router.message(RegisterForTeachers.verification_code)
async def register_verification_code(message: types.Message, state: FSMContext):
    await state.update_data(verification_code=message.text)
    data = await state.get_data()
    await message.answer(
        f'Вы успешно зарегистрированы как преподаватель. \n Ваше ФИО: {data["initials"]} \n '
        f'Код подтверждения: {data["verification_code"]}', reply_markup=kb.info_about_me)
    await state.clear()


@router.message(RegisterForStudents.initials)
async def register_name_for_student(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await state.set_state(RegisterUsers.status)
        await message.answer('Вы вернулись к выбору статуса. Пожалуйста, выберите вашу роль:', reply_markup=kb.main)
    else:
        await state.update_data(initials=message.text)
        await state.set_state(RegisterForStudents.group)
        await message.answer('Введите вашу учебную группу')


@router.message(RegisterForStudents.group)
async def register_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    data = await state.get_data()
    await message.answer(
        f'Вы успешно зарегистрированы как студент. \n Ваше ФИО: {data["initials"]} \n '
        f'Ваша учебная группа: {data["group"]}', reply_markup=kb.info_about_me)
    await state.clear()

