import asyncpg
import os
from dotenv import load_dotenv
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# Загрузка переменных окружения
load_dotenv()

# Конфигурация базы данных
DATABASE_URL = os.getenv('DATABASE_URL')

class DatabaseHandler:
    def __init__(self):
        self.pool = None
    
    async def initialize(self):
        """Инициализация пула подключений к базе данных"""
        try:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            await self.create_tables()
            logging.info("Пул подключений к базе данных успешно инициализирован")
        except Exception as e:
            logging.error(f"Не удалось инициализировать пул подключений к базе данных: {e}")
            raise
    
    async def create_tables(self):
        """Создание необходимых таблиц, если они не существуют"""
        async with self.pool.acquire() as connection:
            # Создание таблицы tg_users
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS tg_users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создание таблицы records
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS records (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    record_date DATE NOT NULL,
                    temperature DECIMAL(4,2),
                    mucus_type VARCHAR(50),
                    menstruation_type VARCHAR(50),
                    cervical_position VARCHAR(50),
                    note TEXT,
                    abdominal_pain BOOLEAN DEFAULT FALSE,
                    breast_tenderness BOOLEAN DEFAULT FALSE,
                    intercourse BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES tg_users (user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, record_date)
                )
            ''')
            
            # Добавление новых полей для существующих таблиц (миграция)
            try:
                await connection.execute('ALTER TABLE records ADD COLUMN IF NOT EXISTS abdominal_pain BOOLEAN DEFAULT FALSE')
                await connection.execute('ALTER TABLE records ADD COLUMN IF NOT EXISTS breast_tenderness BOOLEAN DEFAULT FALSE')
                await connection.execute('ALTER TABLE records ADD COLUMN IF NOT EXISTS intercourse BOOLEAN DEFAULT FALSE')
            except Exception as migration_error:
                logging.warning(f"Миграция не требуется или уже выполнена: {migration_error}")
            
            # Создание индексов для лучшей производительности
            await connection.execute('''
                CREATE INDEX IF NOT EXISTS idx_records_user_id ON records (user_id)
            ''')
            
            await connection.execute('''
                CREATE INDEX IF NOT EXISTS idx_records_date ON records (record_date)
            ''')
            
            logging.info("Таблицы базы данных успешно созданы/проверены")
    
    async def create_user(self, user_id: int, username: Optional[str] = None, 
                         first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Создание нового пользователя или обновление информации существующего пользователя"""
        try:
            async with self.pool.acquire() as connection:
                await connection.execute('''
                    INSERT INTO tg_users (user_id, username, first_name, last_name)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        updated_at = CURRENT_TIMESTAMP
                ''', user_id, username, first_name, last_name)
                return True
        except Exception as e:
            logging.error(f"Не удалось создать/обновить пользователя {user_id}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow('''
                    SELECT id, user_id, username, first_name, last_name, created_at, updated_at
                    FROM tg_users WHERE user_id = $1
                ''', user_id)
                return dict(row) if row else None
        except Exception as e:
            logging.error(f"Не удалось получить пользователя {user_id}: {e}")
            return None
    
    async def create_record(self, user_id: int, record_date: str, temperature: Optional[float] = None,
                           mucus_type: Optional[str] = None, menstruation_type: Optional[str] = None,
                           cervical_position: Optional[str] = None, note: Optional[str] = None,
                           abdominal_pain: Optional[bool] = None, breast_tenderness: Optional[bool] = None,
                           intercourse: Optional[bool] = None) -> bool:
        """Создание или обновление записи для пользователя"""
        try:
            logging.debug(f"Creating record for user {user_id} with date {record_date} (type: {type(record_date)})")
            
            # Преобразование строки даты в объект даты
            if isinstance(record_date, str):
                record_date_obj = datetime.strptime(record_date, "%Y-%m-%d").date()
                logging.debug(f"Converted string date to date object: {record_date_obj}")
            else:
                record_date_obj = record_date
                logging.debug(f"Date is already a date object: {record_date_obj}")
            
            logging.debug(f"Executing database query with user_id={user_id}, record_date={record_date_obj}")
            
            async with self.pool.acquire() as connection:
                await connection.execute('''
                    INSERT INTO records (
                        user_id, record_date, temperature, mucus_type, 
                        menstruation_type, cervical_position, note,
                        abdominal_pain, breast_tenderness, intercourse
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (user_id, record_date)
                    DO UPDATE SET
                        temperature = EXCLUDED.temperature,
                        mucus_type = EXCLUDED.mucus_type,
                        menstruation_type = EXCLUDED.menstruation_type,
                        cervical_position = EXCLUDED.cervical_position,
                        note = EXCLUDED.note,
                        abdominal_pain = EXCLUDED.abdominal_pain,
                        breast_tenderness = EXCLUDED.breast_tenderness,
                        intercourse = EXCLUDED.intercourse,
                        updated_at = CURRENT_TIMESTAMP
                ''', user_id, record_date_obj, temperature, mucus_type, menstruation_type, cervical_position, note,
                     abdominal_pain, breast_tenderness, intercourse)
                logging.debug("Record created/updated successfully")
                return True
        except Exception as e:
            logging.error(f"Не удалось создать/обновить запись для пользователя {user_id}: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def get_user_records(self, user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
        """Получение записей пользователя, отсортированных по дате (новые первыми)"""
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch('''
                    SELECT id, user_id, record_date, temperature, mucus_type, 
                           menstruation_type, cervical_position, note, created_at, updated_at,
                           abdominal_pain, breast_tenderness, intercourse
                    FROM records 
                    WHERE user_id = $1 
                    ORDER BY record_date DESC 
                    LIMIT $2
                ''', user_id, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"Не удалось получить записи для пользователя {user_id}: {e}")
            return []
    
    async def get_record_by_date(self, user_id: int, record_date: str) -> Optional[Dict[str, Any]]:
        """Получение конкретной записи по user_id и дате"""
        try:
            logging.debug(f"Getting record for user {user_id} with date {record_date} (type: {type(record_date)})")
            
            # Преобразование строки даты в объект даты
            if isinstance(record_date, str):
                record_date_obj = datetime.strptime(record_date, "%Y-%m-%d").date()
                logging.debug(f"Converted string date to date object: {record_date_obj}")
            else:
                record_date_obj = record_date
                logging.debug(f"Date is already a date object: {record_date_obj}")
                
            logging.debug(f"Executing database query with user_id={user_id}, record_date={record_date_obj}")
                
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow('''
                    SELECT id, user_id, record_date, temperature, mucus_type, 
                           menstruation_type, cervical_position, note, created_at, updated_at,
                           abdominal_pain, breast_tenderness, intercourse
                    FROM records 
                    WHERE user_id = $1 AND record_date = $2
                ''', user_id, record_date_obj)
                result = dict(row) if row else None
                logging.debug(f"Retrieved record: {result}")
                return result
        except Exception as e:
            logging.error(f"Не удалось получить запись для пользователя {user_id} на {record_date}: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def delete_record(self, user_id: int, record_date: str) -> bool:
        """Удаление конкретной записи по user_id и дате"""
        try:
            # Преобразование строки даты в объект даты
            if isinstance(record_date, str):
                record_date_obj = datetime.strptime(record_date, "%Y-%m-%d").date()
            else:
                record_date_obj = record_date
                
            async with self.pool.acquire() as connection:
                result = await connection.execute('''
                    DELETE FROM records 
                    WHERE user_id = $1 AND record_date = $2
                ''', user_id, record_date_obj)
                return result == "DELETE 1"
        except Exception as e:
            logging.error(f"Не удалось удалить запись для пользователя {user_id} на {record_date}: {e}")
            return False
    
    async def close(self):
        """Закрытие пула подключений к базе данных"""
        if self.pool:
            await self.pool.close()
            logging.info("Пул подключений к базе данных закрыт")

# Глобальный экземпляр
db = DatabaseHandler()