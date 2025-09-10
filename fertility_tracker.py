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
    builder.button(text="💧 Добавить слизь")
    builder.button(text="🩸 Добавить менструацию")
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
            "🔹 Цервикальную слизь\n"
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
            "/add_mucus - Добавить наблюдение за цервикальной слизью\n"
            "/add_cervix - Добавить наблюдение за положением шейки матки\n"
            "/add_menstruation - Добавить данные о менструации\n"
            "/add_note - Добавить другие наблюдения\n"
            "/view_data - Просмотр данных вашего текущего цикла\n"
            "/view_chart - Просмотр графика температуры\n"
            "/reset_cycle - Начать новый цикл\n\n"
            "Симптотермальный метод помогает определить ваше фертильное окно путем отслеживания:\n"
            "1. Базальной температуры тела (измеряется каждое утро)\n"
            "2. Наблюдений за цервикальной слизью\n"
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
                        note=record.get('note')
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

# Обработчик кнопки клавиатуры для слизи
@dp.message(F.text == "💧 Добавить слизь")
async def handle_mucus_button(message: Message):
    try:
        # Создание инлайн-клавиатуры для типов слизи
        builder = InlineKeyboardBuilder()
        builder.button(text="Сухо", callback_data="mucus_dry")
        builder.button(text="Липкое", callback_data="mucus_sticky")
        builder.button(text="Кремообразное", callback_data="mucus_creamy")
        builder.button(text="Водянистое", callback_data="mucus_watery")
        builder.button(text="Слизь", callback_data="mucus_eggwhite")
        builder.button(text="Другое", callback_data="mucus_other")
        builder.adjust(2)
        
        await message.answer("Выберите тип цервикальной слизи:", reply_markup=builder.as_markup())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике кнопки слизи: {e}")

# Обработчик выбора слизи
@dp.callback_query(lambda c: c.data.startswith("mucus_"))
async def handle_mucus_selection(callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        mucus_type = callback_query.data.split("_")[1]
        mucus_descriptions = {
            "dry": "Сухо",
            "sticky": "Липкое",
            "creamy": "Кремообразное",
            "watery": "Водянистое",
            "eggwhite": "Слизь",
            "other": "Другое"
        }
        
        today_db = get_today_db_format()  # Формат для БД
        today_display = get_today_display_format()  # Формат для отображения
        logging.debug(f"Processing mucus selection for user {user_id} on date {today_db}")
        
        # Получение существующей записи или создание новой
        record = await db.get_record_by_date(user_id, today_db)
        if record:
            logging.debug(f"Updating existing record for user {user_id}")
            # Обновление существующей записи
            await db.create_record(
                user_id=user_id,
                record_date=today_db,
                temperature=record.get('temperature'),
                mucus_type=mucus_descriptions[mucus_type],
                menstruation_type=record.get('menstruation_type'),
                cervical_position=record.get('cervical_position'),
                note=record.get('note')
            )
        else:
            logging.debug(f"Creating new record for user {user_id}")
            # Создание новой записи
            await db.create_record(
                user_id=user_id,
                record_date=today_db,
                mucus_type=mucus_descriptions[mucus_type]
            )
        
        await callback_query.message.edit_text(f"✅ Цервикальная слизь '{mucus_descriptions[mucus_type]}' записана на {today_display}")
        await callback_query.answer()
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {callback_query.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка при обработке выбора слизи: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

# Обработчик кнопки клавиатуры для менструации
@dp.message(F.text == "🩸 Добавить менструацию")
async def handle_menstruation_button(message: Message):
    try:
        # Создание инлайн-клавиатуры для типов менструации
        builder = InlineKeyboardBuilder()
        builder.button(text="Слабые", callback_data="menstruation_light")
        builder.button(text="Средние", callback_data="menstruation_medium")
        builder.button(text="Обильные", callback_data="menstruation_heavy")
        builder.button(text="Мажущие", callback_data="menstruation_spotting")
        builder.adjust(2)
        
        await message.answer("Выберите тип менструации:", reply_markup=builder.as_markup())
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике кнопки менструации: {e}")

# Обработчик выбора менструации
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
                note=record.get('note')
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

# Обработчик кнопки клавиатуры для заметок
@dp.message(F.text == "📝 Добавить заметку")
async def handle_note_button(message: Message):
    try:
        await message.answer("Пожалуйста, введите вашу заметку:")
        # Установка состояния ожидания ввода заметки
        user_id = message.from_user.id
        # Хранение состояния в простом словаре (в production можно использовать FSM)
        if not hasattr(dp, 'note_input_state'):
            dp.note_input_state = {}
        dp.note_input_state[user_id] = True
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике кнопки заметки: {e}")

# Обработчик ввода заметки
@dp.message(lambda message: hasattr(dp, 'note_input_state') and 
                           message.from_user.id in dp.note_input_state and 
                           dp.note_input_state[message.from_user.id])
async def handle_note_input(message: Message):
    try:
        user_id = message.from_user.id
        note = message.text
        
        # Добавление заметки в базу данных
        today_db = get_today_db_format()  # Формат для БД
        today_display = get_today_display_format()  # Формат для отображения
        logging.debug(f"Processing note input for user {user_id} on date {today_db}")
        
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
                cervical_position=record.get('cervical_position'),
                note=note
            )
        else:
            logging.debug(f"Creating new record for user {user_id}")
            # Создание новой записи
            await db.create_record(
                user_id=user_id,
                record_date=today_db,
                note=note
            )
        
        await message.answer(f"✅ Заметка записана на {today_display}", reply_markup=get_main_keyboard())
        
        # Сброс состояния ввода
        if hasattr(dp, 'note_input_state') and user_id in dp.note_input_state:
            del dp.note_input_state[user_id]
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка при обработке ввода заметки: {e}")
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
                data_text += f"💧 Слизь: {record['mucus_type']}\n"
            if record['menstruation_type']:
                data_text += f"🩸 Менструация: {record['menstruation_type']}\n"
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
            "💧 Добавить слизь - Отслеживать изменения цервикальной слизи\n"
            "🩸 Добавить менструацию - Записать менструальный поток\n"
            "📝 Добавить заметку - Добавить другие наблюдения\n"
            "📊 Просмотр данных - Посмотреть все данные вашего текущего цикла\n"
            "🔄 Новый цикл - Начать новый цикл\n"
            "ℹ️ Помощь - Показать эту справку\n\n"
            "Симптотермальный метод помогает определить ваше фертильное окно путем отслеживания:\n"
            "1. Базальной температуры тела (измеряется каждое утро)\n"
            "2. Наблюдений за цервикальной слизью\n"
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