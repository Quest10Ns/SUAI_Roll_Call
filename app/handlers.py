import asyncio
from aiogram import types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import app.keyboads as kb

router = Router()


class RegisterForTeachers(StatesGroup):
    initials = State()
    verification_code = State()


class RegisterForStudents(StatesGroup):
    initials = State()
    group = State()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer('Приветственный текст', reply_markup=kb.main)


@router.message(Command('info'))
async def cmd_info(message: types.Message):
    await message.answer('Im Helping')


@router.message(F.text == 'Преподаватель')
async def teacher(message: types.Message, state: FSMContext):
    await message.reply('Отлично, теперь необходима пройти регистрацию и подтвердить, что вы преподаватель')
    await state.set_state(RegisterForTeachers.initials)
    await message.answer('Введите ваше имя, фамилию и отчество')


@router.message(RegisterForTeachers.initials)
async def register_name_for_teacher(message: types.Message, state: FSMContext):
    await state.update_data(initials=message.text)
    await state.set_state(RegisterForTeachers.verification_code)
    await message.answer('Введите код для подтверждения статуса преподавателя')


@router.message(RegisterForTeachers.verification_code)
async def register_verification_code(message: types.Message, state: FSMContext):
    await state.update_data(verification_code=message.text)
    data = await state.get_data()
    await message.answer(
        f'Вы успешно зарегистрированы как преподаватель. \n Ваше ФИО: {data["initials"]} \n Код подтверждения: {data["verification_code"]}')
    await state.clear()


@router.message(F.text == 'Студент')
async def student(message: types.Message, state: FSMContext):
    await message.reply('Отлично, теперь необходима пройти регистрацию')
    await state.set_state(RegisterForStudents.initials)
    await message.answer('Введите ваше имя, фамилию и отчество')


@router.message(RegisterForStudents.initials)
async def register_name_for_student(message: types.Message, state: FSMContext):
    await state.update_data(initials=message.text)
    await state.set_state(RegisterForStudents.group)
    await message.answer('Введите вашу учебную группу')


@router.message(RegisterForStudents.group)
async def register_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    data = await state.get_data()
    await message.answer(
        f'Вы успешно зарегистрированы как студент. \n Ваше ФИО: {data["initials"]} \n Ваша учебная группа: {data["group"]}')
    await state.clear()
