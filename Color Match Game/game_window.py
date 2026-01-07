from PyQt5.QtWidgets import QMainWindow, QMessageBox, QDialog
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush
from ui.main_window import Ui_MainWindow
from game_logic import GameLogic
from settings import SettingsDialog
from stats import StatsDialog
import random

class GameWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.game_logic = GameLogic()
        self.current_diff_element = None
        self.score = 0
        self.streak = 0
        self.round_time = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        # Настройки по умолчанию
        self.difficulty = "easy"
        self.elements_count = 4
        self.colors_count = 2
        self.diff_type = "color"
        self.time_limit = 0  # 0 - нет ограничения

        self.init_ui()
        self.new_round()

    def init_ui(self):
        self.actionEasy.triggered.connect(lambda: self.set_difficulty("easy"))
        self.actionMedium.triggered.connect(lambda: self.set_difficulty("medium"))
        self.actionHard.triggered.connect(lambda: self.set_difficulty("hard"))
        self.actionSettings.triggered.connect(self.open_settings)
        self.actionStatistics.triggered.connect(self.open_stats)
        self.actionExit.triggered.connect(self.close)

    def set_difficulty(self, difficulty):
        self.difficulty = difficulty
        if difficulty == "easy":
            self.elements_count = 4
            self.colors_count = 2
            self.diff_type = "color"
            self.time_limit = 0
        elif difficulty == "medium":
            self.elements_count = 6
            self.colors_count = 3
            self.diff_type = "color"
            self.time_limit = 10
        elif difficulty == "hard":
            self.elements_count = 9
            self.colors_count = 3
            self.diff_type = "color+shape"
            self.time_limit = 7

        self.new_round()

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Применяем новые настройки
            self.elements_count = dialog.elements_count
            self.colors_count = dialog.colors_count
            self.diff_type = dialog.diff_type
            self.time_limit = dialog.time_limit
            self.new_round()

    def open_stats(self):
        dialog = StatsDialog(self)
        dialog.exec_()

    def new_round(self):
        # Генерация нового раунда
        self.game_logic.generate_round(
            self.elements_count,
            self.colors_count,
            self.diff_type
        )
        self.current_diff_element = self.game_logic.diff_element_index

        # Отрисовка элементов
        self.draw_elements()

        # Запуск таймера, если есть ограничение по времени
        if self.time_limit > 0:
            self.round_time = self.time_limit
            self.timer_label.setText(str(self.round_time))
            self.timer.start(1000)
        else:
            self.timer_label.setText("∞")

    def draw_elements(self):
        # Очищаем предыдущие элементы
        for i in reversed(range(self.game_area.count())):
            self.game_area.itemAt(i).widget().setParent(None)

        # Рассчитываем размер сетки
        rows = int(self.elements_count ** 0.5)
        cols = self.elements_count // rows
        if rows * cols < self.elements_count:
            cols += 1

        # Создаем элементы
        for i in range(self.elements_count):
            element = GameElement(i, self.game_logic.elements[i], self)
            element.clicked.connect(self.element_clicked)
            self.game_area.addWidget(element, i // cols, i % cols)

    def element_clicked(self, index):
        if self.time_limit > 0:
            self.timer.stop()

        if index == self.current_diff_element:
            # Правильный ответ
            self.handle_correct_answer()
        else:
            # Неправильный ответ
            self.handle_wrong_answer(index)

        # Задержка перед новым раундом для отображения анимации
        QTimer.singleShot(1000, self.new_round)

    def handle_correct_answer(self):
        self.streak += 1
        base_points = 10 * (1 + (self.colors_count - 2) * 0.5)
        time_bonus = 0

        if self.time_limit > 0:
            time_bonus = int((self.round_time / self.time_limit) * 10)

        streak_bonus = int((self.streak - 1) * 2)
        points = int(base_points + time_bonus + streak_bonus)
        self.score += points

        self.score_label.setText(f"Score: {self.score}")
        self.streak_label.setText(f"Streak: {self.streak}x")

        # Анимация успеха
        for i in range(self.game_area.count()):
            widget = self.game_area.itemAt(i).widget()
            if widget.index == self.current_diff_element:
                widget.show_success()

    def handle_wrong_answer(self, clicked_index):
        self.streak = 0
        self.streak_label.setText(f"Streak: {self.streak}x")

        # Показываем правильный ответ
        for i in range(self.game_area.count()):
            widget = self.game_area.itemAt(i).widget()
            if widget.index == self.current_diff_element:
                widget.show_correct()
            elif widget.index == clicked_index:
                widget.show_wrong()

    def update_timer(self):
        self.round_time -= 1
        self.timer_label.setText(str(self.round_time))

        if self.round_time <= 0:
            self.timer.stop()
            self.handle_timeout()

    def handle_timeout(self):
        self.streak = 0
        self.streak_label.setText(f"Streak: {self.streak}x")

        # Показываем правильный ответ
        for i in range(self.game_area.count()):
            widget = self.game_area.itemAt(i).widget()
            if widget.index == self.current_diff_element:
                widget.show_correct()

        QTimer.singleShot(1000, self.new_round)

class GameElement(QPushButton):
    clicked = pyqtSignal(int)

    def __init__(self, index, element_data, parent=None):
        super().__init__(parent)
        self.index = index
        self.element_data = element_data
        self.setFixedSize(100, 100)
        self.clicked.connect(lambda: self.clicked.emit(self.index))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Рисуем фон
        if hasattr(self, 'is_success'):
            painter.setBrush(QBrush(QColor(0, 255, 0)))
        elif hasattr(self, 'is_wrong'):
            painter.setBrush(QBrush(QColor(255, 0, 0)))
        elif hasattr(self, 'is_correct'):
            painter.setBrush(QBrush(QColor(0, 0, 255)))
        else:
            painter.setBrush(QBrush(self.element_data['color']))

        painter.drawRect(self.rect())

        # Если режим с формами, рисуем форму
        if 'shape' in self.element_data:
            if self.element_data['shape'] == 'circle':
                painter.drawEllipse(self.rect().adjusted(10, 10, -10, -10))
            elif self.element_data['shape'] == 'triangle':
                path = QPainterPath()
                path.moveTo(self.width() // 2, 10)
                path.lineTo(10, self.height() - 10)
                path.lineTo(self.width() - 10, self.height() - 10)
                path.closeSubpath()
                painter.drawPath(path)

    def show_success(self):
        self.is_success = True
        self.update()

    def show_wrong(self):
        self.is_wrong = True
        self.update()

    def show_correct(self):
        self.is_correct = True
        self.update()
