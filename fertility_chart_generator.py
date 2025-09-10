"""
Модуль для создания графиков фертильности с анализом фаз цикла
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any
import io
import logging
from dataclasses import dataclass
from enum import Enum

# Настройка matplotlib для русского языка
plt.rcParams['font.family'] = ['DejaVu Sans', 'Liberation Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class FertilityPhase(Enum):
    """Фазы менструального цикла"""
    MENSTRUAL = "Менструация"
    FOLLICULAR = "Фолликулярная"
    OVULATION = "Овуляция"
    LUTEAL = "Лютеиновая"
    UNKNOWN = "Неопределенная"

@dataclass
class CycleDay:
    """Данные одного дня цикла"""
    date: date
    day_number: int
    temperature: Optional[float] = None
    mucus_type: Optional[str] = None
    menstruation_type: Optional[str] = None
    note: Optional[str] = None
    phase: FertilityPhase = FertilityPhase.UNKNOWN
    is_fertile: bool = False

class FertilityAnalyzer:
    """Анализатор фертильности для определения фаз цикла"""
    
    @staticmethod
    def detect_ovulation(temperatures: List[float], dates: List[date]) -> Tuple[Optional[int], List[FertilityPhase]]:
        """
        Определение овуляции по правилу симптотермального метода
        Возвращает индекс дня овуляции и фазы для каждого дня
        """
        if len(temperatures) < 6:
            return None, [FertilityPhase.UNKNOWN] * len(temperatures)
        
        phases = [FertilityPhase.UNKNOWN] * len(temperatures)
        ovulation_day = None
        
        # Ищем подъем температуры (правило 6 низких дней + 3 высоких)
        for i in range(6, len(temperatures)):
            if temperatures[i] is None:
                continue
            
            # Проверяем 6 предыдущих дней (низкие температуры)
            low_temps = [t for t in temperatures[i-6:i] if t is not None]
            if len(low_temps) < 3:  # Минимум 3 измерения из 6 дней
                continue
            
            avg_low = sum(low_temps) / len(low_temps)
            
            # Проверяем подъем на 0.2°C или больше
            if temperatures[i] >= avg_low + 0.2:
                # Проверяем, что следующие 2 дня тоже высокие
                high_days = 1
                for j in range(i + 1, min(i + 3, len(temperatures))):
                    if temperatures[j] is not None and temperatures[j] >= avg_low + 0.1:
                        high_days += 1
                
                if high_days >= 2:  # Минимум 2 высоких дня после подъема
                    ovulation_day = i - 1  # Овуляция за день до подъема
                    break
        
        # Назначаем фазы на основе найденной овуляции
        if ovulation_day is not None:
            for i in range(len(phases)):
                if i <= ovulation_day:
                    phases[i] = FertilityPhase.FOLLICULAR
                elif i == ovulation_day + 1:
                    phases[i] = FertilityPhase.OVULATION
                else:
                    phases[i] = FertilityPhase.LUTEAL
        else:
            # Если овуляция не найдена, назначаем фазы примерно
            mid_point = len(phases) // 2
            for i in range(len(phases)):
                if i < mid_point:
                    phases[i] = FertilityPhase.FOLLICULAR
                else:
                    phases[i] = FertilityPhase.LUTEAL
        
        return ovulation_day, phases
    
    @staticmethod
    def identify_menstrual_days(records: List[Dict]) -> List[bool]:
        """Определение дней менструации"""
        return [bool(record.get('menstruation_type')) for record in records]
    
    @staticmethod
    def calculate_fertile_window(ovulation_day: Optional[int], cycle_length: int) -> List[bool]:
        """Расчет фертильного окна (5 дней до + день овуляции + 1 день после)"""
        fertile_days = [False] * cycle_length
        
        if ovulation_day is not None:
            # Фертильное окно: 5 дней до овуляции, день овуляции и 1 день после
            start = max(0, ovulation_day - 5)
            end = min(cycle_length, ovulation_day + 2)
            
            for i in range(start, end):
                fertile_days[i] = True
        
        return fertile_days

class FertilityChartGenerator:
    """Генератор графиков фертильности"""
    
    def __init__(self):
        self.analyzer = FertilityAnalyzer()
        
    def process_cycle_data(self, records: List[Dict]) -> List[CycleDay]:
        """Обработка данных цикла"""
        if not records:
            return []
        
        # Сортируем записи по дате
        sorted_records = sorted(records, key=lambda x: x['record_date'])
        
        cycle_days = []
        temperatures = []
        dates = []
        
        for i, record in enumerate(sorted_records):
            record_date = record['record_date']
            if isinstance(record_date, str):
                record_date = datetime.strptime(record_date, '%Y-%m-%d').date()
            
            temp = record.get('temperature')
            if temp:
                temp = float(temp)
            
            cycle_day = CycleDay(
                date=record_date,
                day_number=i + 1,
                temperature=temp,
                mucus_type=record.get('mucus_type'),
                menstruation_type=record.get('menstruation_type'),
                note=record.get('note')
            )
            
            cycle_days.append(cycle_day)
            temperatures.append(temp)
            dates.append(record_date)
        
        # Анализ фаз
        ovulation_day, phases = self.analyzer.detect_ovulation(temperatures, dates)
        menstrual_days = self.analyzer.identify_menstrual_days(sorted_records)
        fertile_days = self.analyzer.calculate_fertile_window(ovulation_day, len(cycle_days))
        
        # Обновляем фазы и фертильность
        for i, day in enumerate(cycle_days):
            if menstrual_days[i]:
                day.phase = FertilityPhase.MENSTRUAL
            else:
                day.phase = phases[i] if i < len(phases) else FertilityPhase.UNKNOWN
            
            day.is_fertile = fertile_days[i] if i < len(fertile_days) else False
        
        return cycle_days
    
    def create_temperature_chart(self, cycle_data: List[CycleDay], title: str = "График базальной температуры") -> io.BytesIO:
        """Создание графика температуры с фазами"""
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Извлекаем данные
        dates = [day.date for day in cycle_data]
        temperatures = [day.temperature for day in cycle_data if day.temperature is not None]
        temp_dates = [day.date for day in cycle_data if day.temperature is not None]
        
        if not temperatures:
            # Создаем пустой график с сообщением
            ax.text(0.5, 0.5, 'Нет данных о температуре', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=16)
            ax.set_title(title, fontsize=16, fontweight='bold')
            
        else:
            # График температуры
            ax.plot(temp_dates, temperatures, 'o-', linewidth=2, markersize=6, 
                   color='#2E86AB', label='БТТ')
            
            # Цветовые зоны для фаз
            self._add_phase_backgrounds(ax, cycle_data, dates)
            
            # Отмечаем особые дни
            self._add_special_markers(ax, cycle_data)
            
            # Настройка осей
            ax.set_ylabel('Температура (°C)', fontsize=12)
            ax.set_title(title, fontsize=16, fontweight='bold')
            
            # Устанавливаем разумные пределы для температуры
            if temperatures:
                min_temp = min(temperatures) - 0.1
                max_temp = max(temperatures) + 0.1
                ax.set_ylim(min_temp, max_temp)
            
            # Форматируем ось дат
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            # Сетка
            ax.grid(True, alpha=0.3)
            
            # Легенда
            ax.legend(loc='upper right')
        
        # Добавляем информацию о текущей фазе
        current_phase = self._get_current_phase(cycle_data)
        phase_text = f"Текущая фаза: {current_phase.value}"
        ax.text(0.02, 0.98, phase_text, transform=ax.transAxes, 
               fontsize=12, verticalalignment='top',
               bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
        
        plt.tight_layout()
        
        # Сохраняем в BytesIO
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='PNG', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close(fig)
        
        return img_buffer
    
    def _add_phase_backgrounds(self, ax, cycle_data: List[CycleDay], dates: List[date]):
        """Добавление цветных фонов для фаз цикла"""
        phase_colors = {
            FertilityPhase.MENSTRUAL: '#FF6B6B',      # Красный
            FertilityPhase.FOLLICULAR: '#4ECDC4',      # Бирюзовый
            FertilityPhase.OVULATION: '#45B7D1',       # Синий
            FertilityPhase.LUTEAL: '#96CEB4',          # Зеленый
            FertilityPhase.UNKNOWN: '#CCCCCC'          # Серый
        }
        
        if not dates:
            return
        
        current_phase = None
        phase_start = dates[0]
        
        for i, day in enumerate(cycle_data):
            if day.phase != current_phase:
                # Завершаем предыдущую фазу
                if current_phase is not None:
                    ax.axvspan(phase_start, day.date, 
                             alpha=0.2, color=phase_colors.get(current_phase, '#CCCCCC'))
                
                # Начинаем новую фазу
                current_phase = day.phase
                phase_start = day.date
        
        # Завершаем последнюю фазу
        if current_phase is not None:
            ax.axvspan(phase_start, dates[-1], 
                     alpha=0.2, color=phase_colors.get(current_phase, '#CCCCCC'))
    
    def _add_special_markers(self, ax, cycle_data: List[CycleDay]):
        """Добавление специальных маркеров"""
        for day in cycle_data:
            if day.temperature is None:
                continue
            
            # Маркер овуляции
            if day.phase == FertilityPhase.OVULATION:
                ax.scatter(day.date, day.temperature, s=100, c='red', 
                          marker='*', zorder=5, label='Овуляция' if not hasattr(ax, '_ovulation_marked') else "")
                ax._ovulation_marked = True
            
            # Маркер фертильных дней
            if day.is_fertile and day.phase != FertilityPhase.OVULATION:
                ax.scatter(day.date, day.temperature, s=60, c='orange', 
                          marker='o', alpha=0.7, zorder=4, 
                          label='Фертильные дни' if not hasattr(ax, '_fertile_marked') else "")
                ax._fertile_marked = True
            
            # Маркер менструации
            if day.phase == FertilityPhase.MENSTRUAL:
                ax.scatter(day.date, day.temperature, s=80, c='darkred', 
                          marker='s', zorder=4, 
                          label='Менструация' if not hasattr(ax, '_menstrual_marked') else "")
                ax._menstrual_marked = True
    
    def _get_current_phase(self, cycle_data: List[CycleDay]) -> FertilityPhase:
        """Определение текущей фазы (последний день с данными)"""
        if not cycle_data:
            return FertilityPhase.UNKNOWN
        
        # Ищем последний день с данными
        for day in reversed(cycle_data):
            if day.temperature is not None or day.menstruation_type:
                return day.phase
        
        return cycle_data[-1].phase if cycle_data else FertilityPhase.UNKNOWN
    
    def create_cycle_summary_chart(self, cycle_data: List[CycleDay]) -> io.BytesIO:
        """Создание сводного графика цикла"""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), height_ratios=[3, 1])
        
        # Верхний график - температура
        dates = [day.date for day in cycle_data]
        temperatures = [day.temperature for day in cycle_data if day.temperature is not None]
        temp_dates = [day.date for day in cycle_data if day.temperature is not None]
        
        if temperatures:
            ax1.plot(temp_dates, temperatures, 'o-', linewidth=2, markersize=6, 
                    color='#2E86AB', label='БТТ')
            
            self._add_phase_backgrounds(ax1, cycle_data, dates)
            self._add_special_markers(ax1, cycle_data)
            
            ax1.set_ylabel('Температура (°C)', fontsize=12)
            ax1.set_title('График базальной температуры с фазами цикла', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
        
        # Нижний график - фазы и фертильность
        phase_colors = {
            FertilityPhase.MENSTRUAL: '#FF6B6B',
            FertilityPhase.FOLLICULAR: '#4ECDC4',
            FertilityPhase.OVULATION: '#45B7D1',
            FertilityPhase.LUTEAL: '#96CEB4',
            FertilityPhase.UNKNOWN: '#CCCCCC'
        }
        
        for day in cycle_data:
            color = phase_colors.get(day.phase, '#CCCCCC')
            height = 1.0
            
            if day.is_fertile:
                height = 1.5
            
            if day.phase == FertilityPhase.MENSTRUAL:
                height = 0.8
            
            ax2.bar(day.date, height, color=color, alpha=0.7, width=0.8)
        
        ax2.set_ylabel('Фазы цикла', fontsize=12)
        ax2.set_ylim(0, 2)
        ax2.set_yticks([0.4, 0.8, 1.2, 1.6])
        ax2.set_yticklabels(['', 'Менструация', 'Обычные дни', 'Фертильные дни'])
        
        # Форматируем оси дат для обоих графиков
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        # Информация о цикле
        cycle_info = self._get_cycle_info(cycle_data)
        info_text = f"Длина цикла: {cycle_info['length']} дней\n"
        info_text += f"Текущая фаза: {cycle_info['current_phase']}\n"
        info_text += f"Фертильных дней: {cycle_info['fertile_days']}"
        
        ax1.text(0.02, 0.98, info_text, transform=ax1.transAxes, 
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
        
        plt.tight_layout()
        
        # Сохраняем в BytesIO
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='PNG', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close(fig)
        
        return img_buffer
    
    def _get_cycle_info(self, cycle_data: List[CycleDay]) -> Dict[str, Any]:
        """Получение информации о цикле"""
        if not cycle_data:
            return {
                'length': 0,
                'current_phase': 'Неопределенная',
                'fertile_days': 0
            }
        
        length = len(cycle_data)
        current_phase = self._get_current_phase(cycle_data).value
        fertile_days = sum(1 for day in cycle_data if day.is_fertile)
        
        return {
            'length': length,
            'current_phase': current_phase,
            'fertile_days': fertile_days
        }

# Функции для интеграции с ботом
async def generate_fertility_chart(records: List[Dict], chart_type: str = "temperature") -> Optional[io.BytesIO]:
    """
    Генерация графика фертильности
    
    Args:
        records: Список записей из базы данных
        chart_type: Тип графика ("temperature" или "summary")
    
    Returns:
        BytesIO объект с изображением графика или None при ошибке
    """
    try:
        generator = FertilityChartGenerator()
        cycle_data = generator.process_cycle_data(records)
        
        if not cycle_data:
            logging.warning("Нет данных для создания графика")
            return None
        
        if chart_type == "summary":
            return generator.create_cycle_summary_chart(cycle_data)
        else:
            return generator.create_temperature_chart(cycle_data)
            
    except Exception as e:
        logging.error(f"Ошибка создания графика: {e}")
        return None

def get_current_fertility_phase(records: List[Dict]) -> str:
    """Получение текущей фазы фертильности"""
    try:
        generator = FertilityChartGenerator()
        cycle_data = generator.process_cycle_data(records)
        
        if not cycle_data:
            return "Нет данных"
        
        current_phase = generator._get_current_phase(cycle_data)
        return current_phase.value
        
    except Exception as e:
        logging.error(f"Ошибка определения фазы: {e}")
        return "Ошибка"

def get_fertility_predictions(records: List[Dict]) -> Dict[str, Any]:
    """Получение прогнозов фертильности"""
    try:
        generator = FertilityChartGenerator()
        cycle_data = generator.process_cycle_data(records)
        
        if not cycle_data:
            return {"error": "Нет данных"}
        
        # Находим овуляцию и фертильные дни
        ovulation_day = None
        fertile_days = []
        
        for i, day in enumerate(cycle_data):
            if day.phase == FertilityPhase.OVULATION:
                ovulation_day = i + 1
            if day.is_fertile:
                fertile_days.append(day.date.strftime('%d.%m.%Y'))
        
        # Прогноз следующей овуляции (примерно)
        if cycle_data:
            last_date = cycle_data[-1].date
            next_ovulation = last_date + timedelta(days=14)  # Примерная оценка
        else:
            next_ovulation = None
        
        return {
            "current_phase": generator._get_current_phase(cycle_data).value,
            "cycle_length": len(cycle_data),
            "ovulation_day": ovulation_day,
            "fertile_days": fertile_days,
            "next_ovulation_estimate": next_ovulation.strftime('%d.%m.%Y') if next_ovulation else None,
            "fertile_days_count": len(fertile_days)
        }
        
    except Exception as e:
        logging.error(f"Ошибка создания прогноза: {e}")
        return {"error": str(e)}

# Пример использования
if __name__ == "__main__":
    # Тестовые данные
    test_records = [
        {"record_date": "2024-01-01", "temperature": 36.2, "menstruation_type": "Средние"},
        {"record_date": "2024-01-02", "temperature": 36.1, "menstruation_type": "Средние"},
        {"record_date": "2024-01-03", "temperature": 36.0, "menstruation_type": "Слабые"},
        {"record_date": "2024-01-04", "temperature": 36.1, "menstruation_type": None},
        {"record_date": "2024-01-05", "temperature": 36.0, "menstruation_type": None},
        {"record_date": "2024-01-10", "temperature": 36.2, "menstruation_type": None},
        {"record_date": "2024-01-15", "temperature": 36.6, "menstruation_type": None},
        {"record_date": "2024-01-16", "temperature": 36.7, "menstruation_type": None},
        {"record_date": "2024-01-20", "temperature": 36.8, "menstruation_type": None},
    ]
    
    # Создание графика
    chart = generate_fertility_chart(test_records, "summary")
    if chart:
        with open("test_fertility_chart.png", "wb") as f:
            f.write(chart.getvalue())
        print("График сохранен как test_fertility_chart.png")
    
    # Получение прогноза
    predictions = get_fertility_predictions(test_records)
    print("Прогноз:", predictions)