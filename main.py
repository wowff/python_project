import sys
import io
import os
import segno
import re
import logging  
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTextEdit, QComboBox, QPushButton, QLabel, QMessageBox, QFileDialog,
    QColorDialog
)
from PyQt6.QtGui import QFont, QImage, QPixmap, QColor, QIcon
from PyQt6.QtCore import Qt

# Логи записываются в app_log.txt в кодировке utf-8.
logging.basicConfig(
    filename='app_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)


class QRGeneratorApp(QMainWindow):

    """
        Приложение для генерации QR-кода с графическим интерфейсом.

        Позволяет вводить текст, настраивать размерность, уровень коррекции ошибок, 
        изменять цвет пикселей и сохранять готовый результат в формате PNG на диск.

    """

    def __init__(self):
        """Инициализирует главное окно приложения и базовые переменные класса."""

        super().__init__()
        logging.info("Приложение запущено. Инициализация интерфейса...")
        self.setWindowTitle("Генератор QR-кодов")
        self.setMinimumSize(700, 520)

        self.current_qr_image = None
        self.qr_color = "#000000"

        self.init_ui()

    def init_ui(self):
        """Инициализирует все графические виджеты внутри главного окна"""

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        horizontal_layout = QHBoxLayout(main_widget)
        horizontal_layout.setSpacing(20)
        horizontal_layout.setContentsMargins(20, 20, 20, 20)
        horizontal_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Левая часть приложения с параметрами конфигурации QR кода
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 20, 0, 0)
        left_layout.setSpacing(15)

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Введите текст или ссылку для QR-кода...")
        self.input_field.setFont(QFont("Arial", 11))
        self.input_field.setStyleSheet("""
            QTextEdit { padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; background-color: white; }
            QTextEdit:focus { border: 1px solid #2b7de9; }
        """)
        self.input_field.setMinimumHeight(150)
        left_layout.addWidget(self.input_field)

        settings_row_layout = QHBoxLayout()
        settings_row_layout.setSpacing(15)

        size_block = QVBoxLayout()
        size_block.setSpacing(5)
        self.size_label_title = QLabel("Размерность:")
        self.size_label_title.setFont(QFont("Arial", 10))
        size_block.addWidget(self.size_label_title)

        self.size_combo = QComboBox()
        self.size_combo.setFont(QFont("Arial", 10))
        sizes = ["200", "300", "400", "500", "600", "700", "800"]
        for size in sizes:
            self.size_combo.addItem(f"{size}x{size} px", size)
        self.size_combo.setCurrentIndex(1)
        
        self.size_combo.currentIndexChanged.connect(
            lambda: logging.info(f"Пользователь выбрал размерность: {self.size_combo.currentData()}x{self.size_combo.currentData()} px")
        )
        size_block.addWidget(self.size_combo)

        error_block = QVBoxLayout()
        error_block.setSpacing(5)
        self.error_label_title = QLabel("Коррекция ошибок:")
        self.error_label_title.setFont(QFont("Arial", 10))
        error_block.addWidget(self.error_label_title)

        self.error_combo = QComboBox()
        self.error_combo.setFont(QFont("Arial", 10))
        self.error_combo.addItem("L (Низкая - 7%)", "L")
        self.error_combo.addItem("M (Средняя - 15%)", "M")
        self.error_combo.addItem("Q (Высокая - 25%)", "Q")
        self.error_combo.addItem("H (Лучшая - 30%)", "H")
        self.error_combo.setCurrentIndex(1)
        # Логируем изменение уровня коррекции
        self.error_combo.currentIndexChanged.connect(
            lambda: logging.info(f"Пользователь выбрал уровень коррекции: {self.error_combo.currentData()}")
        )
        error_block.addWidget(self.error_combo)

        settings_row_layout.addLayout(size_block, stretch=1)
        settings_row_layout.addLayout(error_block, stretch=1)
        left_layout.addLayout(settings_row_layout)

        self.btn_color = QPushButton(" Выбрать цвет QR-кода")
        self.btn_color.setFont(QFont("Arial", 10))
        self.btn_color.clicked.connect(self.choose_color)
        left_layout.addWidget(self.btn_color)

        left_layout.addStretch(1)

        # Правая часть приложения с интерфейсом генерации и сохранения QR
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.qr_label = QLabel("Ожидание генерации...")
        self.qr_label.setMinimumSize(300, 300)
        self.qr_label.setMaximumSize(300, 300)
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.qr_label.setStyleSheet("""
            QLabel { background-color: #ffffff; color: #1e293b; border: 3px solid #000000; border-radius: 10px; }
        """)
        right_layout.addWidget(self.qr_label)

        self.btn_generate = QPushButton("Сгенерировать QR-код")
        self.btn_generate.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.btn_generate.setStyleSheet("""
            QPushButton { background-color: #2b7de9; color: white; padding: 12px; border-radius: 6px; }
            QPushButton:hover { background-color: #1e62c1; }
        """)
        self.btn_generate.clicked.connect(self.generate_qr)
        right_layout.addWidget(self.btn_generate)

        self.btn_save = QPushButton("Сохранить QR-код")
        self.btn_save.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; padding: 12px; border-radius: 6px; }
            QPushButton:hover { background-color: #059669; }
            QPushButton:disabled { background-color: #cbd5e1; color: #94a3b8; }
        """)
        self.btn_save.clicked.connect(self.save_qr)
        right_layout.addWidget(self.btn_save)

        # Выводим наши части приложения на экран приложения
        horizontal_layout.addWidget(left_container, stretch=1)
        horizontal_layout.addWidget(right_container, stretch=0)

    def choose_color(self):
        """
        Открывает диалоговое окно для выбора цвета QR-кода.

        Если цвет успешно выбран пользователем, обновляет переменную класса и
        записывает событие в системный лог.
        """

        color = QColorDialog.getColor(QColor(self.qr_color), self, "Выберите цвет для QR-кода")
        if color.isValid():
            self.qr_color = color.name()
            logging.info(f"Пользователь изменил цвет QR-кода на HEX: {self.qr_color}")

    
    def is_valid_filename(self, filename):
        """
        Проверяет имя файла на отсутствие запрещенных спецсимволов.
        """
        return not re.search(r'[<>:"/\\|?*]', filename) and filename.strip() != ""

    def generate_qr(self):
        """
        Генерирует QR-код на основе введенных пользователем данных.

        Считывает текст, проверяет допустимость длины, запрашивает у библиотеки segno
        построение модуля кода с учетом уровня коррекции и выбранного цвета.

        Загружает результат в QImage, выполняет сглаженное масштабирование 
        и активирует кнопку экспорта.

        Записывает в лог технические ошибки, возникающие на этапе генерации.
        """

        text = self.input_field.toPlainText().strip()
        if not text:
            logging.warning("Попытка генерации: поле ввода пустое.")
            QMessageBox.warning(self, "Внимание", "Пожалуйста, введите текст для генерации QR-кода.")
            return
        if len(text) > 1400:
            logging.warning(f"Попытка генерации: текст превышает лимит ({len(text)} символов).")
            QMessageBox.warning(self, "Превышен лимит", f"Длина текста ({len(text)} симв.) превышает лимит в 1400 символов.")
            return

        target_size = int(self.size_combo.currentData())
        error_level = self.error_combo.currentData()
        
        logging.info(f"Старт генерации. Параметры -> Размер: {target_size}px, Коррекция: {error_level}, Цвет: {self.qr_color}")

        try:
            qr = segno.make(text, error=error_level)
            buffer = io.BytesIO()
            qr.save(buffer, kind="png", scale=10, dark=self.qr_color)
            qr_bytes = buffer.getvalue()
            image = QImage.fromData(qr_bytes)
            self.current_qr_image = image.scaled(target_size, target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            display_size = min(300, target_size) - 10 if target_size < 300 else 290
            screen_image = self.current_qr_image.scaled(display_size, display_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.qr_label.setPixmap(QPixmap.fromImage(screen_image))
            self.btn_save.setEnabled(True)
            logging.info("QR-код успешно сгенерирован и выведен на экран.")
        except Exception as e:
            logging.error("Ошибка при генерации QR-кода!", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при генерации:\n{str(e)}")

    def save_qr(self):
        """
        Выгружает полноразмерный объект QImage из памяти на жесткий диск.

        Открывает диалог сохранения, автоматически предлагает уникальное имя 
        файла с заданным шаблоном <дата_время>. 
        
        Осуществляет проверку на валидность строки имени, существование папки и наличие прав 
        на запись.

        Перехватывает ошибки, связанные с обработкой и сохранением файла.
        """

        if not self.current_qr_image:
            return

        current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_dir = os.path.expanduser("~/Desktop")
        default_name = f"qr_{current_time_str}.png"
        default_path = os.path.join(default_dir, default_name)

        logging.info("Пользователь открыл диалог сохранения файла.")
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить QR-код", default_path, "PNG Files (*.png);;All Files (*)")
        if not file_path:
            logging.info("Сохранение отменено пользователем.")
            return

        if os.path.exists(file_path):
            logging.info(f"Конфликт имен: файл {file_path} уже существует. Запуск автоподбора имени...")
            base, ext = os.path.splitext(file_path)
            counter = 1
            while os.path.exists(f"{base}_{counter}{ext}"):
                counter += 1
            file_path = f"{base}_{counter}{ext}"
            logging.info(f"Новое имя файла после разрешения конфликта: {file_path}")

        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)

        if not self.is_valid_filename(filename):
            logging.error(f"Ошибка сохранения: имя файла '{filename}' содержит недопустимые символы.")
            QMessageBox.critical(self, "Ошибка", "Имя файла содержит недопустимые символы.")
            return

        if not os.path.exists(directory):
            logging.error(f"Ошибка сохранения: папка '{directory}' не существует.")
            QMessageBox.critical(self, "Ошибка", f"Указанная папка не существует:\n{directory}")
            return

        if not os.access(directory, os.W_OK):
            logging.error(f"Ошибка доступа: нет прав на запись в папку '{directory}'.")
            QMessageBox.critical(self, "Ошибка доступа", f"Нет прав на запись в папку:\n{directory}")
            return

        try:
            if self.current_qr_image.save(file_path, "PNG"):
                logging.info(f"Файл успешно сохранен на диск. Путь: {file_path}")
                QMessageBox.information(self, "Успех", f"QR-код сохранен как:\n{filename}")
            else:
                logging.error(f"Внутренний сбой QImage.save() при записи пути: {file_path}")
                QMessageBox.critical(self, "Ошибка", "Не удалось сохранить файл.")
        except Exception as e:
            logging.error("Непредвиденная ошибка во время записи файла на диск!", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Непредвиденная ошибка при сохранении:\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QRGeneratorApp()
    window.show()
    sys.exit(app.exec())
