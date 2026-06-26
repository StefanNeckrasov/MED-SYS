import tkinter as tk
from tkinter import ttk, messagebox
import os, sys, tempfile, subprocess

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    sys.path.append(application_path)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(application_path)

from validators import Validators

class PatientCardWindow:
    def __init__(self, parent, patient_data, callback, db):
        self.parent = parent
        self.patient_data = patient_data
        self.callback = callback
        self.db = db
        self.is_archived = (patient_data[19] == 1) if len(patient_data) > 19 else False  # hidden поле
        self.window = tk.Toplevel(parent)
        self.window.title(f"Карточка пациента: {patient_data[1]}")
        self.window.geometry("700x800")
        self.window.configure(bg="#f0f0f0")
        self.window.resizable(True, True)
        self.center_window()
        self.create_widgets()
        self.fill_data()

    def center_window(self):
        self.window.update_idletasks()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (w // 2)
        y = (self.window.winfo_screenheight() // 2) - (h // 2)
        self.window.geometry(f'{w}x{h}+{x}+{y}')

    def create_widgets(self):
        # Заголовок
        hf = tk.Frame(self.window, bg="#0056b3", height=60)
        hf.pack(fill=tk.X, pady=(0,10))
        tk.Label(hf, text="КАРТОЧКА ПАЦИЕНТА", font=("Segoe UI", 16, "bold"),
                 fg="white", bg="#0056b3").pack(pady=15)

        main = tk.Frame(self.window, bg="#f0f0f0")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        canvas = tk.Canvas(main, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Поля (аналогично main)
        labels = [
            ("ID пациента:", "readonly"),
            ("Номер истории болезни:", "entry"),
            ("ФИО пациента:", "entry"),
            ("Год рождения:", "entry"),
            ("Возраст (лет):", "entry"),
            ("Пол:", ["М", "Ж", "Другой"]),
            ("Диагноз:", "text"),
            ("Дата начала лечения (ДД-ММ-ГГГГ):", "entry"),
            ("Дата окончания лечения (ДД-ММ-ГГГГ):", "entry"),
            ("Отделение:", ["1 реанимационное", "2 реанимационное", "3 реанимационное",
                           "1 хирургическое", "2 хирургическое", "3 хирургическое",
                           "1 урологическое", "2 урологическое", "нейрохирургическое",
                           "колопроктологическое", "травматолог ортопедическое",
                           "гинекологическое", "оториноларингологическое",
                           "отделение челюстно-лицевой хирургии", "офтальмологическое",
                           "амбулаторное", "неврологическое", "1 кардиологиологическое", 
                           "2 кардиологическое", "1 терапевтическое", "2 терапевтическое", 
                           "ревматологическое", "химиотерапевтическое", "гастроэнтерологическое", "пульмонологическое"]),
            ("Давление (число):", "pressure"),
            ("Показания к использованию:", ["Плановое", "Срочное"]),
            ("Результат лечения:", "entry"),
            ("Количество сеансов:", "entry"),
            ("Номер курса:", "entry"),
            ("Осложнения:", ["нет", "есть", "бароевстахеит", "бароотит", "кислородная интоксикация", "поражение лёгких"]),
            ("Эффект:", ["хороший", "удовлетворительный", "без эффекта", "отрицательный", "неопределённый"]),
            ("Примечания:", "text"),
        ]

        self.entries = {}
        self.row = 0
        for label_text, widget_type in labels:
            tk.Label(self.scrollable_frame, text=label_text, font=("Segoe UI", 10, "bold"),
                     bg="#f0f0f0", anchor="w").grid(row=self.row, column=0, sticky="w", padx=10, pady=8)

            if widget_type == "readonly":
                ent = tk.Entry(self.scrollable_frame, state="readonly", bg="#e9ecef",
                               width=30, font=("Segoe UI", 10))
                ent.grid(row=self.row, column=1, padx=10, pady=8, sticky="w")
                self.entries[label_text] = ent
            elif widget_type == "pressure":
                frame = tk.Frame(self.scrollable_frame, bg="#f0f0f0")
                frame.grid(row=self.row, column=1, padx=10, pady=8, sticky="w")
                val_entry = tk.Entry(frame, width=8, font=("Segoe UI", 10))
                val_entry.pack(side=tk.LEFT)
                unit_combo = ttk.Combobox(frame, values=["ата", "ати"], width=5, state="readonly")
                unit_combo.pack(side=tk.LEFT, padx=5)
                self.entries[label_text] = (val_entry, unit_combo)
            elif isinstance(widget_type, list):
                combo = ttk.Combobox(self.scrollable_frame, values=widget_type, state="readonly", width=27)
                combo.grid(row=self.row, column=1, padx=10, pady=8, sticky="w")
                self.entries[label_text] = combo
            elif widget_type == "text":
                text = tk.Text(self.scrollable_frame, width=40, height=4, font=("Segoe UI", 10), wrap=tk.WORD)
                text.grid(row=self.row, column=1, padx=10, pady=8, sticky="w")
                scroll_text = ttk.Scrollbar(self.scrollable_frame, orient=tk.VERTICAL, command=text.yview)
                text['yscrollcommand'] = scroll_text.set
                scroll_text.grid(row=self.row, column=2, sticky="ns")
                self.entries[label_text] = text
            else:
                ent = tk.Entry(self.scrollable_frame, width=30, font=("Segoe UI", 10))
                ent.grid(row=self.row, column=1, padx=10, pady=8, sticky="w")
                self.entries[label_text] = ent
            self.row += 1

        # Кнопки
        btn_frame = tk.Frame(self.scrollable_frame, bg="#f0f0f0")
        btn_frame.grid(row=self.row, column=0, columnspan=2, pady=20)

        # Стандартные кнопки
        tk.Button(btn_frame, text="💾 Сохранить изменения", command=self.save_changes,
                  bg="#28a745", fg="white", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=20, padx=10, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Кнопка "Закрыть и сохранить" (архивирует)
        tk.Button(btn_frame, text="📥 Закрыть и сохранить", command=self.close_and_save,
                  bg="#ffc107", fg="black", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=20, padx=10, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Новая кнопка "Вернуть из архива" – показываем только для архивных записей
        if self.is_archived:
            tk.Button(btn_frame, text="↩ Вернуть из архива", command=self.restore_from_archive,
                      bg="#007bff", fg="white", font=("Segoe UI", 11, "bold"),
                      relief="flat", width=18, padx=10, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="🖨 Печать", command=self.print_card,
                  bg="#17a2b8", fg="white", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=15, padx=10, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="✖ Отмена", command=self.window.destroy,
                  bg="#6c757d", fg="white", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=15, padx=10, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

    def fill_data(self):
        """Заполнение полей данными пациента."""
        try:
            p = self.patient_data
            # ID
            e = self.entries["ID пациента:"]
            e.configure(state="normal")
            e.delete(0, tk.END)
            e.insert(0, str(p[0]))
            e.configure(state="readonly")
            # Остальные поля
            self._set_entry("Номер истории болезни:", p[2])
            self._set_entry("ФИО пациента:", p[1])
            self._set_entry("Год рождения:", p[3])
            self._set_entry("Возраст (лет):", p[4])
            self._set_combo("Пол:", p[5])
            self._set_text("Диагноз:", p[6])
            self._set_entry("Дата начала лечения (ДД-ММ-ГГГГ):", p[7])
            self._set_entry("Дата окончания лечения (ДД-ММ-ГГГГ):", p[8])
            self._set_combo("Отделение:", p[9])
            if p[10] is not None and p[11] is not None:
                self.entries["Давление (число):"][0].delete(0, tk.END)
                self.entries["Давление (число):"][0].insert(0, str(p[10]))
                self.entries["Давление (число):"][1].set(p[11])
            else:
                self.entries["Давление (число):"][0].delete(0, tk.END)
                self.entries["Давление (число):"][1].set("")
            self._set_combo("Показания к использованию:", p[15])
            self._set_entry("Результат лечения:", p[12])
            self._set_entry("Количество сеансов:", p[13] if p[13] else 0)
            self._set_entry("Номер курса:", p[14] if p[14] else 0)
            self._set_combo("Осложнения:", p[16])
            self._set_combo("Эффект:", p[17])
            self._set_text("Примечания:", p[18])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке данных: {e}")

    def _set_entry(self, label, value):
        self.entries[label].delete(0, tk.END)
        self.entries[label].insert(0, str(value) if value is not None else "")

    def _set_combo(self, label, value):
        """Устанавливает значение комбобокса, только если оно есть в списке допустимых."""
        combo = self.entries[label]
        if value and value in combo['values']:
            combo.set(value)
        else:
            combo.set("")   # сбрасываем, чтобы не было невалидного значения

    def _set_text(self, label, value):
        widget = self.entries[label]
        widget.delete("1.0", tk.END)
        if value:
            widget.insert("1.0", value)

    def _get_text(self, label):
        widget = self.entries[label]
        return widget.get("1.0", "end-1c").strip()

    def _validate_and_prepare(self):
        """Проверка полей и сбор кортежа данных для сохранения. Возвращает данные или None при ошибке."""
        try:
            full_name = self.entries["ФИО пациента:"].get().strip()
            case_number = self.entries["Номер истории болезни:"].get().strip()
            birth_year_str = self.entries["Год рождения:"].get().strip()
            age_str = self.entries["Возраст (лет):"].get().strip()
            gender = self.entries["Пол:"].get().strip()
            diagnosis = self._get_text("Диагноз:")
            treatment_start_date = self.entries["Дата начала лечения (ДД-ММ-ГГГГ):"].get().strip()
            treatment_end_date = self.entries["Дата окончания лечения (ДД-ММ-ГГГГ):"].get().strip()
            department = self.entries["Отделение:"].get().strip()
            val_entry, unit_combo = self.entries["Давление (число):"]
            pressure_str = val_entry.get().strip()
            pressure_unit = unit_combo.get().strip()
            indication = self.entries["Показания к использованию:"].get().strip()
            treatment_result = self.entries["Результат лечения:"].get().strip()
            sessions_str = self.entries["Количество сеансов:"].get().strip()
            courses_str = self.entries["Номер курса:"].get().strip()
            complications = self.entries["Осложнения:"].get().strip()
            effect = self.entries["Эффект:"].get().strip()
            notes = self._get_text("Примечания:")

            if not full_name or not diagnosis:
                messagebox.showerror("Ошибка", "ФИО и диагноз обязательны.")
                return None
            if not treatment_start_date:
                messagebox.showerror("Ошибка", "Введите дату начала лечения.")
                return None
            if birth_year_str and not Validators.validate_year(birth_year_str):
                messagebox.showerror("Ошибка", "Год рождения должен быть целым числом от 1900 до 2100.")
                return None
            if age_str and not Validators.validate_age(age_str):
                messagebox.showerror("Ошибка", "Возраст должен быть целым числом от 0 до 150.")
                return None
            birth_year = int(birth_year_str) if birth_year_str else None
            age = int(age_str) if age_str else None
            if not Validators.validate_date(treatment_start_date):
                messagebox.showerror("Ошибка", "Дата начала лечения должна быть в формате ДД-ММ-ГГГГ.")
                return None
            if treatment_end_date and not Validators.validate_date(treatment_end_date):
                messagebox.showerror("Ошибка", "Дата окончания лечения должна быть в формате ДД-ММ-ГГГГ.")
                return None
            pressure_value = None
            if pressure_str:
                if not Validators.validate_pressure_value(pressure_str):
                    messagebox.showerror("Ошибка", "Давление должно быть положительным числом.")
                    return None
                if not pressure_unit:
                    messagebox.showerror("Ошибка", "Выберите единицу давления.")
                    return None
                pressure_value = float(pressure_str)
            else:
                pressure_unit = None
            sessions = int(sessions_str) if sessions_str else 0
            courses = int(courses_str) if courses_str else 0
            if sessions < 0 or courses < 0:
                raise ValueError("Количество не может быть отрицательным")

            updated_data = (
                full_name, case_number, birth_year, age, gender, diagnosis,
                treatment_start_date, treatment_end_date, department,
                pressure_value, pressure_unit,
                treatment_result, sessions, courses,
                indication, complications, effect, notes
            )
            return updated_data
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректные данные: {e}")
            return None
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при проверке данных: {e}")
            return None

    def _save_changes(self, hidden=None):
        """Фактическое сохранение в БД. hidden = 0/1 или None."""
        updated_data = self._validate_and_prepare()
        if updated_data is None:
            return False
        self.db.update_patient(self.patient_data[0], updated_data, hidden=hidden)
        return True

    def save_changes(self):
        """Обычное сохранение без архивирования."""
        if self._save_changes(hidden=0):
            messagebox.showinfo("Успех", "Данные пациента обновлены.")
            self.callback()
            self.window.destroy()

    def close_and_save(self):
        """Сохранить и переместить в архив (скрыть из основного списка)."""
        if self._save_changes(hidden=1):
            messagebox.showinfo("Успех", "Пациент сохранён и перемещён в архив.")
            self.callback()
            self.window.destroy()

    def restore_from_archive(self):
        """Вернуть пациента из архива (сделать видимым)."""
        if self._save_changes(hidden=0):
            messagebox.showinfo("Успех", "Пациент возвращён из архива.")
            self.callback()
            self.window.destroy()

    def print_card(self):
        """Формирование печатного представления и отправка на принтер."""
        data = self.patient_data
        lines = [
            "Карточка пациента",
            "==================",
            f"ID: {data[0]}",
            f"Номер истории: {data[2] or '-'}",
            f"ФИО: {data[1]}",
            f"Год рождения: {data[3] or '-'}",
            f"Возраст: {data[4] or '-'}",
            f"Пол: {data[5] or '-'}",
            f"Диагноз: {data[6] or '-'}",
            f"Дата начала лечения: {data[7] or '-'}",
            f"Дата окончания лечения: {data[8] or '-'}",
            f"Отделение: {data[9] or '-'}",
            f"Давление: {f'{data[10]} {data[11]}' if data[10] is not None else '-'}",
            f"Показания: {data[15] or '-'}",
            f"Результат лечения: {data[12] or '-'}",
            f"Сеансы: {data[13] if data[13] else 0}",
            f"Номер курса: {data[14] if data[14] else 0}",
            f"Осложнения: {data[16] or '-'}",
            f"Эффект: {data[17] or '-'}",
            f"Примечания: {data[18] or '-'}",
        ]
        content = "\n".join(lines)

        temp_file = os.path.join(tempfile.gettempdir(), "patient_card.txt")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content)

        try:
            if sys.platform == "win32":
                os.startfile(temp_file, "print")
            else:
                subprocess.run(["lp", temp_file], check=True)
        except Exception as e:
            messagebox.showerror("Ошибка печати", f"Не удалось отправить на печать: {e}")