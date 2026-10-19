import sqlite3
import os
import sys

class Database:
    def __init__(self, db_name='medical_records.db'):
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.db_name = os.path.join(self.base_path, db_name)
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
        self.migrate_if_needed()

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
        except Exception as e:
            print("Ошибка подключения к БД:", e)
            raise

    def create_tables(self):
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    case_number TEXT,
                    birth_year INTEGER,
                    age INTEGER,
                    gender TEXT,
                    diagnosis TEXT,
                    treatment_start_date TEXT,
                    treatment_end_date TEXT,
                    department TEXT,
                    pressure_value REAL,
                    pressure_unit TEXT,
                    treatment_result TEXT,
                    sessions_count INTEGER DEFAULT 0,
                    courses_count INTEGER DEFAULT 0,
                    indication TEXT,
                    complications TEXT,
                    effect TEXT,
                    notes TEXT,
                    hidden INTEGER DEFAULT 0,
                    deleted INTEGER DEFAULT 0
                )
            ''')
            self.conn.commit()
        except Exception as e:
            print("Ошибка создания таблицы:", e)
            raise

    def migrate_if_needed(self):
        try:
            self.cursor.execute("PRAGMA table_info(patients)")
            columns = [row[1] for row in self.cursor.fetchall()]
            if 'hidden' not in columns:
                self.cursor.execute("ALTER TABLE patients ADD COLUMN hidden INTEGER DEFAULT 0")
                self.conn.commit()
                print("Миграция: добавлен столбец hidden.")
            if 'deleted' not in columns:
                self.cursor.execute("ALTER TABLE patients ADD COLUMN deleted INTEGER DEFAULT 0")
                self.conn.commit()
                print("Миграция: добавлен столбец deleted.")
        except Exception as e:
            print("Ошибка миграции:", e)

    def add_patient(self, patient_data):
        try:
            self.cursor.execute('''
                INSERT INTO patients (
                    full_name, case_number, birth_year, age, gender, diagnosis,
                    treatment_start_date, treatment_end_date, department,
                    pressure_value, pressure_unit,
                    treatment_result, sessions_count, courses_count,
                    indication, complications, effect, notes, hidden, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', patient_data + (0, 0))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print("Ошибка добавления пациента:", e)
            raise

    def get_patients_sorted(self, hidden=0, deleted=0, order_by="id DESC"):
        """
        Получить пациентов с учётом фильтров hidden и deleted.
        hidden: 0 — активные, 1 — архивные
        deleted: 0 — не удалённые, 1 — удалённые (корзина)
        """
        try:
            query = (
                f"SELECT * FROM patients "
                f"WHERE IFNULL(hidden, 0) = ? AND IFNULL(deleted, 0) = ? "
                f"ORDER BY {order_by}"
            )
            self.cursor.execute(query, (hidden, deleted))
            return self.cursor.fetchall()
        except Exception as e:
            print("Ошибка получения пациентов с сортировкой:", e)
            return []

    def get_patient_by_id(self, patient_id):
        try:
            self.cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
            return self.cursor.fetchone()
        except Exception as e:
            print("Ошибка получения пациента:", e)
            return None

    def update_patient(self, patient_id, patient_data, hidden=None, deleted=None):
        try:
            fields = '''
                full_name = ?, case_number = ?, birth_year = ?, age = ?,
                gender = ?, diagnosis = ?,
                treatment_start_date = ?, treatment_end_date = ?,
                department = ?, pressure_value = ?, pressure_unit = ?,
                treatment_result = ?, sessions_count = ?, courses_count = ?,
                indication = ?, complications = ?, effect = ?, notes = ?
            '''
            params = list(patient_data)
            if hidden is not None:
                fields += ", hidden = ?"
                params.append(hidden)
            if deleted is not None:
                fields += ", deleted = ?"
                params.append(deleted)
            params.append(patient_id)
            self.cursor.execute(f"UPDATE patients SET {fields} WHERE id = ?", params)
            self.conn.commit()
        except Exception as e:
            print("Ошибка обновления пациента:", e)
            raise

    def search_patients(self, query, params):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print("Ошибка поиска:", e)
            return []

    def archive_patient(self, patient_id):
        try:
            self.cursor.execute("UPDATE patients SET hidden = 1 WHERE id = ?", (patient_id,))
            self.conn.commit()
        except Exception as e:
            print("Ошибка архивирования пациента:", e)
            raise

    # ---------- Мягкое удаление ----------
    def soft_delete_patient(self, patient_id):
        """Пометить пациента как удалённого (переместить в корзину)."""
        try:
            self.cursor.execute("UPDATE patients SET deleted = 1 WHERE id = ?", (patient_id,))
            self.conn.commit()
            return self.cursor.rowcount
        except Exception as e:
            print("Ошибка мягкого удаления пациента:", e)
            raise

    def restore_patient(self, patient_id):
        """Восстановить пациента из корзины."""
        try:
            self.cursor.execute("UPDATE patients SET deleted = 0 WHERE id = ?", (patient_id,))
            self.conn.commit()
            return self.cursor.rowcount
        except Exception as e:
            print("Ошибка восстановления пациента:", e)
            raise

    def delete_patient_permanently(self, patient_id):
        """Безвозвратное удаление (для очистки корзины)."""
        try:
            self.cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
            self.conn.commit()
            return self.cursor.rowcount
        except Exception as e:
            print("Ошибка безвозвратного удаления пациента:", e)
            raise

    # ---------- Резервное копирование ----------
    def backup_to(self, target_path):
        """
        Безопасно создать резервную копию текущей БД в указанный файл
        через встроенный механизм sqlite3 backup API.
        Текущее соединение НЕ закрывается, данные не теряются.
        """
        try:
            target_conn = sqlite3.connect(target_path)
            try:
                self.conn.backup(target_conn)
            finally:
                target_conn.close()
            return True
        except Exception as e:
            print(f"Ошибка резервного копирования в {target_path}: {e}")
            return False

    def close(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception as e:
            print("Ошибка закрытия БД:", e)