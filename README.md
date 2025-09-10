# Проект Telegram бота

Этот проект содержит реализации Telegram ботов с использованием Python.

## Файлы

- `old.py` - Оригинальная реализация бота
- `new_bot.py` - Новая реализация бота (с использованием aiogram)
- `fertility_tracker_bot.py` - Бот для отслеживания фертильности (с использованием aiogram)
- `db_handler.py` - Обработчик базы данных для хранения пользовательских данных и записей
- `telegram_bot.py` - Альтернативная реализация бота (с использованием python-telegram-bot)

## Настройка

1. Убедитесь, что у вас установлен Python 3.7+
2. Установите необходимые зависимости:
   ```
   pip install -r requirements.txt
   ```

## Настройка базы данных

Бот для отслеживания фертильности использует PostgreSQL для хранения данных. Убедитесь, что DATABASE_URL в файле `.env` правильно настроен.

Бот автоматически создает две таблицы:
- `tg_users` - Хранит информацию о пользователях Telegram
- `records` - Хранит данные отслеживания фертильности для каждого пользователя

## Запуск ботов

### Запуск бота для отслеживания фертильности (aiogram)
```
python fertility_tracker_bot.py
```

### Запуск нового бота (aiogram)
```
python new_bot.py
```

### Запуск оригинального бота (aiogram)
```
python old.py
```

### Запуск альтернативного бота (python-telegram-bot)
```
python telegram_bot.py
```

Все боты будут использовать API_TOKEN из вашего файла `.env`.

## Функции бота для отслеживания фертильности

Бот для отслеживания фертильности помогает вам отслеживать фертильность с использованием симптотермального метода:

1. **Отслеживание базальной температуры тела (БТТ)**
   - Запись ежедневных утренних показаний температуры
   - Визуализация температурных паттернов

2. **Отслеживание цервикальной слизи**
   - Отслеживание изменений цервикальной слизи в течение цикла
   - Определение дней пиковой фертильности

3. **Отслеживание менструации**
   - Запись характеристик менструального потока

4. **Дополнительные заметки**
   - Добавление наблюдений о факторах, которые могут повлиять на фертильность
   - Отслеживание половой активности, болезней или других важных факторов

### Команды бота для отслеживания фертильности

- `/start` - Инициализация бота и создание вашего профиля
- `/help` - Показать справочную информацию
- `/add_temperature` - Добавить сегодняшнюю базальную температуру тела
- `/add_mucus` - Добавить наблюдение за цервикальной слизью
- `/add_menstruation` - Добавить данные о менструации
- `/add_note` - Добавить другие наблюдения
- `/view_data` - Просмотр данных вашего текущего цикла
- `/reset_cycle` - Начать новый цикл

Или используйте удобные кнопки клавиатуры:
- 🌡 Добавить температуру
- 💧 Добавить слизь
- 🩸 Добавить менструацию
- 📝 Добавить заметку
- 📊 Просмотр данных
- 🔄 Новый цикл
- ℹ️ Помощь

## Переменные окружения

Боты ожидают следующие переменные окружения:
- `API_TOKEN` - Токен вашего Telegram бота от BotFather
- `DATABASE_URL` - Строка подключения к базе данных PostgreSQL

## Схема базы данных

### Таблица tg_users
```sql
CREATE TABLE IF NOT EXISTS tg_users (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Таблица records
```sql
CREATE TABLE IF NOT EXISTS records (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    record_date DATE NOT NULL,
    temperature DECIMAL(4,2),
    mucus_type VARCHAR(50),
    menstruation_type VARCHAR(50),
    cervical_position VARCHAR(50),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES tg_users (user_id) ON DELETE CASCADE,
    UNIQUE(user_id, record_date)
)
```