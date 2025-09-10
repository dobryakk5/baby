# main.py
"""
Главный файл бота отслеживания фертильности с поддержкой Excel и графиков
"""

from fertility_tracker import *  # Импортируем все из основного файла бота
from fertility_excel_bot_integration import register_excel_handlers
from fertility_chart_bot_integration import register_chart_handlers

# Обновляем основную клавиатуру с новыми кнопками
def get_main_keyboard_with_excel():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🌡 Добавить температуру")
    builder.button(text="💧 Выделения")
    builder.button(text="🔹 Шейка матки")
    builder.button(text="⚠️ Нарушения")
    builder.button(text="📝 Добавить заметку")
    builder.button(text="📊 Просмотр данных")
    builder.button(text="📈 Мой график")  # Новая кнопка графики
    builder.button(text="📊 Excel импорт/экспорт")  # Новая кнопка
    builder.button(text="📤 Экспорт в Excel")  # Новая кнопка
    builder.button(text="🔄 Новый цикл")
    builder.button(text="ℹ️ Помощь")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# Переопределяем функцию получения клавиатуры
get_main_keyboard = get_main_keyboard_with_excel

# Обновляем обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler_updated(message: Message):
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
            "🔹 Другие наблюдения\n\n"
            "✨ <b>Новые возможности:</b>\n"
            "📈 Графики температуры с анализом фаз\n"
            "📊 Импорт данных из Excel файлов\n"
            "📤 Экспорт ваших данных в Excel\n"
            "🔮 Прогнозы фертильности\n"
            "📄 Создание шаблонов для заполнения\n\n"
            "Используйте клавиатуру ниже или /help для просмотра всех доступных команд."
        )
        await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике start: {e}")

# Обновляем обработчик команды /help
@dp.message(Command("help"))
async def command_help_handler_updated(message: Message):
    try:
        help_text = (
            "Я могу помочь вам отслеживать данные о фертильности с использованием симптотермального метода.\n\n"
            "<b>Основные команды:</b>\n"
            "🌡 Добавить температуру - Записать утреннюю базальную температуру тела\n"
            "💧 Выделения - Отслеживать выделения и менструацию\n"
            "🔹 Шейка матки - Записать положение шейки матки\n"
            "📝 Добавить заметку - Добавить другие наблюдения\n"
            "📊 Просмотр данных - Посмотреть все данные вашего текущего цикла\n\n"
            "<b>Графики и анализ:</b>\n"
            "📈 Мой график - Графики температуры с анализом фаз\n"
            "🔮 Прогноз фертильности - Анализ текущего цикла\n"
            "📅 Определение текущей фазы цикла\n"
            "⭐ Автоматическое выделение овуляции\n\n"
            "<b>Excel интеграция:</b>\n"
            "📊 Excel импорт/экспорт - Работа с Excel файлами\n"
            "📤 Экспорт в Excel - Скачать ваши данные в Excel\n"
            "📥 Импорт из Excel - Загрузить данные из Excel файла\n"
            "📄 Шаблон Excel - Скачать шаблон для заполнения\n\n"
            "<b>Дополнительные команды:</b>\n"
            "🔄 Новый цикл - Начать новый цикл\n"
            "ℹ️ Помощь - Показать эту справку\n\n"
            "<b>Симптотермальный метод</b> помогает определить ваше фертильное окно путем отслеживания:\n"
            "1. Базальной температуры тела (измеряется каждое утро)\n"
            "2. Наблюдений за цервикальной слизью\n"
            "3. Положения шейки матки (опционально)\n\n"
            "<b>Excel импорт поддерживает:</b>\n"
            "• День цикла\n"
            "• Дата записи\n"
            "• БТТ (базальная температура тела)\n"
            "• Нарушения измерения\n"
            "• Время измерения\n"
            "• Примечания и заметки"
        )
        await message.answer(help_text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    except TelegramForbiddenError:
        logging.warning(f"Пользователь {message.from_user.id} заблокировал бота")
    except Exception as e:
        logging.error(f"Ошибка в обработчике help: {e}")

# Регистрация всех обработчиков
def register_all_handlers():
    """Регистрация всех обработчиков, включая Excel функции и графики"""
    # Регистрируем Excel обработчики
    register_excel_handlers(dp)
    
    # Регистрируем обработчики графиков
    register_chart_handlers(dp)
    
    logging.info("Все обработчики зарегистрированы, включая Excel функции и графики")

# Обновленная функция main
async def main_updated():
    # Регистрируем все обработчики
    register_all_handlers()
    
    # Регистрация обработчиков запуска и завершения работы
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    logging.info("Запуск обновленного бота для отслеживания фертильности с Excel поддержкой и графиками...")
    try:
        await dp.start_polling(bot)
    except TelegramForbiddenError as e:
        logging.error(f"Бот заблокирован пользователем: {e}")
    except Exception:
        logging.exception("Критическая ошибка при опросе")

if __name__ == "__main__":
    try:
        asyncio.run(main_updated())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception:
        logging.exception("Непредвиденная ошибка")