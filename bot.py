import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from config import ADMIN_IDS, TOKEN, ADMIN_GROUP_ID, INVITE_LINK
from database import (
    init_db, save_form, get_all_forms, get_user_form, 
    delete_form, delete_user_form, update_form_status,
    ban_user, is_banned, unban_user, update_form_field,
    get_admin_message_id, update_admin_message_id
)

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher()

# -------------------------------

async def update_admin_form_message(user_id):
    """Обновить сообщение с анкетой в админ-чате"""
    form = get_user_form(user_id)
    if not form:
        return
    
    # Проверяем количество полей и распаковываем соответственно
    if len(form) == 13:  # Новая структура
        form_id, user_id_db, name, tg_username, mc_nick, call_as, age, extra, status, created_at, edited_at, is_edited, admin_message_id = form
    else:  # Старая структура
        logging.warning("Старая структура БД - пересоздайте базу данных!")
        return
    
    if not admin_message_id:
        return
    
    edited_mark = " ✏️ <i>(Отредактирована)</i>" if is_edited else ""
    
    text = (
        f"📝 <b>Новая анкета!</b>{edited_mark}\n\n"
        f"<b>🆔 ID анкеты:</b> {form_id}\n"
        f"<b>👤 Имя:</b> {name}\n"
        f"<b>📱 Telegram:</b> @{tg_username}\n"
        f"<b>🎮 Minecraft:</b> {mc_nick}\n"
        f"<b>💬 Обращение:</b> {call_as}\n"
        f"<b>🎂 Возраст:</b> {age}\n"
        f"<b>📝 Дополнительно:</b>\n{extra}\n\n"
        f"<i>🔑 User ID:</i> <code>{user_id}</code>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{user_id}_{form_id}"),
            InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_{user_id}_{form_id}")
        ],
        [
            InlineKeyboardButton(text="💬 Связаться", callback_data=f"contact_{user_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{form_id}_{user_id}")
        ]
    ])
    
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=ADMIN_GROUP_ID,
            message_id=admin_message_id,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Не удалось обновить сообщение в админ-чате: {e}")

# -------------------------------

def get_main_menu(user_id):
    """Получить главное меню с учётом наличия анкеты"""
    form = get_user_form(user_id)
    
    if form:
        keyboard = [
            [KeyboardButton(text="📋 Моя анкета")],
            [KeyboardButton(text="✏️ Редактировать анкету"), KeyboardButton(text="🗑 Удалить анкету")],
            [KeyboardButton(text="📨 Связь с админом")]
        ]
    else:
        keyboard = [
            [KeyboardButton(text="📋 Заполнить анкету")],
            [KeyboardButton(text="📨 Связь с админом")]
        ]
    
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=keyboard)

# -------------------------------

class FormState(StatesGroup):
    name = State()
    tg_username = State()
    mc_nick = State()
    call_as = State()
    age = State()
    extra = State()

class EditFormState(StatesGroup):
    editing_name = State()
    editing_tg_username = State()
    editing_mc_nick = State()
    editing_call_as = State()
    editing_age = State()
    editing_extra = State()

class ContactAdmin(StatesGroup):
    waiting_for_message = State()

class AdminContact(StatesGroup):
    waiting_for_admin_message = State()

# -------------------------------

@dp.message(Command("start"))
async def start(message: types.Message):
    # Проверка на бан
    if is_banned(message.from_user.id):
        await message.answer("🚫 Вы заблокированы в этом боте.")
        return
    
    menu = get_main_menu(message.from_user.id)
    await message.answer("👋 Привет! Я анкетолог.\n\nВыберите действие:", reply_markup=menu)

# ------------------------------- АНКЕТА -------------------------------

