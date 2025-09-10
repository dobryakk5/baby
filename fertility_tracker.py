# fertility_tracker_bot.py
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List
from db_handler import db

# Загрузка переменных окружения
load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Функция для форматирования даты в формат DD.MM.YY
def format_date(date_str):
    """Форматирование даты из YYYY-MM-DD в DD.MM.YY"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%d.%m.%y")
    except:
        return date_str

# Функция для получения сегодняшней даты в формате YYYY-MM-DD (для БД)
def get_today_db_format():
    """Получение сегодняшней даты в формате YYYY-MM-DD для БД"""
    return datetime.now().strftime("%Y-%m-%d")

# Функция для получения сегодняшней даты в формате DD.MM.YY (для отображения)
def get_today_display_format():
    """Получение сегодняшней даты в формате DD.MM.YY для отображения"""
    return datetime.now().strftime("%d.%m.%y")

# Создание основной клавиатуры
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🌡 Добавить температуру")
    builder.button(text="💧 Выделения")
    builder.button(text="🔹 Шейка матки")
    builder.button(text="📝 Добавить заметку")
    builder.button(text="📊 Просмотр данных")
    builder.button(text="🔄 Новый цикл")
    builder.button(text="ℹ️ Помощь")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        
        # Создание или обновление пользователя в базе данных
        await db.create_user(user_id, username, first_name, last_name)
        
        welcome_text = (
            f"Здравствуйте, {message.from_user.full_name}! 👋\n\n"
            "Я ваш помощник по отслеживанию фертильности на основе симптотермального метода.\n\n"
            "Я могу помочь вам отслеживать:\n"
            "🔹 Базальную температуру тела (БТТ)\n"
            "🔹 Выделения\n"
            "🔹 Положение шейки матки\n"
            "🔹 Менструацию\n"
            "🔹 Другие наблюдения\n\n"
            "Используйте клавиатуру ниже или /help для просмотра всех доступных команд."
        )
        await message.answer(welcome_text, reply_markup=get_main_keyboard())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике start: {e}")

# Обработчик команды /help
@dp.message(Command("help"))
async def command_help_handler(message: Message):
    try:
        help_text = (
            "Я могу помочь вам отслеживать данные о фертильности с использованием симптотермального метода.\n\n"
            "Доступные команды:\n"
            "/start - Запустить бота\n"
            "/help - Показать эту справку\n"
            "/add_temperature - Добавить сегодняшнюю базальную температуру тела\n"
            "/add_discharge - Добавить выделения\n"
            "/add_cervix - Добавить наблюдение за положением шейки матки\n"
            "/add_menstruation - Добавить данные о менструации\n"
            "/add_note - Добавить другие наблюдения\n"
            "/view_data - Просмотр данных вашего текущего цикла\n"
            "/view_chart - Просмотр графика температуры\n"
            "/reset_cycle - Начать новый цикл\n\n"
            "Симптотермальный метод помогает определить ваше фертильное окно путем отслеживания:\n"
            "1. Базальной температуры тела (измеряется каждое утро)\n"
            "2. Наблюдений за выделениями\n"
            "3. Положения шейки матки (опционально)"
        )
        await message.answer(help_text, reply_markup=get_main_keyboard())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике help: {e}")

# Обработчик кнопки клавиатуры для температуры
@dp.message(F.text == "🌡 Добавить температуру")
async def handle_temperature_button(message: Message):
    try:
        await message.answer("Пожалуйста, введите вашу базальную температуру тела (в °C):")
        # Установка состояния ожидания ввода температуры
        user_id = message.from_user.id
        # Хранение состояния в простом словаре (в production можно использовать FSM)
        if not hasattr(dp, 'temp_input_state'):
            dp.temp_input_state = {}
        dp.temp_input_state[user_id] = True
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике кнопки температуры: {e}")

# Обработчик ввода температуры
@dp.message(lambda message: hasattr(dp, 'temp_input_state') and 
                           message.from_user.id in dp.temp_input_state and 
                           dp.temp_input_state[message.from_user.id])
async def handle_temperature_input(message: Message):
    try:
        user_id = message.from_user.id
        try:
            temperature = float(message.text.replace(',', '.'))
            # Проверка диапазона температуры (разумный диапазон БТТ)
            if 35.0 <= temperature <= 40.0:
                # Добавление температуры в базу данных
                today_db = get_today_db_format()  # Формат для БД
                today_display = get_today_display_format()  # Формат для отображения
                logging.debug(f"Processing temperature input for user {user_id} on date {today_db}")
                
                # Получение существующей записи или создание новой
                record = await db.get_record_by_date(user_id, today_db)
                if record:
                    logging.debug(f"Updating existing record for user {user_id}")
                    # Обновление существующей записи
                    await db.create_record(
                        user_id=user_id,
                        record_date=today_db,
                        temperature=temperature,
                        mucus_type=record.get('mucus_type'),
                        menstruation_type=record.get('menstruation_type'),
                        cervical_position=record.get('cervical_position'),
                        note=record.get('note'),
                        abdominal_pain=record.get('abdominal_pain'),
                        breast_tenderness=record.get('breast_tenderness'),
                        intercourse=record.get('intercourse')
                    )
                else:
                    logging.debug(f"Creating new record for user {user_id}")
                    # Создание новой записи
                    await db.create_record(
                        user_id=user_id,
                        record_date=today_db,
                        temperature=temperature
                    )
                
                await message.answer(f"✅ Температура {temperature}°C записана на {today_display}", reply_markup=get_main_keyboard())
            else:
                await message.answer("❌ Пожалуйста, введите действительную температуру от 35.0°C до 40.0°C")
        except ValueError:
            await message.answer("❌ Пожалуйста, введите действительное число для температуры")
        
        # Сброс состояния ввода
        if hasattr(dp, 'temp_input_state') and user_id in dp.temp_input_state:
            del dp.temp_input_state[user_id]
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка при обработке ввода температуры: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

# Обработчик кнопки клавиатуры для выделений
@dp.message(F.text == "💧 Выделения")
async def handle_discharge_button(message: Message):
    try:
        # Создание инлайн-клавиатуры для типов выделений
        builder = InlineKeyboardBuilder()
        builder.button(text="Менструация", callback_data="discharge_menstruation")
        builder.button(text="Сухо", callback_data="discharge_dry")
        builder.button(text="Влажно", callback_data="discharge_wet")
        builder.button(text="Мокро", callback_data="discharge_moist")
        builder.adjust(2)
        
        await message.answer("Выберите тип выделений:", reply_markup=builder.as_markup())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике кнопки выделений: {e}")


# Обработчик выбора выделений
@dp.callback_query(lambda c: c.data.startswith("discharge_"))
async def handle_discharge_selection(callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        discharge_type = callback_query.data.split("_")[1]
        
        today_db = get_today_db_format()  # Формат для БД
        today_display = get_today_display_format()  # Формат для отображения
        logging.debug(f"Processing discharge selection for user {user_id} on date {today_db}")
        
        # Получение существующей записи или создание новой
        record = await db.get_record_by_date(user_id, today_db)
        
        if discharge_type == "menstruation":
            # Если выбрана менструация, показываем дополнительные опции
            builder = InlineKeyboardBuilder()
            builder.button(text="Слабые", callback_data="menstruation_light")
            builder.button(text="Средние", callback_data="menstruation_medium")
            builder.button(text="Обильные", callback_data="menstruation_heavy")
            builder.button(text="Мажущие", callback_data="menstruation_spotting")
            builder.adjust(2)
            
            await callback_query.message.edit_text("Выберите тип менструации:", reply_markup=builder.as_markup())
        else:
            # Обработка типов слизи
            discharge_descriptions = {
                "dry": "Сухо",
                "wet": "Влажно", 
                "moist": "Мокро"
            }
            
            if record:
                logging.debug(f"Updating existing record for user {user_id}")
                # Обновление существующей записи
                await db.create_record(
                    user_id=user_id,
                    record_date=today_db,
                    temperature=record.get('temperature'),
                    mucus_type=discharge_descriptions[discharge_type],
                    menstruation_type=record.get('menstruation_type'),
                    cervical_position=record.get('cervical_position'),
                    note=record.get('note'),
                    abdominal_pain=record.get('abdominal_pain'),
                    breast_tenderness=record.get('breast_tenderness'),
                    intercourse=record.get('intercourse')
                )
            else:
                logging.debug(f"Creating new record for user {user_id}")
                # Создание новой записи
                await db.create_record(
                    user_id=user_id,
                    record_date=today_db,
                    mucus_type=discharge_descriptions[discharge_type]
                )
            
            await callback_query.message.edit_text(f"✅ Выделения '{discharge_descriptions[discharge_type]}' записаны на {today_display}")
        
        await callback_query.answer()
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {callback_query.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка при обработке выбора выделений: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

# Обработчик выбора менструации (для обратной совместимости)
@dp.callback_query(lambda c: c.data.startswith("menstruation_"))
async def handle_menstruation_selection(callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        menstruation_type = callback_query.data.split("_")[1]
        menstruation_descriptions = {
            "light": "Слабые",
            "medium": "Средние",
            "heavy": "Обильные",
            "spotting": "Мажущие"
        }
        
        today_db = get_today_db_format()  # Формат для БД
        today_display = get_today_display_format()  # Формат для отображения
        logging.debug(f"Processing menstruation selection for user {user_id} on date {today_db}")
        
        # Получение существующей записи или создание новой
        record = await db.get_record_by_date(user_id, today_db)
        if record:
            logging.debug(f"Updating existing record for user {user_id}")
            # Обновление существующей записи
            await db.create_record(
                user_id=user_id,
                record_date=today_db,
                temperature=record.get('temperature'),
                mucus_type=record.get('mucus_type'),
                menstruation_type=menstruation_descriptions[menstruation_type],
                cervical_position=record.get('cervical_position'),
                note=record.get('note'),
                abdominal_pain=record.get('abdominal_pain'),
                breast_tenderness=record.get('breast_tenderness'),
                intercourse=record.get('intercourse')
            )
        else:
            logging.debug(f"Creating new record for user {user_id}")
            # Создание новой записи
            await db.create_record(
                user_id=user_id,
                record_date=today_db,
                menstruation_type=menstruation_descriptions[menstruation_type]
            )
        
        await callback_query.message.edit_text(f"✅ Менструация '{menstruation_descriptions[menstruation_type]}' записана на {today_display}")
        await callback_query.answer()
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {callback_query.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка при обработке выбора менструации: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

# Обработчик кнопки клавиатуры для шейки матки
@dp.message(F.text == "🔹 Шейка матки")
async def handle_cervix_button(message: Message):
    try:
        # Создание инлайн-клавиатуры для позиции шейки матки (первый уровень)
        builder = InlineKeyboardBuilder()
        builder.button(text="Низко", callback_data="cervix_low")
        builder.button(text="Высоко", callback_data="cervix_high")
        builder.adjust(2)
        
        await message.answer("Выберите позицию шейки матки:", reply_markup=builder.as_markup())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике кнопки шейки матки: {e}")

# Обработчик выбора позиции шейки матки (первый уровень)
@dp.callback_query(lambda c: c.data.startswith("cervix_"))
async def handle_cervix_position_selection(callback_query: CallbackQuery):
    try:
        position = callback_query.data.split("_")[1]  # low или high
        
        # Создание инлайн-клавиатуры для состояния шейки матки (второй уровень)
        builder = InlineKeyboardBuilder()
        builder.button(text="Закрыта", callback_data=f"cervix_state_{position}_closed")
        builder.button(text="Открыта", callback_data=f"cervix_state_{position}_open")
        builder.adjust(2)
        
        position_text = "низко" if position == "low" else "высоко"
        await callback_query.message.edit_text(
            f"Шейка матки {position_text}. Выберите состояние:", 
            reply_markup=builder.as_markup()
        )
        await callback_query.answer()
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {callback_query.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка при обработке выбора позиции шейки матки: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

# Обработчик выбора состояния шейки матки (второй уровень)
@dp.callback_query(lambda c: c.data.startswith("cervix_state_"))
async def handle_cervix_state_selection(callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        parts = callback_query.data.split("_")  # cervix_state_position_state
        position = parts[2]  # low или high
        state = parts[3]     # closed или open
        
        # Кодирование согласно требованию:
        # 1 - высоко открыта, 2 - высоко закрыта, 3 - низко открыта, 4 - низко закрыта
        cervix_codes = {
            "high_open": 1,    # высоко открыта
            "high_closed": 2,  # высоко закрыта  
            "low_open": 3,     # низко открыта
            "low_closed": 4    # низко закрыта
        }
        
        code_key = f"{position}_{state}"
        cervical_position_code = cervix_codes[code_key]
        
        # Создание описания для пользователя
        position_text = "высоко" if position == "high" else "низко"
        state_text = "открыта" if state == "open" else "закрыта"
        
        today_db = get_today_db_format()  # Формат для БД
        today_display = get_today_display_format()  # Формат для отображения
        logging.debug(f"Processing cervix selection for user {user_id} on date {today_db}")
        
        # Получение существующей записи или создание новой
        record = await db.get_record_by_date(user_id, today_db)
        if record:
            logging.debug(f"Updating existing record for user {user_id}")
            # Обновление существующей записи
            await db.create_record(
                user_id=user_id,
                record_date=today_db,
                temperature=record.get('temperature'),
                mucus_type=record.get('mucus_type'),
                menstruation_type=record.get('menstruation_type'),
                cervical_position=cervical_position_code,
                note=record.get('note')
            )
        else:
            logging.debug(f"Creating new record for user {user_id}")
            # Создание новой записи
            await db.create_record(
                user_id=user_id,
                record_date=today_db,
                cervical_position=cervical_position_code
            )
        
        await callback_query.message.edit_text(
            f"✅ Шейка матки '{position_text} {state_text}' записана на {today_display}"
        )
        await callback_query.answer()
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {callback_query.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка при обработке выбора состояния шейки матки: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

# Обработчик кнопки клавиатуры для заметок
@dp.message(F.text == "📝 Добавить заметку")
async def handle_note_button(message: Message):
    try:
        # Создание инлайн-клавиатуры для типов заметок
        builder = InlineKeyboardBuilder()
        builder.button(text="😢 Боли/вздутие живота", callback_data="note_abdominal_pain")
        builder.button(text="🤱 Напряжение в груди", callback_data="note_breast_tenderness")
        builder.button(text="💕 Супружеская близость", callback_data="note_intercourse")
        builder.adjust(1)
        
        await message.answer("Выберите тип заметки:", reply_markup=builder.as_markup())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике кнопки заметки: {e}")

# Обработчик выбора типа заметки
@dp.callback_query(lambda c: c.data.startswith("note_"))
async def handle_note_selection(callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        note_type = callback_query.data.split("_")[1]  # abdominal_pain, breast_tenderness, intercourse
        
        today_db = get_today_db_format()  # Формат для БД
        today_display = get_today_display_format()  # Формат для отображения
        logging.debug(f"Processing note selection for user {user_id} on date {today_db}")
        
        # Определяем, какое поле обновлять
        note_fields = {
            "abdominal_pain": ("abdominal_pain", "😢 Боли/вздутие живота"),
            "breast_tenderness": ("breast_tenderness", "🤱 Напряжение в груди"),
            "intercourse": ("intercourse", "💕 Супружеская близость")
        }
        
        field_name, field_description = note_fields[note_type]
        
        # Получение существующей записи или создание новой
        record = await db.get_record_by_date(user_id, today_db)
        
        # Подготовка параметров для обновления
        update_params = {
            "user_id": user_id,
            "record_date": today_db,
            "temperature": record.get('temperature') if record else None,
            "mucus_type": record.get('mucus_type') if record else None,
            "menstruation_type": record.get('menstruation_type') if record else None,
            "cervical_position": record.get('cervical_position') if record else None,
            "note": record.get('note') if record else None,
            "abdominal_pain": record.get('abdominal_pain') if record else None,
            "breast_tenderness": record.get('breast_tenderness') if record else None,
            "intercourse": record.get('intercourse') if record else None
        }
        
        # Обновляем конкретное поле
        update_params[field_name] = True
        
        # Сохраняем в базу данных
        await db.create_record(**update_params)
        
        await callback_query.message.edit_text(
            f"✅ Отмечено: {field_description} на {today_display}"
        )
        await callback_query.answer()
        
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {callback_query.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка при обработке выбора типа заметки: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

# Обработчик кнопки клавиатуры для просмотра данных
@dp.message(F.text == "📊 Просмотр данных")
async def handle_view_data_button(message: Message):
    try:
        user_id = message.from_user.id
        logging.debug(f"Processing view data request for user {user_id}")
        records = await db.get_user_records(user_id, limit=30)
        
        if not records:
            await message.answer("Данные еще не записаны. Начните с добавления температуры, слизи или менструации.", reply_markup=get_main_keyboard())
            return
        
        # Форматирование данных для отображения
        data_text = f"📊 <b>Последние данные цикла</b>\n\n"
        
        # Отображение записей, отсортированных по дате (новые первыми)
        for record in records:
            # Форматирование даты для отображения
            display_date = format_date(str(record['record_date']))
            data_text += f"📅 <b>{display_date}</b>\n"
            if record['temperature']:
                data_text += f"🌡 Температура: {record['temperature']}°C\n"
            if record['mucus_type']:
                data_text += f"💧 Выделения: {record['mucus_type']}\n"
            if record['menstruation_type']:
                data_text += f"💧 Выделения: {record['menstruation_type']}\n"
            if record['cervical_position']:
                # Декодирование позиции шейки матки
                cervix_descriptions = {
                    1: "высоко открыта",
                    2: "высоко закрыта", 
                    3: "низко открыта",
                    4: "низко закрыта"
                }
                cervix_text = cervix_descriptions.get(record['cervical_position'], f"код {record['cervical_position']}")
                data_text += f"🔹 Шейка матки: {cervix_text}\n"
            # Отображение специальных заметок
            if record.get('abdominal_pain'):
                data_text += f"😢 Боли/вздутие живота\n"
            if record.get('breast_tenderness'):
                data_text += f"🤱 Напряжение в груди\n"
            if record.get('intercourse'):
                data_text += f"💕 Супружеская близость\n"
            if record['note']:
                data_text += f"📝 Заметка: {record['note']}\n"
            data_text += "\n"
        
        # Ограничение длины сообщения, если оно слишком длинное
        if len(data_text) > 4000:
            data_text = data_text[:4000] + "\n... (данные обрезаны)"
        
        await message.answer(data_text, parse_mode="HTML", reply_markup=get_main_keyboard())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике просмотра данных: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

# Обработчик кнопки клавиатуры для нового цикла
@dp.message(F.text == "🔄 Новый цикл")
async def handle_reset_cycle_button(message: Message):
    try:
        # Для этого бота "сброс цикла" не удаляет данные, а просто информирует пользователя
        # В более продвинутой версии можно реализовать отслеживание циклов
        today_display = get_today_display_format()
        await message.answer(f"🔄 Эта функция предназначена для отслеживания нескольких циклов. Ваши данные сохраняются непрерывно. Сегодня {today_display}", reply_markup=get_main_keyboard())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике сброса цикла: {e}")

# Обработчик кнопки помощи
@dp.message(F.text == "ℹ️ Помощь")
async def handle_help_button(message: Message):
    try:
        help_text = (
            "Я могу помочь вам отслеживать данные о фертильности с использованием симптотермального метода.\n\n"
            "Доступные команды:\n"
            "🌡 Добавить температуру - Записать утреннюю базальную температуру тела\n"
            "💧 Выделения - Отслеживать выделения и менструацию\n"
            "🔹 Шейка матки - Записать положение шейки матки\n"
            "📝 Добавить заметку - Добавить другие наблюдения\n"
            "📊 Просмотр данных - Посмотреть все данные вашего текущего цикла\n"
            "🔄 Новый цикл - Начать новый цикл\n"
            "ℹ️ Помощь - Показать эту справку\n\n"
            "Симптотермальный метод помогает определить ваше фертильное окно путем отслеживания:\n"
            "1. Базальной температуры тела (измеряется каждое утро)\n"
            "2. Наблюдений за выделениями\n"
            "3. Положения шейки матки (опционально)"
        )
        await message.answer(help_text, reply_markup=get_main_keyboard())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике кнопки помощи: {e}")

# Настройка логирования
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Changed to DEBUG for more detailed logging
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Файловый обработчик с ротацией по дате
file_handler = TimedRotatingFileHandler(
    filename="logs/fertility_bot.log",
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8"
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)  # Ensure file handler also logs debug messages

# Консольный обработчик
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)  # Console logs info and above

# Добавление обработчиков
logger.addHandler(file_handler)
logger.addHandler(console_handler)

async def on_startup():
    """Инициализация подключения к базе данных при запуске"""
    try:
        await db.initialize()
        logging.info("База данных успешно инициализирована")
    except Exception as e:
        logging.error(f"Не удалось инициализировать базу данных: {e}")
        raise

async def on_shutdown():
    """Закрытие подключения к базе данных при завершении работы"""
    try:
        await db.close()
        logging.info("Подключение к базе данных закрыто")
    except Exception as e:
        logging.error(f"Ошибка при закрытии подключения к базе данных: {e}")

async def main():
    # Регистрация обработчиков запуска и завершения работы
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    logging.info("Запуск бота для отслеживания фертильности...")
    try:
        await dp.start_polling(bot)
    except TelegramForbiddenError as e:
        logging.error(f"Бот заблокирован пользователем: {e}")
    except Exception:
        logging.exception("Критическая ошибка при опросе")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception:
        logging.exception("Непредвиденная ошибка")