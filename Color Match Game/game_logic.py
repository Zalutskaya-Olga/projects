from PyQt5.QtGui import QColor
import random

class GameLogic:
    def __init__(self):
        self.elements = []
        self.diff_element_index = -1

    def generate_round(self, elements_count, colors_count, diff_type):
        self.elements = []
        self.diff_element_index = random.randint(0, elements_count - 1)

        # Генерируем базовый цвет
        base_color = QColor(
            random.randint(100, 200),
            random.randint(100, 200),
            random.randint(100, 200)
        )

        # Генерируем цвета для всех элементов
        for i in range(elements_count):
            if i == self.diff_element_index:
                # Генерируем отличающийся цвет
                diff_color = self.generate_diff_color(base_color, colors_count)
                element = {
                    'color': diff_color,
                    'is_diff': True
                }

                # Если режим с формами, добавляем форму
                if diff_type == "color+shape":
                    element['shape'] = random.choice(['circle', 'triangle'])
            else:
                element = {
                    'color': base_color,
                    'is_diff': False
                }

            self.elements.append(element)

    def generate_diff_color(self, base_color, colors_count):
        if colors_count == 2:
            # Для 2 цветов просто инвертируем
            return QColor(
                255 - base_color.red(),
                255 - base_color.green(),
                255 - base_color.blue()
            )
        else:
            # Для 3 цветов выбираем случайное отличие
            option = random.randint(0, 2)
            if option == 0:
                return QColor(
                    base_color.red(),
                    255 - base_color.green(),
                    255 - base_color.blue()
                )
            elif option == 1:
                return QColor(
                    255 - base_color.red(),
                    base_color.green(),
                    255 - base_color.blue()
                )
            else:
                return QColor(
                    255 - base_color.red(),
                    255 - base_color.green(),
                    base_color.blue()
                )