@dp.message(lambda m: m.text == "📋 Заполнить анкету")
async def form_start(message: types.Message, state: FSMContext):
    # Проверка на бан
    if is_banned(message.from_user.id):
        await message.answer("🚫 Вы заблокированы в этом боте.")
        return
    
    # Проверка, есть ли уже анкета
    form = get_user_form(message.from_user.id)
    if form:
        await message.answer("❗️ У вас уже есть анкета! Используйте кнопки для редактирования или удаления.")
        return
    
    await message.answer("📝 Начинаем заполнение анкеты!\n\n❓ <b>Как тебя зовут?</b>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(FormState.name)

@dp.message(FormState.name)
async def form_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("❓ <b>Твой Telegram username?</b>", parse_mode="HTML")
    await state.set_state(FormState.tg_username)

@dp.message(FormState.tg_username)
async def form_tg(message: types.Message, state: FSMContext):
    await state.update_data(tg_username=message.text)
    await message.answer("❓ <b>Твой ник в Minecraft?</b>", parse_mode="HTML")
    await state.set_state(FormState.mc_nick)

@dp.message(FormState.mc_nick)
async def form_mc(message: types.Message, state: FSMContext):
    await state.update_data(mc_nick=message.text)
    await message.answer("❓ <b>Как к тебе обращаться?</b>", parse_mode="HTML")
    await state.set_state(FormState.call_as)

@dp.message(FormState.call_as)
async def form_call_as(message: types.Message, state: FSMContext):
    await state.update_data(call_as=message.text)
    await message.answer("❓ <b>Сколько тебе лет?</b>", parse_mode="HTML")
    await state.set_state(FormState.age)

@dp.message(FormState.age)
async def form_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("❓ <b>Добавь что-то от себя (расскажи о себе):</b>", parse_mode="HTML")
    await state.set_state(FormState.extra)

@dp.message(FormState.extra)
async def form_extra(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data["extra"] = message.text
    data["user_id"] = message.from_user.id

    # Сначала сохраняем анкету без message_id
    form_id = save_form(data)

    # Уведомление в админ-группу
    text = (
        "📝 <b>Новая анкета!</b>\n\n"
        f"<b>🆔 ID анкеты:</b> {form_id}\n"
        f"<b>👤 Имя:</b> {data['name']}\n"
        f"<b>📱 Telegram:</b> @{data['tg_username']}\n"
        f"<b>🎮 Minecraft:</b> {data['mc_nick']}\n"
        f"<b>💬 Обращение:</b> {data['call_as']}\n"
        f"<b>🎂 Возраст:</b> {data['age']}\n"
        f"<b>📝 Дополнительно:</b>\n{data['extra']}\n\n"
        f"<i>🔑 User ID:</i> <code>{data['user_id']}</code>"
    )

    # Кнопки для админов
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{data['user_id']}_{form_id}"),
            InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_{data['user_id']}_{form_id}")
        ],
        [
            InlineKeyboardButton(text="💬 Связаться", callback_data=f"contact_{data['user_id']}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{form_id}_{data['user_id']}")
        ]
    ])

    # Отправляем сообщение в админ-группу
    admin_msg = await bot.send_message(
        ADMIN_GROUP_ID,
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    # Сохраняем ID сообщения в базу
    update_admin_message_id(data['user_id'], admin_msg.message_id)

    menu = get_main_menu(message.from_user.id)
    await message.answer("✅ Анкета сохранена и отправлена на рассмотрение!", reply_markup=menu)
    await state.clear()

# ------------------------------- ПРОСМОТР АНКЕТЫ -------------------------------

@dp.message(lambda m: m.text == "📋 Моя анкета")
async def show_my_form(message: types.Message):
    form = get_user_form(message.from_user.id)
    
    if not form:
        await message.answer("❌ У вас пока нет анкеты.")
        return
    
    # Проверяем количество полей и распаковываем соответственно
    if len(form) == 13:  # Новая структура
        form_id, user_id, name, tg_username, mc_nick, call_as, age, extra, status, created_at, edited_at, is_edited, admin_message_id = form
    else:  # Старая структура (на случай если БД не пересоздана)
        form_id, user_id, name, tg_username, mc_nick, call_as, age, extra, status = form[:9]
        is_edited = 0
    
    status_emoji = {
        'pending': '⏳ На рассмотрении',
        'accepted': '✅ Одобрена',
        'rejected': '❌ Отклонена'
    }
    
    edited_mark = " ✏️ <i>(Отредактирована)</i>" if is_edited else ""
    
    text = (
        f"📋 <b>Ваша анкета:</b>{edited_mark}\n\n"
        f"<b>👤 Имя:</b> {name}\n"
        f"<b>📱 Telegram:</b> @{tg_username}\n"
        f"<b>🎮 Minecraft:</b> {mc_nick}\n"
        f"<b>💬 Обращение:</b> {call_as}\n"
        f"<b>🎂 Возраст:</b> {age}\n"
        f"<b>📝 Дополнительно:</b>\n{extra}\n\n"
        f"<b>📊 Статус:</b> {status_emoji.get(status, status)}"
    )
    
    await message.answer(text, parse_mode="HTML")

# ------------------------------- РЕДАКТИРОВАНИЕ АНКЕТЫ -------------------------------

@dp.message(lambda m: m.text == "✏️ Редактировать анкету")
async def edit_form_menu(message: types.Message, state: FSMContext):
    form = get_user_form(message.from_user.id)
    
    if not form:
        await message.answer("❌ У вас пока нет анкеты для редактирования.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="📱 Telegram username", callback_data="edit_tg_username")],
        [InlineKeyboardButton(text="🎮 Minecraft ник", callback_data="edit_mc_nick")],
        [InlineKeyboardButton(text="💬 Обращение", callback_data="edit_call_as")],
        [InlineKeyboardButton(text="🎂 Возраст", callback_data="edit_age")],
        [InlineKeyboardButton(text="📝 Дополнительно", callback_data="edit_extra")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")]
    ])
    
    await message.answer("✏️ <b>Выберите, что хотите отредактировать:</b>", parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "edit_name")
async def edit_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ <b>Введите новое имя:</b>", parse_mode="HTML")
    await state.set_state(EditFormState.editing_name)
    await callback.answer()

@dp.message(EditFormState.editing_name)
async def save_edited_name(message: types.Message, state: FSMContext):
    update_form_field(message.from_user.id, "name", message.text)
    await update_admin_form_message(message.from_user.id)
    menu = get_main_menu(message.from_user.id)
    await message.answer("✅ <b>Имя обновлено!</b>", parse_mode="HTML", reply_markup=menu)
    await state.clear()

@dp.callback_query(F.data == "edit_tg_username")
async def edit_tg(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ <b>Введите новый Telegram username:</b>", parse_mode="HTML")
    await state.set_state(EditFormState.editing_tg_username)
    await callback.answer()

@dp.message(EditFormState.editing_tg_username)
async def save_edited_tg(message: types.Message, state: FSMContext):
    update_form_field(message.from_user.id, "tg_username", message.text)
    await update_admin_form_message(message.from_user.id)
    menu = get_main_menu(message.from_user.id)
    await message.answer("✅ <b>Telegram username обновлён!</b>", parse_mode="HTML", reply_markup=menu)
    await state.clear()

@dp.callback_query(F.data == "edit_mc_nick")
async def edit_mc(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ <b>Введите новый Minecraft ник:</b>", parse_mode="HTML")
    await state.set_state(EditFormState.editing_mc_nick)
    await callback.answer()

@dp.message(EditFormState.editing_mc_nick)
async def save_edited_mc(message: types.Message, state: FSMContext):
    update_form_field(message.from_user.id, "mc_nick", message.text)
    await update_admin_form_message(message.from_user.id)
    menu = get_main_menu(message.from_user.id)
    await message.answer("✅ <b>Minecraft ник обновлён!</b>", parse_mode="HTML", reply_markup=menu)
    await state.clear()

@dp.callback_query(F.data == "edit_call_as")
async def edit_call(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ <b>Введите новое обращение:</b>", parse_mode="HTML")
    await state.set_state(EditFormState.editing_call_as)
    await callback.answer()

@dp.message(EditFormState.editing_call_as)
async def save_edited_call(message: types.Message, state: FSMContext):
    update_form_field(message.from_user.id, "call_as", message.text)
    await update_admin_form_message(message.from_user.id)
    menu = get_main_menu(message.from_user.id)
    await message.answer("✅ <b>Обращение обновлено!</b>", parse_mode="HTML", reply_markup=menu)
    await state.clear()

@dp.callback_query(F.data == "edit_age")
async def edit_age(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ <b>Введите новый возраст:</b>", parse_mode="HTML")
    await state.set_state(EditFormState.editing_age)
    await callback.answer()

@dp.message(EditFormState.editing_age)
async def save_edited_age(message: types.Message, state: FSMContext):
    update_form_field(message.from_user.id, "age", message.text)
    await update_admin_form_message(message.from_user.id)
    menu = get_main_menu(message.from_user.id)
    await message.answer("✅ <b>Возраст обновлён!</b>", parse_mode="HTML", reply_markup=menu)
    await state.clear()

@dp.callback_query(F.data == "edit_extra")
async def edit_extra(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ <b>Введите новую дополнительную информацию:</b>", parse_mode="HTML")
    await state.set_state(EditFormState.editing_extra)
    await callback.answer()

@dp.message(EditFormState.editing_extra)
async def save_edited_extra(message: types.Message, state: FSMContext):
    update_form_field(message.from_user.id, "extra", message.text)
    await update_admin_form_message(message.from_user.id)
    menu = get_main_menu(message.from_user.id)
    await message.answer("✅ <b>Дополнительная информация обновлена!</b>", parse_mode="HTML", reply_markup=menu)
    await state.clear()

@dp.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Редактирование отменено.")
    await callback.answer()

# ------------------------------- УДАЛЕНИЕ АНКЕТЫ -------------------------------

@dp.message(lambda m: m.text == "🗑 Удалить анкету")
async def delete_my_form(message: types.Message):
    form = get_user_form(message.from_user.id)
    
    if not form:
        await message.answer("❌ У вас нет анкеты для удаления.")
        return
    
    # Создаём кнопки подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_my_form"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
        ]
    ])
    
    await message.answer("⚠️ Вы уверены, что хотите удалить свою анкету?", reply_markup=keyboard)

@dp.callback_query(F.data == "confirm_delete_my_form")
async def confirm_delete_my_form(callback: types.CallbackQuery):
    delete_user_form(callback.from_user.id)
    
    menu = get_main_menu(callback.from_user.id)
    await callback.message.edit_text("✅ Ваша анкета удалена.")
    await callback.message.answer("Вы можете заполнить новую анкету.", reply_markup=menu)
    await callback.answer()

@dp.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()

# ------------------------------- РАЗБАН ПОЛЬЗОВАТЕЛЯ -------------------------------

@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    # Проверяем, что команда из админ-группы И от админа
    if message.chat.id != ADMIN_GROUP_ID:
        return
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 У вас нет прав на эту команду.")
        return

    try:
        user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.reply("❌ Использование: /unban <user_id>\nПример: /unban 123456789")
        return

    if not is_banned(user_id):
        await message.reply(f"Пользователь <code>{user_id}</code> не забанен.", parse_mode="HTML")
        return

    unban_user(user_id)

    try:
        await bot.send_message(
            user_id,
            "✅ <b>Вы были разбанены!</b>\n\nТеперь вы снова можете пользоваться ботом.",
            parse_mode="HTML"
        )
        await message.reply(f"✅ Пользователь <code>{user_id}</code> успешно разбанен и уведомлён.", parse_mode="HTML")
    except:
        await message.reply(f"✅ Разбанен <code>{user_id}</code>, но не удалось отправить уведомление (возможно, он заблокировал бота).", parse_mode="HTML")

# ------------------------------- ОБРАБОТКА КНОПОК ДЛЯ АДМИНОВ -------------------------------

@dp.callback_query(F.data.startswith("accept_"))
async def accept_application(callback: types.CallbackQuery):
    # Проверка, что команда из админ-группы
    if callback.message.chat.id != ADMIN_GROUP_ID:
        await callback.answer("Эта команда доступна только в админ-группе!")
        return

    parts = callback.data.split("_")
    user_id = int(parts[1])
    form_id = int(parts[2])

    # Обновляем статус анкеты
    update_form_status(user_id, 'accepted')

    # Красивое приветственное сообщение пользователю
    welcome_text = (
        "🎉 <b>Поздравляем!</b> 🎉\n\n"
        "Ваша анкета была одобрена! Добро пожаловать в наше сообщество!\n\n"
        "🎮 Желаем вам приятной игры и отличного общения!\n"
        "🤝 Если возникнут вопросы - всегда рады помочь!\n\n"
        f"👉 Присоединяйтесь по ссылке: {INVITE_LINK}"
    )

    try:
        await bot.send_message(user_id, welcome_text, parse_mode="HTML")
        
        # Уведомление админу об успешной отправке
        await callback.answer("✅ Приглашение отправлено!")
        
        # Обновляем сообщение в группе
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>ПРИНЯТО</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("reject_"))
async def reject_application(callback: types.CallbackQuery):
    # Проверка, что команда из админ-группы
    if callback.message.chat.id != ADMIN_GROUP_ID:
        await callback.answer("Эта команда доступна только в админ-группе!")
        return

    parts = callback.data.split("_")
    user_id = int(parts[1])
    form_id = int(parts[2])

    # Удаляем анкету и баним пользователя
    delete_form(form_id)
    ban_user(user_id)

    # Сообщение пользователю
    reject_text = (
        "❌ <b>К сожалению, ваша анкета была отклонена.</b>\n\n"
        "Доступ к боту ограничен."
    )

    try:
        await bot.send_message(user_id, reject_text, parse_mode="HTML")
        
        await callback.answer("❌ Анкета отклонена, пользователь забанен!")
        
        # Обновляем сообщение в группе
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ <b>ОТКЛОНЕНО + БАН</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("delete_"))
async def delete_form_by_admin(callback: types.CallbackQuery):
    # Проверка, что команда из админ-группы
    if callback.message.chat.id != ADMIN_GROUP_ID:
        await callback.answer("Эта команда доступна только в админ-группе!")
        return

    parts = callback.data.split("_")
    form_id = int(parts[1])
    user_id = int(parts[2])
    
    delete_form(form_id)
    
    # Уведомление пользователю
    delete_text = (
        "📋 <b>Ваша анкета была удалена администратором.</b>\n\n"
        "Вы можете заполнить новую анкету."
    )
    
    try:
        await bot.send_message(user_id, delete_text, parse_mode="HTML", reply_markup=get_main_menu(user_id))
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
    
    await callback.answer("🗑 Анкета удалена!")
    await callback.message.edit_text(
        callback.message.text + "\n\n🗑 <b>УДАЛЕНО АДМИНОМ</b>",
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("contact_"))
async def contact_user(callback: types.CallbackQuery, state: FSMContext):
    # Проверка, что команда из админ-группы
    if callback.message.chat.id != ADMIN_GROUP_ID:
        await callback.answer("Эта команда доступна только в админ-группе!")
        return

    user_id = int(callback.data.split("_")[1])
    
    # Сохраняем user_id в состояние
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminContact.waiting_for_admin_message)
    
    await callback.message.reply(
        f"✍️ Напишите сообщение для пользователя (ID: <code>{user_id}</code>):",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(AdminContact.waiting_for_admin_message)
async def send_admin_message(message: types.Message, state: FSMContext):
    # Проверка, что сообщение из админ-группы
    if message.chat.id != ADMIN_GROUP_ID:
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")

    admin_text = (
        "💬 <b>Сообщение от администрации:</b>\n\n"
        f"{message.text}"
    )

    try:
        await bot.send_message(user_id, admin_text, parse_mode="HTML")
        await message.reply("✅ Сообщение доставлено!")
    except Exception as e:
        await message.reply(f"❌ Ошибка при отправке: {e}")
    
    await state.clear()

# ------------------------------- КОМАНДА ПРОСМОТРА АНКЕТ -------------------------------

@dp.message(Command("forms"))
async def show_all_forms(message: types.Message):
    # Проверка, что команда из админ-группы
    if message.chat.id != ADMIN_GROUP_ID:
        return

    forms = get_all_forms()

    if not forms:
        await message.reply("📭 Анкет пока нет.")
        return

    response = "📋 <b>Все полученные анкеты:</b>\n\n"
    
    status_emoji = {
        'pending': '⏳',
        'accepted': '✅',
        'rejected': '❌'
    }
    
    for form in forms:
        # Проверяем количество полей и распаковываем соответственно
        if len(form) == 13:  # Новая структура
            form_id, user_id, name, tg_username, mc_nick, call_as, age, extra, status, created_at, edited_at, is_edited, admin_message_id = form
        else:  # Старая структура
            form_id, user_id, name, tg_username, mc_nick, call_as, age, extra, status = form[:9]
            is_edited = 0
        
        edited_mark = " ✏️" if is_edited else ""
        
        response += (
            f"{status_emoji.get(status, '❓')}{edited_mark} <b>ID анкеты:</b> {form_id}\n"
            f"<b>👤 Имя:</b> {name}\n"
            f"<b>📱 Telegram:</b> @{tg_username}\n"
            f"<b>🎮 Minecraft:</b> {mc_nick}\n"
            f"<b>💬 Обращение:</b> {call_as}\n"
            f"<b>🎂 Возраст:</b> {age}\n"
            f"<b>📝 Дополнительно:</b> {extra}\n"
            f"<b>🔑 User ID:</b> <code>{user_id}</code>\n"
            f"<b>📊 Статус:</b> {status}\n"
            f"{'-' * 30}\n\n"
        )

    # Telegram имеет лимит на длину сообщения (4096 символов)
    if len(response) > 4000:
        # Разбиваем на несколько сообщений
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await message.reply(part, parse_mode="HTML")
    else:
        await message.reply(response, parse_mode="HTML")

# ------------------------------- СВЯЗЬ С АДМИНОМ -------------------------------

@dp.message(lambda m: m.text == "📨 Связь с админом")
async def contact_admin(message: types.Message, state: FSMContext):
    # Проверка на бан
    if is_banned(message.from_user.id):
        await message.answer("🚫 Вы заблокированы в этом боте.")
        return
    
    await message.answer("✍️ <b>Напишите сообщение для администраторов:</b>", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ContactAdmin.waiting_for_message)

@dp.message(ContactAdmin.waiting_for_message)
async def contact_admin_send(message: types.Message, state: FSMContext):
    user = message.from_user

    text = (
        "📨 <b>Сообщение от пользователя</b>\n\n"
        f"<b>От:</b> {user.full_name}\n"
        f"<b>Username:</b> @{user.username}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n\n"
        f"<b>Текст:</b>\n{message.text}"
    )

    # Добавляем кнопку "Ответить"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"contact_{user.id}")]
    ])

    await bot.send_message(ADMIN_GROUP_ID, text, parse_mode="HTML", reply_markup=keyboard)

    menu = get_main_menu(message.from_user.id)
    await message.answer("✅ <b>Сообщение отправлено администраторам!</b>", parse_mode="HTML", reply_markup=menu)
    await state.clear()

# -------------------------------

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())