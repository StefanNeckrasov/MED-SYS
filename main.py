import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    sys.path.append(application_path)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(application_path)

from database import Database
from validators import Validators
from patient_card import PatientCardWindow

class MedicalDatabaseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Медицинская информационная система")
        self.root.geometry("1500x900")
        self.root.configure(bg="#f0f0f0")
        self.db = Database()
        self.create_widgets()
        self.show_records()

    def create_widgets(self):
        # Заголовок
        self.header_frame = tk.Frame(self.root, bg="#0056b3", height=80)
        self.header_frame.pack(fill=tk.X)
        tk.Label(self.header_frame, text="МЕДИЦИНСКАЯ ИНФОРМАЦИОННАЯ СИСТЕМА",
                 font=("Segoe UI", 22, "bold"), fg="white", bg="#0056b3").pack(pady=25)

        # Основной фрейм
        self.main_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Левая панель ввода
        self.input_frame = tk.LabelFrame(self.main_frame, text="Добавить новую запись",
                                         font=("Segoe UI", 13, "bold"), bg="#f0f0f0", fg="#0056b3")
        self.input_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))

        labels = [
            ("ФИО пациента:", "entry"),
            ("Номер истории болезни:", "entry"),
            ("Год рождения:", "entry"),
            ("Возраст (лет):", "entry"),
            ("Пол:", ["М", "Ж"]),
            ("Диагноз:", "entry"),
            ("Дата лечения (ДД-ММ-ГГГГ):", "entry"),
            ("Отделение:", "entry"),
            ("Давление (число):", "pressure"),
            ("Показания к использованию:", ["Плановое", "Срочное"]),
            ("Результат лечения:", "entry"),
            ("Количество сеансов:", "entry"),
            ("Количество курсов:", "entry"),
            ("Категория сложности:", "entry"),
            ("Осложнения:", "entry"),
            ("Эффект:", "entry"),
            ("Примечания:", "entry"),
        ]

        self.entries = {}
        for i, item in enumerate(labels):
            label_text, widget_type = item[0], item[1]
            tk.Label(self.input_frame, text=label_text, font=("Segoe UI", 10), bg="#f0f0f0")\
                .grid(row=i, column=0, sticky="w", padx=10, pady=5)

            if widget_type == "pressure":
                pressure_frame = tk.Frame(self.input_frame, bg="#f0f0f0")
                pressure_frame.grid(row=i, column=1, padx=10, pady=5, sticky="w")
                val_entry = tk.Entry(pressure_frame, width=8, font=("Segoe UI", 10))
                val_entry.pack(side=tk.LEFT)
                unit_combo = ttk.Combobox(pressure_frame, values=["ата", "ати"], width=5, state="readonly")
                unit_combo.pack(side=tk.LEFT, padx=5)
                unit_combo.set("")
                self.entries[label_text] = (val_entry, unit_combo)

            elif isinstance(widget_type, list):  # Combobox
                combo = ttk.Combobox(self.input_frame, values=widget_type, state="readonly", width=27)
                combo.grid(row=i, column=1, padx=10, pady=5, sticky="w")
                combo.set("")
                self.entries[label_text] = combo
            else:  # entry
                entry = tk.Entry(self.input_frame, width=30, font=("Segoe UI", 10))
                entry.grid(row=i, column=1, padx=10, pady=5)
                self.entries[label_text] = entry

        # Кнопки
        btn_frame = tk.Frame(self.input_frame, bg="#f0f0f0")
        btn_frame.grid(row=len(labels), column=0, columnspan=2, pady=20)
        tk.Button(btn_frame, text="Добавить запись", command=self.add_record,
                  bg="#007acc", fg="white", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=20, padx=10, pady=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Очистить поля", command=self.clear_entries,
                  bg="#6c757d", fg="white", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=15, padx=10, pady=8).pack(side=tk.LEFT, padx=5)

        # Правая панель (таблица)
        self.table_frame = tk.LabelFrame(self.main_frame, text="Медицинские записи",
                                         font=("Segoe UI", 13, "bold"), bg="#f0f0f0", fg="#0056b3")
        self.table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Поиск
        search_frame = tk.Frame(self.table_frame, bg="#f0f0f0")
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(search_frame, text="Селективный поиск:", font=("Segoe UI", 11, "bold"), bg="#f0f0f0")\
            .pack(side=tk.LEFT, padx=(0, 10))
        self.search_field_var = tk.StringVar(value="Все поля")
        fields = ["Все поля", "ФИО", "Номер истории", "Год рождения", "Возраст", "Пол", "Диагноз",
                  "Дата лечения", "Отделение", "Давление", "Результат", "Сеансы", "Курсы",
                  "Показания", "Категория сложности", "Осложнения", "Эффект", "Примечания"]
        ttk.Combobox(search_frame, textvariable=self.search_field_var, values=fields,
                     state="readonly", width=15).pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry = tk.Entry(search_frame, width=30, font=("Segoe UI", 10))
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self.search_records())
        tk.Button(search_frame, text="Найти", command=self.search_records,
                  bg="#28a745", fg="white", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=10).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(search_frame, text="Сбросить", command=self.reset_search,
                  bg="#ffc107", fg="black", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=10).pack(side=tk.LEFT)

        # Таблица
        columns = ("ID", "ФИО", "Пол", "Номер истории", "Год рожд.", "Возраст", "Диагноз",
                   "Дата лечения", "Отделение", "Давление", "Результат", "Сеансы", "Курсы")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
        widths = [40, 150, 50, 100, 70, 70, 120, 100, 100, 100, 120, 70, 70]
        for col, w in zip(columns, widths):
            self.tree.column(col, width=w, anchor="center")

        scroll_y = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self.table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scroll_y.set, xscroll=scroll_x.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree.bind('<Double-1>', self.open_patient_card)
        tk.Button(self.table_frame, text="Обновить данные", command=self.show_records,
                  bg="#0056b3", fg="white", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=15, padx=10, pady=8).pack(pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- Вспомогательные методы ---
    def open_patient_card(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        patient_id = item['values'][0]
        data = self.db.get_patient_by_id(patient_id)
        if data:
            PatientCardWindow(self.root, data, self.show_records, self.db)

    def add_record(self):
        try:
            full_name = self.entries["ФИО пациента:"].get().strip()
            case_number = self.entries["Номер истории болезни:"].get().strip()
            birth_year_str = self.entries["Год рождения:"].get().strip()
            age_str = self.entries["Возраст (лет):"].get().strip()
            gender = self.entries["Пол:"].get().strip()
            diagnosis = self.entries["Диагноз:"].get().strip()
            treatment_date = self.entries["Дата лечения (ДД-ММ-ГГГГ):"].get().strip()
            department = self.entries["Отделение:"].get().strip()

            # Давление
            val_entry, unit_combo = self.entries["Давление (число):"]
            pressure_value_str = val_entry.get().strip()
            pressure_unit = unit_combo.get().strip()

            indication = self.entries["Показания к использованию:"].get().strip()
            treatment_result = self.entries["Результат лечения:"].get().strip()
            sessions_str = self.entries["Количество сеансов:"].get().strip()
            courses_str = self.entries["Количество курсов:"].get().strip()
            complexity = self.entries["Категория сложности:"].get().strip()
            complications = self.entries["Осложнения:"].get().strip()
            effect = self.entries["Эффект:"].get().strip()
            notes = self.entries["Примечания:"].get().strip()

            if not full_name or not diagnosis or not treatment_date:
                messagebox.showerror("Ошибка", "ФИО, диагноз и дата лечения обязательны.")
                return

            # Валидация года и возраста
            if birth_year_str and not Validators.validate_year(birth_year_str):
                messagebox.showerror("Ошибка", "Год рождения должен быть целым числом от 1900 до 2100.")
                return
            if age_str and not Validators.validate_age(age_str):
                messagebox.showerror("Ошибка", "Возраст должен быть целым числом от 0 до 150.")
                return

            birth_year = int(birth_year_str) if birth_year_str else None
            age = int(age_str) if age_str else None

            if not Validators.validate_date(treatment_date):
                messagebox.showerror("Ошибка", "Дата лечения должна быть в формате ДД-ММ-ГГГГ.")
                return

            # Давление
            pressure_value = None
            if pressure_value_str:
                if not Validators.validate_pressure_value(pressure_value_str):
                    messagebox.showerror("Ошибка", "Давление должно быть положительным числом (целым или дробным).")
                    return
                if not pressure_unit:
                    messagebox.showerror("Ошибка", "Выберите единицу давления (ата/ати).")
                    return
                pressure_value = float(pressure_value_str)
            else:
                pressure_unit = None  # не задано – оба None

            # Сеансы/курсы (необязательные)
            sessions = int(sessions_str) if sessions_str else 0
            courses = int(courses_str) if courses_str else 0
            if sessions < 0 or courses < 0:
                raise ValueError("Количество не может быть отрицательным")

            patient_data = (
                full_name, case_number, birth_year, age, gender, diagnosis,
                treatment_date, department, pressure_value, pressure_unit,
                treatment_result, sessions, courses,
                indication, complexity, complications, effect, notes
            )
            self.db.add_patient(patient_data)
            self.clear_entries()
            self.show_records()
            messagebox.showinfo("Успех", "Запись успешно добавлена!")
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректные данные: {e}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при добавлении: {e}")

    def clear_entries(self):
        for key, widget in self.entries.items():
            if isinstance(widget, tuple):  # давление (entry, combo)
                widget[0].delete(0, tk.END)
                widget[1].set("")
            elif isinstance(widget, ttk.Combobox):
                widget.set("")
            elif isinstance(widget, tk.Entry):
                widget.delete(0, tk.END)

    def reset_search(self):
        self.search_entry.delete(0, tk.END)
        self.search_field_var.set("Все поля")
        self.show_records()

    def search_records(self):
        term = self.search_entry.get().strip()
        field = self.search_field_var.get()
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not term:
            self.show_records()
            return
        try:
            query, params = self._build_search_query(term, field)
            records = self.db.search_patients(query, params)
            for rec in records:
                self._insert_tree_row(rec)
            if not records:
                messagebox.showinfo("Результаты поиска", f"По запросу '{term}' ничего не найдено")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка поиска: {e}")

    def _build_search_query(self, term, field):
        if field == "Все поля":
            query = """
                SELECT * FROM patients
                WHERE LOWER(full_name) LIKE ?
                   OR case_number LIKE ?
                   OR CAST(birth_year AS TEXT) LIKE ?
                   OR CAST(age AS TEXT) LIKE ?
                   OR LOWER(gender) LIKE ?
                   OR LOWER(diagnosis) LIKE ?
                   OR treatment_date LIKE ?
                   OR LOWER(department) LIKE ?
                   OR CAST(pressure_value AS TEXT) LIKE ?
                   OR LOWER(pressure_unit) LIKE ?
                   OR LOWER(treatment_result) LIKE ?
                   OR CAST(sessions_count AS TEXT) LIKE ?
                   OR CAST(courses_count AS TEXT) LIKE ?
                   OR LOWER(indication) LIKE ?
                   OR LOWER(complexity) LIKE ?
                   OR LOWER(complications) LIKE ?
                   OR LOWER(effect) LIKE ?
                   OR LOWER(notes) LIKE ?
                ORDER BY id DESC
            """
            t = f"%{term.lower()}%"
            params = (t,) * 18
            return query, params
        else:
            mapping = {
                "ФИО": ("full_name", True),
                "Номер истории": ("case_number", False),
                "Год рождения": ("birth_year", False),
                "Возраст": ("age", False),
                "Пол": ("gender", True),
                "Диагноз": ("diagnosis", True),
                "Дата лечения": ("treatment_date", False),
                "Отделение": ("department", True),
                "Давление": ("pressure_value", False),
                "Результат": ("treatment_result", True),
                "Сеансы": ("sessions_count", False),
                "Курсы": ("courses_count", False),
                "Показания": ("indication", True),
                "Категория сложности": ("complexity", True),
                "Осложнения": ("complications", True),
                "Эффект": ("effect", True),
                "Примечания": ("notes", True),
            }
            db_field, is_text = mapping[field]
            if field == "Давление":
                query = """
                    SELECT * FROM patients
                    WHERE CAST(pressure_value AS TEXT) LIKE ?
                       OR LOWER(pressure_unit) LIKE ?
                    ORDER BY id DESC
                """
                return query, (f"%{term}%", f"%{term.lower()}%")
            else:
                if is_text:
                    query = f"SELECT * FROM patients WHERE LOWER({db_field}) LIKE ? ORDER BY id DESC"
                    params = (f"%{term.lower()}%",)
                else:
                    query = f"SELECT * FROM patients WHERE CAST({db_field} AS TEXT) LIKE ? ORDER BY id DESC"
                    params = (f"%{term}%",)
                return query, params

    def show_records(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        records = self.db.get_all_patients()
        for rec in records:
            self._insert_tree_row(rec)

    def _insert_tree_row(self, rec):
        # rec: (0:id, 1:full_name, 2:case_number, 3:birth_year, 4:age, 5:gender,
        #       6:diagnosis, 7:treatment_date, 8:department, 9:pressure_value,
        #       10:pressure_unit, 11:treatment_result, 12:sessions, 13:courses,
        #       14:indication, 15:complexity, 16:complications, 17:effect, 18:notes)
        pressure_display = ""
        if rec[9] is not None and rec[10] is not None:
            pressure_display = f"{rec[9]} {rec[10]}"
        values = (
            rec[0],          # ID
            rec[1],          # ФИО
            rec[5] or "",    # Пол
            rec[2] or "",    # Номер истории
            rec[3] or "",    # Год рождения
            rec[4] or "",    # Возраст
            rec[6] or "",    # Диагноз
            rec[7] or "",    # Дата лечения
            rec[8] or "",    # Отделение
            pressure_display,
            rec[11] or "",   # Результат
            rec[12] or 0,    # Сеансы
            rec[13] or 0,    # Курсы
        )
        self.tree.insert("", tk.END, values=values)

    def on_closing(self):
        self.db.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MedicalDatabaseApp(root)
    root.mainloop()