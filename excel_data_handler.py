import pandas as pd
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from db_handler import db
import os
from dataclasses import dataclass

@dataclass
class FertilityRecord:
    """Структура данных для записи о фертильности"""
    cycle_day: Optional[int] = None
    date: Optional[date] = None
    temperature: Optional[float] = None  # БТТ (базальная температура тела)
    temperature_alt: Optional[float] = None  # альтернативная температура
    disruptions: Optional[str] = None  # нарушения
    note: Optional[str] = None  # примечание
    new_thermometer: Optional[str] = None  # примечание о новом термометре
    disruption_code: Optional[str] = None  # код нарушения (НТ)
    measurement_time: Optional[str] = None  # время измерения
    timing_note: Optional[str] = None  # позже/раньше
    fertile_period: Optional[str] = None  # плодный период

class ExcelDataHandler:
    """Класс для обработки данных из Excel таблиц фертильности"""
    
    def __init__(self, excel_file_path: str):
        self.excel_file_path = excel_file_path
        self.data = None
        
    def load_excel_data(self) -> bool:
        """Загрузка данных из Excel файла"""
        try:
            # Читаем первый лист (Карта 1)
            self.data = pd.read_excel(self.excel_file_path, sheet_name=0)
            logging.info(f"Успешно загружен Excel файл: {self.excel_file_path}")
            logging.info(f"Размер данных: {self.data.shape}")
            return True
        except Exception as e:
            logging.error(f"Ошибка загрузки Excel файла: {e}")
            return False
    
    def extract_fertility_records(self) -> List[FertilityRecord]:
        """Извлечение записей о фертильности из Excel данных"""
        if self.data is None:
            logging.error("Данные не загружены. Сначала вызовите load_excel_data()")
            return []
        
        records = []
        
        try:
            # Находим строки с данными о температуре
            temp_mask = self.data['БТТ'].notna() | self.data['температура.1'].notna()
            fertility_data = self.data[temp_mask].copy()
            
            for _, row in fertility_data.iterrows():
                record = FertilityRecord()
                
                # Основные поля
                if pd.notna(row.get('День цикла')):
                    record.cycle_day = int(row['День цикла'])
                
                # Обработка даты
                if pd.notna(row.get('Дата')):
                    # Предполагаем, что дата может быть числом дня месяца
                    try:
                        day = int(row['Дата'])
                        # Создаем дату для текущего года и месяца (можно адаптировать)
                        current_year = datetime.now().year
                        current_month = datetime.now().month
                        record.date = date(current_year, current_month, day)
                    except (ValueError, TypeError):
                        logging.warning(f"Не удалось обработать дату: {row.get('Дата')}")
                
                # Температура
                if pd.notna(row.get('БТТ')):
                    record.temperature = float(row['БТТ'])
                
                if pd.notna(row.get('температура.1')):
                    record.temperature_alt = float(row['температура.1'])
                
                # Нарушения и коды
                if pd.notna(row.get('Нарушения')):
                    record.disruptions = str(row['Нарушения'])
                
                if pd.notna(row.get('НТ')):
                    record.disruption_code = str(row['НТ'])
                
                # Примечания и заметки
                if pd.notna(row.get('Примечание')):
                    record.note = str(row['Примечание'])
                
                if pd.notna(row.get('Новый термометр')):
                    record.new_thermometer = str(row['Новый термометр'])
                
                # Время измерения
                if pd.notna(row.get('Время')):
                    record.measurement_time = str(row['Время'])
                
                if pd.notna(row.get('позже/раньше')):
                    record.timing_note = str(row['позже/раньше'])
                
                if pd.notna(row.get('плодный период')):
                    record.fertile_period = str(row['плодный период'])
                
                records.append(record)
                
            logging.info(f"Извлечено {len(records)} записей о фертильности")
            return records
            
        except Exception as e:
            logging.error(f"Ошибка извлечения данных: {e}")
            return []
    
    async def save_to_database(self, user_id: int, records: List[FertilityRecord]) -> bool:
        """Сохранение записей в базу данных"""
        try:
            success_count = 0
            
            for record in records:
                # Подготовка данных для сохранения
                temperature = record.temperature or record.temperature_alt
                
                # Создание заметки из различных полей
                note_parts = []
                if record.note:
                    note_parts.append(f"Примечание: {record.note}")
                if record.new_thermometer:
                    note_parts.append(f"Термометр: {record.new_thermometer}")
                if record.disruption_code:
                    note_parts.append(f"Код: {record.disruption_code}")
                if record.measurement_time:
                    note_parts.append(f"Время: {record.measurement_time}")
                if record.timing_note:
                    note_parts.append(f"Время заметка: {record.timing_note}")
                if record.fertile_period:
                    note_parts.append(f"Плодный период: {record.fertile_period}")
                if record.cycle_day:
                    note_parts.append(f"День цикла: {record.cycle_day}")
                
                combined_note = "; ".join(note_parts) if note_parts else None
                
                # Сохранение в базу данных
                if record.date:
                    date_str = record.date.strftime("%Y-%m-%d")
                    success = await db.create_record(
                        user_id=user_id,
                        record_date=date_str,
                        temperature=temperature,
                        mucus_type=None,  # В Excel таблице нет явного поля для слизи
                        menstruation_type=None,  # В Excel таблице нет явного поля для менструации
                        cervical_position=None,  # В Excel таблице нет явного поля для позиции шейки матки
                        note=combined_note,
                        abdominal_pain=None,
                        breast_tenderness=None,
                        intercourse=None,
                        disruptions=None
                    )
                    if success:
                        success_count += 1
                
            logging.info(f"Успешно сохранено {success_count} из {len(records)} записей")
            return success_count == len(records)
            
        except Exception as e:
            logging.error(f"Ошибка сохранения в базу данных: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики по данным"""
        if self.data is None:
            return {}
        
        records = self.extract_fertility_records()
        
        stats = {
            "total_records": len(records),
            "temperature_records": len([r for r in records if r.temperature or r.temperature_alt]),
            "records_with_disruptions": len([r for r in records if r.disruptions]),
            "records_with_notes": len([r for r in records if r.note]),
            "date_range": {
                "start": min([r.date for r in records if r.date], default=None),
                "end": max([r.date for r in records if r.date], default=None)
            },
            "temperature_stats": self._get_temperature_stats(records)
        }
        
        return stats
    
    def _get_temperature_stats(self, records: List[FertilityRecord]) -> Dict[str, float]:
        """Вычисление статистики по температуре"""
        temperatures = []
        
        for record in records:
            if record.temperature:
                temperatures.append(record.temperature)
            elif record.temperature_alt:
                temperatures.append(record.temperature_alt)
        
        if not temperatures:
            return {}
        
        return {
            "min": min(temperatures),
            "max": max(temperatures),
            "avg": sum(temperatures) / len(temperatures),
            "count": len(temperatures)
        }
    
    def export_to_bot_format(self, user_id: int) -> str:
        """Экспорт данных в формат, подходящий для Telegram бота"""
        records = self.extract_fertility_records()
        
        if not records:
            return "Нет данных для экспорта"
        
        result = f"📊 Экспорт данных фертильности (пользователь {user_id})\n\n"
        
        for record in records:
            if record.date:
                result += f"📅 {record.date.strftime('%d.%m.%y')}\n"
            
            if record.temperature:
                result += f"🌡 БТТ: {record.temperature}°C\n"
            elif record.temperature_alt:
                result += f"🌡 Температура: {record.temperature_alt}°C\n"
            
            if record.disruptions:
                result += f"⚠️ Нарушения: {record.disruptions}\n"
            
            if record.measurement_time:
                result += f"⏰ Время: {record.measurement_time}\n"
            
            if record.note or record.new_thermometer:
                note = record.note or record.new_thermometer
                result += f"📝 Заметка: {note}\n"
            
            result += "\n"
        
        return result

# Функции для интеграции с ботом
async def import_excel_to_bot(excel_file_path: str, user_id: int) -> Dict[str, Any]:
    """Импорт данных из Excel в бот"""
    try:
        # Инициализируем обработчик Excel
        excel_handler = ExcelDataHandler(excel_file_path)
        
        # Загружаем данные
        if not excel_handler.load_excel_data():
            return {"success": False, "error": "Не удалось загрузить Excel файл"}
        
        # Извлекаем записи
        records = excel_handler.extract_fertility_records()
        if not records:
            return {"success": False, "error": "Не найдено записей для импорта"}
        
        # Сохраняем в базу данных
        success = await excel_handler.save_to_database(user_id, records)
        
        # Получаем статистику
        stats = excel_handler.get_statistics()
        
        return {
            "success": success,
            "records_imported": len(records),
            "statistics": stats,
            "preview": excel_handler.export_to_bot_format(user_id)[:500] + "..." if len(excel_handler.export_to_bot_format(user_id)) > 500 else excel_handler.export_to_bot_format(user_id)
        }
        
    except Exception as e:
        logging.error(f"Ошибка импорта Excel: {e}")
        return {"success": False, "error": str(e)}

def create_excel_template(output_path: str) -> bool:
    """Создание шаблона Excel для заполнения"""
    try:
        # Создаем структуру данных как в исходной таблице
        template_data = {
            'День цикла': list(range(1, 41)),  # Дни цикла 1-40
            'Дата': [''] * 40,  # Пустые даты для заполнения
            'БТТ': [''] * 40,  # Базальная температура тела
            'Нарушения': [''] * 40,  # Нарушения измерения
            'Примечание': [''] * 40,  # Примечания
            'Новый термометр': [''] * 40,  # Заметки о термометре
            'НТ': [''] * 40,  # Коды нарушений
            'температура.1': [''] * 40,  # Альтернативная температура
            'Время': [''] * 40,  # Время измерения
            'позже/раньше': [''] * 40,  # Заметки о времени
            'плодный период': [''] * 40,  # Отметки плодного периода
        }
        
        df = pd.DataFrame(template_data)
        df.to_excel(output_path, index=False)
        
        logging.info(f"Создан шаблон Excel: {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Ошибка создания шаблона Excel: {e}")
        return False

# Пример использования
async def main():
    """Пример использования ExcelDataHandler"""
    try:
        # Инициализация базы данных
        await db.initialize()
        
        # Путь к Excel файлу
        excel_file = "2_год_2024_Бланк_карт.xlsx"
        
        if os.path.exists(excel_file):
            # Тестовый пользователь
            test_user_id = 123456789
            
            # Импорт данных
            result = await import_excel_to_bot(excel_file, test_user_id)
            
            print(f"Результат импорта: {result}")
            
            # Создание шаблона
            create_excel_template("template_fertility_tracker.xlsx")
        else:
            print(f"Excel файл не найден: {excel_file}")
            
    except Exception as e:
        logging.error(f"Ошибка в main: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # Запуск примера
    asyncio.run(main())