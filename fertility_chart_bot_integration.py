"""
Интеграция графиков фертильности с Telegram ботом
"""

from aiogram import types, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
from datetime import datetime, timedelta
from db_handler import db
from fertility_chart_generator import (
    generate_fertility_chart, 
    get_current_fertility_phase,
    get_fertility_predictions
)

async def handle_chart_request_button(message: Message):
    """Обработчик кнопки запроса графиков"""
    try:
        builder = InlineKeyboardBuilder()
        builder.button(text="📈 График температуры", callback_data="chart_temperature")
        builder.button(text="📊 Сводный график", callback_data="chart_summary")
        builder.button(text="🔮 Прогноз фертильности", callback_data="chart_prediction")
        builder.button(text="📅 Текущая фаза", callback_data="chart_current_phase")
        builder.adjust(2)
        
        help_text = (
            "📊 <b>Графики и анализ фертильности</b>\n\n"
            "Доступные варианты:\n\n"
            "📈 <b>График температуры</b> - показывает изменения базальной температуры с выделением фаз цикла\n\n"
            "📊 <b>Сводный график</b> - комплексный анализ с температурой, фазами и фертильными днями\n\n"
            "🔮 <b>Прогноз фертильности</b> - анализ текущего состояния и прогноз следующей овуляции\n\n"
            "📅 <b>Текущая фаза</b> - определение текущей фазы менструального цикла\n\n"
            "<i>Для создания точного графика необходимо минимум 5-7 записей температуры</i>"
        )
        
        await message.answer(help_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Ошибка в handle_chart_request_button: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def handle_temperature_chart(callback_query: CallbackQuery):
    """Обработчик создания графика температуры"""
    try:
        user_id = callback_query.from_user.id
        
        # Показываем процесс
        await callback_query.message.edit_text("⏳ Создаю график температуры...")
        
        # Получаем данные пользователя за последний цикл (до 40 дней)
        records = await db.get_user_records(user_id, limit=40)
        
        if not records:
            await callback_query.message.edit_text(
                "📊 У вас пока нет записей для создания графика.\n"
                "Начните добавлять данные о температуре, чтобы увидеть график."
            )
            return
        
        # Фильтруем только записи с температурой
        temp_records = [r for r in records if r.get('temperature')]
        
        if len(temp_records) < 3:
            await callback_query.message.edit_text(
                "📊 Недостаточно данных о температуре для создания графика.\n"
                f"У вас {len(temp_records)} записей, нужно минимум 3.\n"
                "Продолжайте добавлять ежедневные измерения температуры."
            )
            return
        
        # Создаем график
        chart_buffer = await generate_fertility_chart(records, "temperature")
        
        if chart_buffer:
            # Отправляем график
            photo = BufferedInputFile(chart_buffer.getvalue(), filename="temperature_chart.png")
            
            current_phase = get_current_fertility_phase(records)
            
            caption = (
                f"📈 <b>График базальной температуры</b>\n\n"
                f"📅 Текущая фаза: <b>{current_phase}</b>\n"
                f"📊 Записей температуры: <b>{len(temp_records)}</b>\n"
                f"📝 Всего записей: <b>{len(records)}</b>\n\n"
                f"<i>График показывает изменения температуры с выделением фаз цикла:</i>\n"
                f"🔴 Менструация\n"
                f"🔵 Фолликулярная фаза\n"
                f"⭐ Овуляция\n"
                f"🟢 Лютеиновая фаза\n"
                f"🟠 Фертильные дни"
            )
            
            await callback_query.message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML"
            )
            
            await callback_query.message.delete()
        else:
            await callback_query.message.edit_text("❌ Не удалось создать график. Попробуйте позже.")
            
    except Exception as e:
        logging.error(f"Ошибка в handle_temperature_chart: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при создании графика.")

async def handle_summary_chart(callback_query: CallbackQuery):
    """Обработчик создания сводного графика"""
    try:
        user_id = callback_query.from_user.id
        
        await callback_query.message.edit_text("⏳ Создаю сводный график...")
        
        records = await db.get_user_records(user_id, limit=40)
        
        if not records:
            await callback_query.message.edit_text(
                "📊 У вас пока нет записей для создания графика."
            )
            return
        
        # Создаем сводный график
        chart_buffer = await generate_fertility_chart(records, "summary")
        
        if chart_buffer:
            photo = BufferedInputFile(chart_buffer.getvalue(), filename="summary_chart.png")
            
            # Получаем детальную информацию
            predictions = get_fertility_predictions(records)
            
            caption = (
                f"📊 <b>Сводный график цикла</b>\n\n"
                f"📅 Текущая фаза: <b>{predictions.get('current_phase', 'Неизвестно')}</b>\n"
                f"📏 Длина цикла: <b>{predictions.get('cycle_length', 0)} дней</b>\n"
                f"🟠 Фертильных дней: <b>{predictions.get('fertile_days_count', 0)}</b>\n"
            )
            
            if predictions.get('ovulation_day'):
                caption += f"⭐ День овуляции: <b>{predictions['ovulation_day']}</b>\n"
            
            if predictions.get('next_ovulation_estimate'):
                caption += f"🔮 Следующая овуляция (примерно): <b>{predictions['next_ovulation_estimate']}</b>\n"
            
            caption += (
                f"\n<i>Верхний график - температура с фазами\n"
                f"Нижний график - календарь фертильности</i>"
            )
            
            await callback_query.message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML"
            )
            
            await callback_query.message.delete()
        else:
            await callback_query.message.edit_text("❌ Не удалось создать график.")
            
    except Exception as e:
        logging.error(f"Ошибка в handle_summary_chart: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при создании графика.")

