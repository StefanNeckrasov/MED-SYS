import re
from datetime import datetime

class Validators:
    @staticmethod
    def validate_date(date_str):
        """Проверка формата даты ДД-ММ-ГГГГ."""
        if not date_str:
            return True
        if not re.match(r'^\d{2}-\d{2}-\d{4}$', date_str):
            return False
        try:
            datetime.strptime(date_str, '%d-%m-%Y')
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_pressure_value(value_str):
        """Проверка, что строка содержит положительное число (целое или с плавающей точкой)."""
        if not value_str:
            return False
        try:
            val = float(value_str)
            if val <= 0:
                return False
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_year(year_str):
        """Год должен быть целым числом в диапазоне 1900..2100."""
        if not year_str:
            return False
        try:
            y = int(year_str)
            return 1900 <= y <= 2100
        except ValueError:
            return False

    @staticmethod
    def validate_age(age_str):
        """Возраст – целое от 0 до 150."""
        if not age_str:
            return False
        try:
            a = int(age_str)
            return 0 <= a <= 150
        except ValueError:
            return False

    @staticmethod
    def validate_positive_number(value_str, allow_zero=True):
        """Общая проверка неотрицательного целого."""
        try:
            if not value_str:
                return True, 0 if allow_zero else None
            value = int(value_str)
            if allow_zero:
                if value >= 0:
                    return True, value
            else:
                if value > 0:
                    return True, value
            return False, None
        except ValueError:
            return False, None