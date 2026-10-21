import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import shutil
import json
from datetime import datetime

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    sys.path.append(application_path)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(application_path)

from database import Database
from validators import Validators
from patient_card import PatientCardWindow


# ---------- Настройки авто-бэкапа ----------
CONFIG_FILE_NAME = "settings.json"
BACKUP_DIR_NAME = "backups"
DEFAULT_CONFIG = {
    "backup_interval_minutes": 10,   # 0 = отключено
    "auto_backup_on_start": True,
    "max_auto_backups": 20
}


def load_config(base_path):
    """Загружает настройки из settings.json, дополняя их значениями по умолчанию."""
    config_path = os.path.join(base_path, CONFIG_FILE_NAME)
    config = dict(DEFAULT_CONFIG)
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k in DEFAULT_CONFIG:
                    if k in data:
                        config[k] = data[k]
    except Exception as e:
        print(f"Ошибка загрузки настроек: {e}")
    return config


def save_config(base_path, config):
    """Сохраняет настройки в settings.json."""
    config_path = os.path.join(base_path, CONFIG_FILE_NAME)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Ошибка сохранения настроек: {e}")
        return False


class MedicalDatabaseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Медицинская информационная система")
        self.root.configure(bg="#f0f0f0")

        # --- Подстраиваемся под разрешение экрана (важно для Win7 с малым экраном) ---
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1500, screen_w - 40)
        win_h = min(950, screen_h - 80)
        x = (screen_w - win_w) // 2
        y = max(0, (screen_h - win_h) // 2 - 20)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self.db = Database()
        self.show_archived = False
        self.show_deleted = False
        self.current_order = "id DESC"

        # --- Конфиг и папка бэкапов ---
        self.config = load_config(self.db.base_path)
        self.backup_dir = os.path.join(self.db.base_path, BACKUP_DIR_NAME)
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
        except Exception as e:
            print(f"Не удалось создать папку бэкапов: {e}")

        self._backup_timer_id = None
        self._settings_window = None

        self.create_widgets()
        self.show_records()

        # --- Стартовый бэкап и планирование ---
        if self.config.get("auto_backup_on_start", True):
            self.auto_backup()
        self.reschedule_backup()

    def create_widgets(self):
        # ===== Заголовок с кнопкой настроек справа =====
        self.header_frame = tk.Frame(self.root, bg="#0056b3", height=80)
        self.header_frame.pack(fill=tk.X)

        # ВАЖНО: сначала пакуем кнопку с side=tk.RIGHT — она резервирует место
        # у правого края, а заголовок потом займёт оставшееся пространство.
        tk.Button(self.header_frame, text="⚙  Настройки", command=self.open_settings,
                  bg="#0056b3", fg="white", font=("Segoe UI", 11, "bold"),
                  activebackground="#004494", activeforeground="white",
                  relief="flat", bd=0, padx=20, pady=10, cursor="hand2")\
            .pack(side=tk.RIGHT, padx=(0, 20), pady=20)

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
            elif isinstance(widget_type, list):
                combo = ttk.Combobox(self.input_frame, values=widget_type, state="readonly", width=27)
                combo.grid(row=i, column=1, padx=10, pady=5, sticky="w")
                combo.set("")
                self.entries[label_text] = combo
            else:
                entry = tk.Entry(self.input_frame, width=30, font=("Segoe UI", 10))
                entry.grid(row=i, column=1, padx=10, pady=5)
                self.entries[label_text] = entry

        # Кнопки добавления/очистки
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

        # Панель управления
        control_frame = tk.Frame(self.table_frame, bg="#f0f0f0")
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        # Поиск
        tk.Label(control_frame, text="Поиск:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0")\
            .pack(side=tk.LEFT, padx=(0, 5))
        self.search_field_var = tk.StringVar(value="Все поля")
        fields = ["Все поля", "ФИО", "Номер истории", "Год рождения", "Возраст", "Пол", "Диагноз",
                  "Дата начала", "Дата окончания", "Отделение", "Давление", "Результат", "Сеансы", "Номер курса",
                  "Показания", "Осложнения", "Эффект", "Примечания"]
        ttk.Combobox(control_frame, textvariable=self.search_field_var, values=fields,
                     state="readonly", width=14).pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = tk.Entry(control_frame, width=20, font=("Segoe UI", 10))
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<Return>', lambda e: self.search_records())
        tk.Button(control_frame, text="Найти", command=self.search_records,
                  bg="#28a745", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", width=8).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(control_frame, text="Сброс", command=self.reset_search,
                  bg="#ffc107", fg="black", font=("Segoe UI", 10, "bold"),
                  relief="flat", width=8).pack(side=tk.LEFT, padx=(0, 10))

        # Сортировка
        tk.Label(control_frame, text="Сортировка:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0")\
            .pack(side=tk.LEFT, padx=(0, 5))
        self.sort_var = tk.StringVar(value="По ID (новые сверху)")
        sort_options = [
            "По ID (новые сверху)",
            "По ID (старые сверху)",
            "По ФИО (А-Я)",
            "По ФИО (Я-А)",
            "По дате начала (новые)",
            "По дате начала (старые)",
            "По дате добавления (новые)",
            "По дате добавления (старые)"
        ]
        sort_combo = ttk.Combobox(control_frame, textvariable=self.sort_var, values=sort_options,
                                  state="readonly", width=20)
        sort_combo.pack(side=tk.LEFT, padx=(0, 10))
        sort_combo.bind('<<ComboboxSelected>>', lambda e: self.change_sort())

        # Кнопки архива, корзины, удаления
        self.archive_button = tk.Button(control_frame, text="📂 Архив", command=self.toggle_archive,
                                        bg="#6f42c1", fg="white", font=("Segoe UI", 10, "bold"),
                                        relief="flat", width=10)
        self.archive_button.pack(side=tk.LEFT, padx=(0, 5))

        self.trash_button = tk.Button(
            control_frame, text="🗑 Корзина", command=self.toggle_trash,
            bg="#6c757d", fg="white", font=("Segoe UI", 10, "bold"),
            relief="flat", width=12
        )
        self.trash_button.pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(control_frame, text="🗑 Удалить", command=self.soft_delete_selected,
                  bg="#dc3545", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", width=10).pack(side=tk.LEFT)

        # Таблица
        columns = ("ID", "ФИО", "Пол", "Номер истории", "Год рожд.", "Возраст", "Диагноз",
                   "Начало лечения", "Окончание лечения", "Отделение", "Давление", "Результат", "Сеансы", "Номер курса")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", height=18)
        for col in columns:
            self.tree.heading(col, text=col)
        widths = [40, 160, 50, 100, 70, 70, 130, 110, 110, 130, 100, 130, 70, 80]
        for col, w in zip(columns, widths):
            self.tree.column(col, width=w, anchor="center")

        scroll_y = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self.table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scroll_y.set, xscroll=scroll_x.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree.bind('<Double-1>', self.open_patient_card)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ====================== ОКНО НАСТРОЕК ======================
    def open_settings(self):
        """Открывает окно настроек (одно на приложение)."""
        # Если окно уже открыто — поднимаем на передний план
        if self._settings_window is not None:
            try:
                if self._settings_window.winfo_exists():
                    self._settings_window.deiconify()
                    self._settings_window.lift()
                    self._settings_window.focus_set()
                    return
            except tk.TclError:
                pass

        win = tk.Toplevel(self.root)
        self._settings_window = win
        win.title("Настройки")
        win.configure(bg="#f0f0f0")
        win.resizable(False, False)
        win.transient(self.root)

        # Заголовок
        hf = tk.Frame(win, bg="#0056b3", height=60)
        hf.pack(fill=tk.X)
        tk.Label(hf, text="⚙  НАСТРОЙКИ", font=("Segoe UI", 16, "bold"),
                 fg="white", bg="#0056b3").pack(pady=15)

        body = tk.Frame(win, bg="#f0f0f0")
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # ===== Секция: Резервное копирование =====
        sec1 = tk.LabelFrame(body, text="  📦  Резервное копирование  ",
                              font=("Segoe UI", 11, "bold"),
                              bg="#f0f0f0", fg="#0056b3", bd=1, relief="groove")
        sec1.pack(fill=tk.X, pady=(0, 15))

        row1 = tk.Frame(sec1, bg="#f0f0f0")
        row1.pack(fill=tk.X, padx=15, pady=(12, 6))
        tk.Label(row1, text="Интервал:", font=("Segoe UI", 10),
                 bg="#f0f0f0", width=22, anchor="w").pack(side=tk.LEFT)
        self.backup_interval_var = tk.StringVar()
        interval_options = ["Выкл.", "5 мин", "10 мин", "15 мин", "30 мин"]
        cur_min = self.config.get("backup_interval_minutes", 10)
        cur_label = "Выкл." if not cur_min else f"{cur_min} мин"
        if cur_label not in interval_options:
            cur_label = "10 мин"
        self.backup_interval_var.set(cur_label)
        interval_combo = ttk.Combobox(row1, textvariable=self.backup_interval_var,
                                       values=interval_options, state="readonly", width=12)
        interval_combo.pack(side=tk.LEFT)
        interval_combo.bind('<<ComboboxSelected>>', lambda e: self.change_backup_interval())

        row2 = tk.Frame(sec1, bg="#f0f0f0")
        row2.pack(fill=tk.X, padx=15, pady=6)
        self.auto_start_var = tk.BooleanVar(value=bool(self.config.get("auto_backup_on_start", True)))
        tk.Checkbutton(row2, text="Создавать копию при запуске программы",
                       variable=self.auto_start_var, command=self.toggle_auto_start,
                       bg="#f0f0f0", font=("Segoe UI", 10), anchor="w").pack(side=tk.LEFT)

        row3 = tk.Frame(sec1, bg="#f0f0f0")
        row3.pack(fill=tk.X, padx=15, pady=6)
        tk.Label(row3, text="Хранить копий:", font=("Segoe UI", 10),
                 bg="#f0f0f0", width=22, anchor="w").pack(side=tk.LEFT)
        self.max_backups_var = tk.StringVar(value=str(self.config.get("max_auto_backups", 20)))
        max_entry = tk.Entry(row3, textvariable=self.max_backups_var, width=12, font=("Segoe UI", 10))
        max_entry.pack(side=tk.LEFT)
        max_entry.bind('<FocusOut>', lambda e: self.change_max_backups())
        max_entry.bind('<Return>', lambda e: self.change_max_backups())
        tk.Label(row3, text="(более старые удаляются)", font=("Segoe UI", 9),
                 fg="#888", bg="#f0f0f0").pack(side=tk.LEFT, padx=(8, 0))

        row4 = tk.Frame(sec1, bg="#f0f0f0")
        row4.pack(fill=tk.X, padx=15, pady=(12, 15))
        tk.Button(row4, text="📁 Открыть папку", command=self.open_backups_folder,
                  bg="#20c997", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=12, pady=6, cursor="hand2").pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(row4, text="💾 Создать бэкап сейчас", command=self.backup_database,
                  bg="#17a2b8", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=12, pady=6, cursor="hand2").pack(side=tk.LEFT)

        # ===== Секция: Импорт БД =====
        sec2 = tk.LabelFrame(body, text="  📥  Импорт базы данных  ",
                              font=("Segoe UI", 11, "bold"),
                              bg="#f0f0f0", fg="#0056b3", bd=1, relief="groove")
        sec2.pack(fill=tk.X, pady=(0, 15))

        tk.Label(sec2, text="Заменить текущую базу данных на выбранную из файла.\n"
                            "Текущая БД будет сохранена как .old резервная копия.",
                 font=("Segoe UI", 9), bg="#f0f0f0", fg="#666", justify="left")\
            .pack(anchor="w", padx=15, pady=(12, 8))

        tk.Button(sec2, text="📂 Выбрать файл БД...", command=self.import_database,
                  bg="#fd7e14", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=12, pady=6, cursor="hand2")\
            .pack(anchor="w", padx=15, pady=(0, 15))

        # ===== Секция: Информация =====
        sec3 = tk.LabelFrame(body, text="  ℹ  Расположение файлов  ",
                              font=("Segoe UI", 11, "bold"),
                              bg="#f0f0f0", fg="#0056b3", bd=1, relief="groove")
        sec3.pack(fill=tk.X)

        tk.Label(sec3, text="База данных:", font=("Segoe UI", 9, "bold"),
                 bg="#f0f0f0").pack(anchor="w", padx=15, pady=(12, 0))
        tk.Label(sec3, text=self.db.db_name, font=("Segoe UI", 9),
                 bg="#f0f0f0", fg="#666", wraplength=480, justify="left")\
            .pack(anchor="w", padx=15)

        tk.Label(sec3, text="Папка бэкапов:", font=("Segoe UI", 9, "bold"),
                 bg="#f0f0f0").pack(anchor="w", padx=15, pady=(8, 0))
        tk.Label(sec3, text=self.backup_dir, font=("Segoe UI", 9),
                 bg="#f0f0f0", fg="#666", wraplength=480, justify="left")\
            .pack(anchor="w", padx=15, pady=(0, 15))

        # ===== Кнопка закрытия =====
        footer = tk.Frame(win, bg="#f0f0f0")
        footer.pack(fill=tk.X, pady=(0, 15))
        tk.Button(footer, text="Закрыть", command=win.destroy,
                  bg="#6c757d", fg="white", font=("Segoe UI", 11, "bold"),
                  relief="flat", width=15, pady=8, cursor="hand2").pack()

        win.bind('<Escape>', lambda e: win.destroy())

        # Центрирование окна
        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        x = (win.winfo_screenwidth() // 2) - (w // 2)
        y = (win.winfo_screenheight() // 2) - (h // 2)
        win.geometry(f'{w}x{h}+{x}+{y}')

    # ---------- Сортировка ----------
    def change_sort(self):
        choice = self.sort_var.get()
        mapping = {
            "По ID (новые сверху)": "id DESC",
            "По ID (старые сверху)": "id ASC",
            "По ФИО (А-Я)": "full_name COLLATE NOCASE ASC",
            "По ФИО (Я-А)": "full_name COLLATE NOCASE DESC",
            "По дате начала (новые)": "treatment_start_date DESC",
            "По дате начала (старые)": "treatment_start_date ASC",
            "По дате добавления (новые)": "id DESC",
            "По дате добавления (старые)": "id ASC"
        }
        self.current_order = mapping.get(choice, "id DESC")
        self.show_records()

    # ---------- Архив ----------
    def toggle_archive(self):
        self.show_archived = not self.show_archived
        if self.show_archived:
            self.archive_button.config(text="🗂 Скрыть архив", bg="#dc3545", width=14)
        else:
            self.archive_button.config(text="📂 Архив", bg="#6f42c1", width=10)
        self.show_records()

    # ---------- Корзина ----------
    def toggle_trash(self):
        self.show_deleted = not self.show_deleted
        if self.show_deleted:
            self.trash_button.config(text="🗑 Скрыть корзину", bg="#dc3545", width=16)
        else:
            self.trash_button.config(text="🗑 Корзина", bg="#6c757d", width=12)
        self.show_records()

    def soft_delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Сначала выберите запись в таблице.")
            return
        item = self.tree.item(sel[0])
        patient_id = item['values'][0]
        full_name = item['values'][1]
        if not messagebox.askyesno(
            "Подтверждение",
            f"Переместить пациента в корзину?\n\n"
            f"{full_name}\n(ID: {patient_id})\n\n"
            "Запись можно будет восстановить."
        ):
            return
        try:
            self.db.soft_delete_patient(patient_id)
            self.show_records()
            messagebox.showinfo("Готово", "Запись перемещена в корзину.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось переместить запись: {e}")

    # ---------- Отображение записей ----------
    def show_records(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        hidden_flag = 1 if self.show_archived else 0
        deleted_flag = 1 if self.show_deleted else 0
        records = self.db.get_patients_sorted(
            hidden=hidden_flag, deleted=deleted_flag, order_by=self.current_order
        )
        for rec in records:
            self._insert_tree_row(rec)

    def _insert_tree_row(self, rec):
        pressure_display = ""
        if rec[10] is not None and rec[11] is not None:
            pressure_display = f"{rec[10]} {rec[11]}"
        values = (
            rec[0], rec[1], rec[5] or "", rec[2] or "", rec[3] or "",
            rec[4] or "", rec[6] or "", rec[7] or "", rec[8] or "",
            rec[9] or "", pressure_display, rec[12] or "", rec[13] or 0, rec[14] or 0
        )
        self.tree.insert("", tk.END, values=values)

    # ---------- Ручной бэкап ----------
    def backup_database(self):
        folder = filedialog.askdirectory(title="Выберите папку для сохранения бэкапа")
        if not folder:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"manual_backup_{timestamp}.db"
        backup_path = os.path.join(folder, backup_name)
        try:
            if self.db.backup_to(backup_path):
                messagebox.showinfo("Успех", f"Бэкап создан:\n{backup_path}")
            else:
                messagebox.showerror("Ошибка", "Не удалось создать бэкап.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать бэкап: {e}")

    # ---------- Авто-бэкап ----------
    def change_backup_interval(self):
        """Вызывается при смене интервала авто-бэкапа в настройках."""
        label = self.backup_interval_var.get()
        mapping = {"Выкл.": 0, "5 мин": 5, "10 мин": 10, "15 мин": 15, "30 мин": 30}
        minutes = mapping.get(label, 10)
        self.config["backup_interval_minutes"] = minutes
        save_config(self.db.base_path, self.config)
        self.reschedule_backup()

    def change_max_backups(self):
        """Валидация и сохранение количества хранимых копий."""
        try:
            val = int(self.max_backups_var.get().strip())
            if val < 1:
                val = 1
            elif val > 1000:
                val = 1000
        except (ValueError, AttributeError):
            val = 20
        self.max_backups_var.set(str(val))
        self.config["max_auto_backups"] = val
        save_config(self.db.base_path, self.config)

    def toggle_auto_start(self):
        """Включение/выключение бэкапа при запуске."""
        self.config["auto_backup_on_start"] = bool(self.auto_start_var.get())
        save_config(self.db.base_path, self.config)

    def reschedule_backup(self):
        """Отменяет текущий таймер и планирует следующий по актуальному интервалу."""
        if self._backup_timer_id is not None:
            try:
                self.root.after_cancel(self._backup_timer_id)
            except Exception:
                pass
            self._backup_timer_id = None
        minutes = self.config.get("backup_interval_minutes", 10)
        if minutes and minutes > 0:
            self._backup_timer_id = self.root.after(
                minutes * 60 * 1000, self._scheduled_backup
            )

    def _scheduled_backup(self):
        self._backup_timer_id = None
        self.auto_backup()
        self.reschedule_backup()

    def auto_backup(self):
        """Создаёт автоматический бэкап и чистит старые."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"auto_backup_{timestamp}.db")
            if self.db.backup_to(backup_path):
                self._rotate_backups()
                print(f"[AUTO-BACKUP] Создан: {backup_path}")
            else:
                print("[AUTO-BACKUP] Не удалось создать резервную копию.")
        except Exception as e:
            print(f"[AUTO-BACKUP] Ошибка: {e}")

    def _rotate_backups(self):
        """Оставляет только последние max_auto_backups копий."""
        try:
            files = [
                f for f in os.listdir(self.backup_dir)
                if f.startswith("auto_backup_") and f.endswith(".db")
            ]
            files.sort(
                key=lambda f: os.path.getmtime(os.path.join(self.backup_dir, f)),
                reverse=True
            )
            max_keep = self.config.get("max_auto_backups", 20)
            for old in files[max_keep:]:
                try:
                    os.remove(os.path.join(self.backup_dir, old))
                    print(f"[AUTO-BACKUP] Удалён старый бэкап: {old}")
                except Exception as e:
                    print(f"[AUTO-BACKUP] Не удалось удалить {old}: {e}")
        except Exception as e:
            print(f"[AUTO-BACKUP] Ошибка ротации: {e}")

    def open_backups_folder(self):
        try:
            if not os.path.isdir(self.backup_dir):
                os.makedirs(self.backup_dir, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(self.backup_dir)
            elif sys.platform == "darwin":
                os.system(f'open "{self.backup_dir}"')
            else:
                os.system(f'xdg-open "{self.backup_dir}"')
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

    # ---------- Импорт ----------
    def import_database(self):
        file_path = filedialog.askopenfilename(
            title="Выберите файл базы данных (.db)",
            filetypes=[("Базы данных SQLite", "*.db"), ("Все файлы", "*.*")]
        )
        if not file_path:
            return
        if not os.path.isfile(file_path):
            messagebox.showerror("Ошибка", "Файл не найден.")
            return
        if not messagebox.askyesno("Подтверждение",
                                   "Вы уверены, что хотите заменить текущую базу данных?\n"
                                   "Текущие данные будут потеряны."):
            return
        try:
            self.db.close()
            old_path = self.db.db_name
            backup_old = old_path + ".old"
            if os.path.exists(old_path):
                if os.path.exists(backup_old):
                    os.remove(backup_old)
                os.rename(old_path, backup_old)
            shutil.copy2(file_path, old_path)
            self.db.connect()
            self.show_records()
            messagebox.showinfo("Успех", "База данных успешно импортирована.\n"
                               "Старая БД сохранена как 'medical_records.db.old'")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось импортировать БД: {e}")
            try:
                self.db.connect()
            except:
                pass

    # ---------- Остальные методы ----------
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
            treatment_start_date = self.entries["Дата начала лечения (ДД-ММ-ГГГГ):"].get().strip()
            treatment_end_date = self.entries["Дата окончания лечения (ДД-ММ-ГГГГ):"].get().strip()
            department = self.entries["Отделение:"].get().strip()

            val_entry, unit_combo = self.entries["Давление (число):"]
            pressure_value_str = val_entry.get().strip()
            pressure_unit = unit_combo.get().strip()

            indication = self.entries["Показания к использованию:"].get().strip()
            treatment_result = self.entries["Результат лечения:"].get().strip()
            sessions_str = self.entries["Количество сеансов:"].get().strip()
            courses_str = self.entries["Номер курса:"].get().strip()
            complications = self.entries["Осложнения:"].get().strip()
            effect = self.entries["Эффект:"].get().strip()
            notes = self.entries["Примечания:"].get().strip()

            if not full_name or not diagnosis:
                messagebox.showerror("Ошибка", "ФИО и диагноз обязательны.")
                return
            if not treatment_start_date:
                messagebox.showerror("Ошибка", "Введите дату начала лечения.")
                return
            if birth_year_str and not Validators.validate_year(birth_year_str):
                messagebox.showerror("Ошибка", "Год рождения должен быть целым числом от 1900 до 2100.")
                return
            if age_str and not Validators.validate_age(age_str):
                messagebox.showerror("Ошибка", "Возраст должен быть целым числом от 0 до 150.")
                return

            birth_year = int(birth_year_str) if birth_year_str else None
            age = int(age_str) if age_str else None

            if not Validators.validate_date(treatment_start_date):
                messagebox.showerror("Ошибка", "Дата начала лечения должна быть в формате ДД-ММ-ГГГГ.")
                return
            if treatment_end_date and not Validators.validate_date(treatment_end_date):
                messagebox.showerror("Ошибка", "Дата окончания лечения должна быть в формате ДД-ММ-ГГГГ.")
                return

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
                pressure_unit = None

            sessions = int(sessions_str) if sessions_str else 0
            courses = int(courses_str) if courses_str else 0
            if sessions < 0 or courses < 0:
                raise ValueError("Количество не может быть отрицательным")

            patient_data = (
                full_name, case_number, birth_year, age, gender, diagnosis,
                treatment_start_date, treatment_end_date, department,
                pressure_value, pressure_unit,
                treatment_result, sessions, courses,
                indication, complications, effect, notes
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
            if isinstance(widget, tuple):
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
                WHERE full_name LIKE ? COLLATE NOCASE
                   OR case_number LIKE ? COLLATE NOCASE
                   OR CAST(birth_year AS TEXT) LIKE ?
                   OR CAST(age AS TEXT) LIKE ?
                   OR gender LIKE ? COLLATE NOCASE
                   OR diagnosis LIKE ? COLLATE NOCASE
                   OR treatment_start_date LIKE ?
                   OR treatment_end_date LIKE ?
                   OR department LIKE ? COLLATE NOCASE
                   OR CAST(pressure_value AS TEXT) LIKE ?
                   OR pressure_unit LIKE ? COLLATE NOCASE
                   OR treatment_result LIKE ? COLLATE NOCASE
                   OR CAST(sessions_count AS TEXT) LIKE ?
                   OR CAST(courses_count AS TEXT) LIKE ?
                   OR indication LIKE ? COLLATE NOCASE
                   OR complications LIKE ? COLLATE NOCASE
                   OR effect LIKE ? COLLATE NOCASE
                   OR notes LIKE ? COLLATE NOCASE
                ORDER BY id DESC
            """
            t = f"%{term}%"
            params = (t,) * 18
            return query, params
        else:
            mapping = {
                "ФИО": ("full_name", True),
                "Номер истории": ("case_number", True),
                "Год рождения": ("birth_year", False),
                "Возраст": ("age", False),
                "Пол": ("gender", True),
                "Диагноз": ("diagnosis", True),
                "Дата начала": ("treatment_start_date", False),
                "Дата окончания": ("treatment_end_date", False),
                "Отделение": ("department", True),
                "Давление": ("pressure_value", False),
                "Результат": ("treatment_result", True),
                "Сеансы": ("sessions_count", False),
                "Номер курса": ("courses_count", False),
                "Показания": ("indication", True),
                "Осложнения": ("complications", True),
                "Эффект": ("effect", True),
                "Примечания": ("notes", True),
            }
            db_field, is_text = mapping[field]

            if field == "ФИО":
                words = term.split()
                if len(words) == 1:
                    query = f"SELECT * FROM patients WHERE {db_field} LIKE ? COLLATE NOCASE ORDER BY id DESC"
                    return query, (f"%{words[0]}%",)
                else:
                    conditions = " OR ".join([f"{db_field} LIKE ? COLLATE NOCASE" for _ in words])
                    query = f"SELECT * FROM patients WHERE {conditions} ORDER BY id DESC"
                    params = tuple(f"%{w}%" for w in words)
                    return query, params

            elif field == "Давление":
                query = """
                    SELECT * FROM patients
                    WHERE CAST(pressure_value AS TEXT) LIKE ?
                       OR pressure_unit LIKE ? COLLATE NOCASE
                    ORDER BY id DESC
                """
                return query, (f"%{term}%", f"%{term}%")

            else:
                if is_text:
                    query = f"SELECT * FROM patients WHERE {db_field} LIKE ? COLLATE NOCASE ORDER BY id DESC"
                    params = (f"%{term}%",)
                else:
                    query = f"SELECT * FROM patients WHERE CAST({db_field} AS TEXT) LIKE ? ORDER BY id DESC"
                    params = (f"%{term}%",)
                return query, params

    def on_closing(self):
        if self._backup_timer_id is not None:
            try:
                self.root.after_cancel(self._backup_timer_id)
            except Exception:
                pass
        self.db.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MedicalDatabaseApp(root)
    root.mainloop()