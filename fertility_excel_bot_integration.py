# fertility_excel_bot_integration.py
"""
Интеграция Excel обработчика с Telegram ботом для отслеживания фертильности
"""

from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import io
import os
import logging
from excel_data_handler import ExcelDataHandler, import_excel_to_bot, create_excel_template

# Добавляем новые обработчики для работы с Excel файлами

async def handle_excel_import_button(message: Message):
    """Обработчик кнопки для импорта Excel файлов"""
    try:
        builder = InlineKeyboardBuilder()
        builder.button(text="📥 Загрузить Excel файл", callback_data="excel_upload")
        builder.button(text="📄 Скачать шаблон", callback_data="excel_template")
        builder.button(text="📊 Просмотреть статистику", callback_data="excel_stats")
        builder.adjust(1)
        
        help_text = (
            "📊 <b>Работа с Excel файлами</b>\n\n"
            "Вы можете:\n"
            "• Загрузить свой Excel файл с данными о фертильности\n"
            "• Скачать шаблон для заполнения\n"
            "• Посмотреть статистику по загруженным данным\n\n"
            "Поддерживаемые поля:\n"
            "🔹 День цикла\n"
            "🔹 Дата\n"
            "🔹 БТТ (Базальная температура тела)\n"
            "🔹 Нарушения измерения\n"
            "🔹 Время измерения\n"
            "🔹 Примечания\n"
        )
        
        await message.answer(help_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка в handle_excel_import_button: {e}")

async def handle_excel_template_download(callback_query: CallbackQuery):
    """Обработчик скачивания шаблона Excel"""
    try:
        user_id = callback_query.from_user.id
        template_path = f"template_fertility_{user_id}.xlsx"
        
        # Создаем шаблон
        if create_excel_template(template_path):
            # Отправляем файл пользователю
            with open(template_path, 'rb') as file:
                await callback_query.message.answer_document(
                    types.BufferedInputFile(
                        file.read(),
                        filename="template_fertility_tracker.xlsx"
                    ),
                    caption="📄 Шаблон Excel для отслеживания фертильности\n\nЗаполните данные и отправьте файл обратно для импорта."
                )
            
            # Удаляем временный файл
            os.remove(template_path)
            
            await callback_query.answer("✅ Шаблон отправлен!")
        else:
            await callback_query.answer("❌ Ошибка создания шаблона", show_alert=True)
            
    except Exception as e:
        logging.error(f"Ошибка в handle_excel_template_download: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

async def handle_excel_upload_request(callback_query: CallbackQuery):
    """Обработчик запроса загрузки Excel файла"""
    try:
        await callback_query.message.edit_text(
            "📥 <b>Загрузка Excel файла</b>\n\n"
            "Отправьте Excel файл (.xlsx) с вашими данными о фертильности.\n"
            "Файл должен содержать столбцы: День цикла, Дата, БТТ, и другие поддерживаемые поля.",
            parse_mode="HTML"
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка в handle_excel_upload_request: {e}")

async def handle_document_upload(message: Message):
    """Обработчик загрузки документов (Excel файлов)"""
    try:
        document = message.document
        
        # Проверяем, что это Excel файл
        if not document.file_name.endswith(('.xlsx', '.xls')):
            await message.answer("❌ Пожалуйста, отправьте файл Excel (.xlsx или .xls)")
            return
        
        # Проверяем размер файла (максимум 10MB)
        if document.file_size > 10 * 1024 * 1024:
            await message.answer("❌ Файл слишком большой. Максимальный размер 10MB")
            return
        
        user_id = message.from_user.id
        
        # Скачиваем файл
        file_info = await message.bot.get_file(document.file_id)
        file_path = f"temp_excel_{user_id}.xlsx"
        
        await message.bot.download_file(file_info.file_path, file_path)
        
        # Показываем прогресс
        progress_message = await message.answer("⏳ Обрабатываем файл...")
        
        try:
            # Импортируем данные
            result = await import_excel_to_bot(file_path, user_id)
            
            if result["success"]:
                response_text = (
                    "✅ <b>Импорт успешно завершен!</b>\n\n"
                    f"📊 Импортировано записей: {result['records_imported']}\n"
                )
                
                if "statistics" in result:
                    stats = result["statistics"]
                    response_text += f"🌡 Записей с температурой: {stats.get('temperature_records', 0)}\n"
                    response_text += f"⚠️ Записей с нарушениями: {stats.get('records_with_disruptions', 0)}\n"
                    response_text += f"📝 Записей с заметками: {stats.get('records_with_notes', 0)}\n"
                    
                    if stats.get('temperature_stats'):
                        temp_stats = stats['temperature_stats']
                        response_text += f"\n🌡 <b>Статистика температуры:</b>\n"
                        response_text += f"Минимум: {temp_stats.get('min', 0):.2f}°C\n"
                        response_text += f"Максимум: {temp_stats.get('max', 0):.2f}°C\n"
                        response_text += f"Среднее: {temp_stats.get('avg', 0):.2f}°C\n"
                
                await progress_message.edit_text(response_text, parse_mode="HTML")
                
                # Показываем превью данных
                if "preview" in result and result["preview"]:
                    await message.answer(f"📋 <b>Превью импортированных данных:</b>\n\n{result['preview']}", parse_mode="HTML")
                    
            else:
                error_msg = result.get("error", "Неизвестная ошибка")
                await progress_message.edit_text(f"❌ Ошибка импорта: {error_msg}")
                
        finally:
            # Удаляем временный файл
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        logging.error(f"Ошибка в handle_document_upload: {e}")
        await message.answer("❌ Произошла ошибка при обработке файла")

async def handle_excel_stats(callback_query: CallbackQuery):
    """Обработчик просмотра статистики Excel данных"""
    try:
        user_id = callback_query.from_user.id
        
        # Получаем записи пользователя из базы данных
        from db_handler import db
        records = await db.get_user_records(user_id, limit=100)
        
        if not records:
            await callback_query.answer("📊 У вас пока нет записей", show_alert=True)
            return
        
        # Анализируем данные
        total_records = len(records)
        temp_records = len([r for r in records if r.get('temperature')])
        note_records = len([r for r in records if r.get('note')])
        
        # Температурная статистика
        temperatures = [float(r['temperature']) for r in records if r.get('temperature')]
        
        stats_text = f"📊 <b>Статистика ваших данных</b>\n\n"
        stats_text += f"📝 Всего записей: {total_records}\n"
        stats_text += f"🌡 Записей с температурой: {temp_records}\n"
        stats_text += f"📋 Записей с заметками: {note_records}\n"
        
        if temperatures:
            stats_text += f"\n🌡 <b>Температурная статистика:</b>\n"
            stats_text += f"Минимум: {min(temperatures):.2f}°C\n"
            stats_text += f"Максимум: {max(temperatures):.2f}°C\n"
            stats_text += f"Среднее: {sum(temperatures)/len(temperatures):.2f}°C\n"
        
        # Анализ последних записей
        if records:
            latest_record = records[0]  # Записи отсортированы по дате (новые первые)
            stats_text += f"\n📅 <b>Последняя запись:</b>\n"
            stats_text += f"Дата: {latest_record['record_date']}\n"
            if latest_record.get('temperature'):
                stats_text += f"Температура: {latest_record['temperature']}°C\n"
            if latest_record.get('note'):
                stats_text += f"Заметка: {latest_record['note'][:50]}...\n"
        
        await callback_query.message.edit_text(stats_text, parse_mode="HTML")
        await callback_query.answer()
        
    except Exception as e:
        logging.error(f"Ошибка в handle_excel_stats: {e}")
        await callback_query.answer("❌ Ошибка получения статистики", show_alert=True)

async def export_user_data_to_excel(user_id: int, limit: int = 100) -> str:
    """Экспорт данных пользователя в Excel файл"""
    try:
        from db_handler import db
        import pandas as pd
        
        # Получаем записи пользователя
        records = await db.get_user_records(user_id, limit=limit)
        
        if not records:
            return None
        
        # Преобразуем в DataFrame
        df_data = []
        for record in records:
            df_data.append({
                'Дата': record['record_date'],
                'БТТ': record.get('temperature'),
                'Тип слизи': record.get('mucus_type'),
                'Менструация': record.get('menstruation_type'),
                'Положение шейки': record.get('cervical_position'),
                'Заметка': record.get('note'),
                'Создано': record['created_at'],
                'Обновлено': record['updated_at']
            })
        
        df = pd.DataFrame(df_data)
        
        # Сохраняем в Excel
        output_path = f"export_fertility_{user_id}.xlsx"
        df.to_excel(output_path, index=False)
        
        return output_path
        
    except Exception as e:
        logging.error(f"Ошибка экспорта в Excel: {e}")
        return None

async def handle_export_to_excel(message: Message):
    """Обработчик экспорта данных пользователя в Excel"""
    try:
        user_id = message.from_user.id
        
        progress_message = await message.answer("⏳ Экспортируем ваши данные в Excel...")
        
        export_path = await export_user_data_to_excel(user_id)
        
        if export_path and os.path.exists(export_path):
            # Отправляем файл пользователю
            with open(export_path, 'rb') as file:
                await message.answer_document(
                    types.BufferedInputFile(
                        file.read(),
                        filename=f"fertility_data_{user_id}.xlsx"
                    ),
                    caption="📊 Ваши данные о фертильности в формате Excel"
                )
            
            # Удаляем временный файл
            os.remove(export_path)
            
            await progress_message.edit_text("✅ Данные успешно экспортированы!")
        else:
            await progress_message.edit_text("❌ Не удалось экспортировать данные. Возможно, у вас нет записей.")
            
    except Exception as e:
        logging.error(f"Ошибка в handle_export_to_excel: {e}")
        await message.answer("❌ Произошла ошибка при экспорте данных")

# Функции для регистрации обработчиков в основном боте
def register_excel_handlers(dp):
    """Регистрация обработчиков Excel функций"""
    
    # Обработчики кнопок и коллбэков
    dp.callback_query.register(handle_excel_template_download, lambda c: c.data == "excel_template")
    dp.callback_query.register(handle_excel_upload_request, lambda c: c.data == "excel_upload")
    dp.callback_query.register(handle_excel_stats, lambda c: c.data == "excel_stats")
    
    # Обработчики документов
    dp.message.register(handle_document_upload, lambda message: message.document is not None)
    
    # Обработчики текстовых команд
    dp.message.register(handle_excel_import_button, lambda message: message.text == "📊 Excel импорт/экспорт")
    dp.message.register(handle_export_to_excel, lambda message: message.text == "📤 Экспорт в Excel")