async def handle_fertility_prediction(callback_query: CallbackQuery):
    """Обработчик прогноза фертильности"""
    try:
        user_id = callback_query.from_user.id
        
        await callback_query.message.edit_text("🔮 Анализирую данные для прогноза...")
        
        records = await db.get_user_records(user_id, limit=40)
        
        if not records:
            await callback_query.message.edit_text(
                "🔮 Недостаточно данных для создания прогноза.\n"
                "Добавьте больше записей о температуре и других наблюдениях."
            )
            return
        
        # Получаем прогноз
        predictions = get_fertility_predictions(records)
        
        if predictions.get('error'):
            await callback_query.message.edit_text(f"❌ Ошибка анализа: {predictions['error']}")
            return
        
        # Формируем текст прогноза
        prediction_text = f"🔮 <b>Анализ фертильности</b>\n\n"
        
        # Текущая фаза
        prediction_text += f"📅 <b>Текущая фаза:</b> {predictions.get('current_phase', 'Неизвестно')}\n"
        
        # Длина цикла
        cycle_length = predictions.get('cycle_length', 0)
        if cycle_length > 0:
            prediction_text += f"📏 <b>Длина текущего цикла:</b> {cycle_length} дней\n"
        
        # Овуляция
        ovulation_day = predictions.get('ovulation_day')
        if ovulation_day:
            prediction_text += f"⭐ <b>День овуляции:</b> {ovulation_day}\n"
        else:
            prediction_text += f"⭐ <b>Овуляция:</b> не определена\n"
        
        # Фертильные дни
        fertile_count = predictions.get('fertile_days_count', 0)
        prediction_text += f"🟠 <b>Фертильных дней в цикле:</b> {fertile_count}\n"
        
        if predictions.get('fertile_days'):
            fertile_days_str = ", ".join(predictions['fertile_days'][-5:])  # Последние 5 дней
            prediction_text += f"📅 <b>Последние фертильные дни:</b> {fertile_days_str}\n"
        
        # Прогноз следующей овуляции
        if predictions.get('next_ovulation_estimate'):
            prediction_text += f"\n🔮 <b>Прогноз следующей овуляции:</b>\n{predictions['next_ovulation_estimate']}\n"
            prediction_text += f"<i>(примерная дата, основана на средней длине цикла)</i>\n"
        
        # Рекомендации
        prediction_text += f"\n💡 <b>Рекомендации:</b>\n"
        
        if cycle_length < 10:
            prediction_text += f"• Продолжайте ежедневные измерения температуры\n"
            prediction_text += f"• Добавляйте наблюдения за слизью и другими симптомами\n"
        elif ovulation_day is None:
            prediction_text += f"• Для точного определения овуляции нужно больше данных\n"
            prediction_text += f"• Измеряйте температуру каждое утро в одно время\n"
        else:
            prediction_text += f"• График показывает хорошую динамику\n"
            prediction_text += f"• Продолжайте регулярные наблюдения\n"
        
        # Создаем кнопки для дополнительных действий
        builder = InlineKeyboardBuilder()
        builder.button(text="📈 Посмотреть график", callback_data="chart_temperature")
        builder.button(text="📊 Сводный анализ", callback_data="chart_summary")
        builder.adjust(1)
        
        await callback_query.message.edit_text(
            prediction_text, 
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logging.error(f"Ошибка в handle_fertility_prediction: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при анализе данных.")

async def handle_current_phase(callback_query: CallbackQuery):
    """Обработчик определения текущей фазы"""
    try:
        user_id = callback_query.from_user.id
        
        await callback_query.message.edit_text("📅 Определяю текущую фазу...")
        
        records = await db.get_user_records(user_id, limit=40)
        
        if not records:
            await callback_query.message.edit_text(
                "📅 Недостаточно данных для определения фазы цикла.\n"
                "Добавьте записи о температуре и менструации."
            )
            return
        
        current_phase = get_current_fertility_phase(records)
        
        # Получаем дополнительную информацию
        temp_records = [r for r in records if r.get('temperature')]
        last_temp = temp_records[0].get('temperature') if temp_records else None
        last_date = records[0]['record_date'] if records else None
        
        phase_text = f"📅 <b>Анализ текущей фазы</b>\n\n"
        phase_text += f"🎯 <b>Текущая фаза:</b> {current_phase}\n"
        
        if last_date:
            if isinstance(last_date, str):
                date_obj = datetime.strptime(last_date, '%Y-%m-%d').date()
            else:
                date_obj = last_date
            phase_text += f"📆 <b>Последняя запись:</b> {date_obj.strftime('%d.%m.%Y')}\n"
        
        if last_temp:
            phase_text += f"🌡 <b>Последняя температура:</b> {last_temp}°C\n"
        
        phase_text += f"📊 <b>Всего записей:</b> {len(records)}\n"
        
        # Описание фаз
        phase_descriptions = {
            "Менструация": "🔴 Менструальная фаза - время месячных. Уровень гормонов низкий, температура обычно снижена.",
            "Фолликулярная": "🔵 Фолликулярная фаза - подготовка к овуляции. Температура низкая, организм готовится к овуляции.",
            "Овуляция": "⭐ Овуляция - самый фертильный период! Температура начинает повышаться после выхода яйцеклетки.",
            "Лютеиновая": "🟢 Лютеиновая фаза - после овуляции. Температура повышена, низкая вероятность зачатия.",
            "Неопределенная": "❓ Фаза не определена - нужно больше данных для точного анализа."
        }
        
        description = phase_descriptions.get(current_phase, "")
        if description:
            phase_text += f"\n💡 <b>Описание:</b>\n{description}\n"
        
        # Рекомендации по фазам
        recommendations = {
            "Менструация": "• Отдыхайте больше\n• Принимайте теплые ванны\n• Следите за интенсивностью кровотечения",
            "Фолликулярная": "• Продолжайте измерения температуры\n• Наблюдайте за изменениями слизи\n• Готовьтесь к фертильному периоду",
            "Овуляция": "• Самое фертильное время!\n• Обратите внимание на симптомы овуляции\n• Температура должна подняться в ближайшие дни",
            "Лютеиновая": "• Температура должна оставаться высокой\n• Наблюдайте за ПМС симптомами\n• До менструации примерно 12-16 дней",
            "Неопределенная": "• Продолжайте ежедневные измерения\n• Добавляйте все наблюдения\n• Для точного анализа нужно время"
        }
        
        recommendation = recommendations.get(current_phase, "")
        if recommendation:
            phase_text += f"\n🎯 <b>Рекомендации:</b>\n{recommendation}\n"
        
        # Кнопки для дополнительных действий
        builder = InlineKeyboardBuilder()
        builder.button(text="📈 График температуры", callback_data="chart_temperature")
        builder.button(text="🔮 Полный прогноз", callback_data="chart_prediction")
        builder.adjust(1)
        
        await callback_query.message.edit_text(
            phase_text, 
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logging.error(f"Ошибка в handle_current_phase: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при определении фазы.")

async def handle_chart_button(message: Message):
    """Обработчик кнопки быстрого доступа к графикам"""
    await handle_chart_request_button(message)

# Функция для регистрации обработчиков графиков
def register_chart_handlers(dp):
    """Регистрация всех обработчиков графиков"""
    
    # Обработчики коллбэков
    dp.callback_query.register(handle_temperature_chart, lambda c: c.data == "chart_temperature")
    dp.callback_query.register(handle_summary_chart, lambda c: c.data == "chart_summary")
    dp.callback_query.register(handle_fertility_prediction, lambda c: c.data == "chart_prediction")
    dp.callback_query.register(handle_current_phase, lambda c: c.data == "chart_current_phase")
    
    # Обработчики текстовых команд
    dp.message.register(handle_chart_request_button, F.text == "📊 Графики и анализ")
    dp.message.register(handle_chart_button, F.text == "📈 Мой график")
    
    logging.info("Обработчики графиков зарегистрированы")

# Автоматическое создание графиков для пользователей с достаточным количеством данных
async def send_automatic_chart_updates():
    """
    Функция для автоматической отправки графиков пользователям
    (может быть использована в планировщике задач)
    """
    try:
        # Здесь можно добавить логику для автоматической отправки
        # графиков пользователям, у которых накопилось достаточно данных
        logging.info("Проверка автоматических обновлений графиков...")
        
        # Пример: найти пользователей с новыми данными за последние 3 дня
        # и отправить им обновленные графики
        
    except Exception as e:
        logging.error(f"Ошибка автоматического обновления графиков: {e}")

# Функции для получения быстрой статистики
async def get_quick_fertility_status(user_id: int) -> str:
    """Быстрый статус фертильности для пользователя"""
    try:
        records = await db.get_user_records(user_id, limit=10)
        
        if not records:
            return "📊 Нет данных для анализа"
        
        current_phase = get_current_fertility_phase(records)
        temp_records = len([r for r in records if r.get('temperature')])
        
        status = f"📅 Фаза: {current_phase}\n"
        status += f"📊 Записей температуры: {temp_records}/10"
        
        return status
        
    except Exception as e:
        logging.error(f"Ошибка получения статуса: {e}")
        return "❌ Ошибка получения данных"