import sys
from PyQt5.QtWidgets import QApplication
from game_window import GameWindow
import warnings
import os
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ['QT_MAC_WANTS_LAYER'] = '1'  # Решает проблемы с графикой на macOS

def main():
    app = QApplication(sys.argv)

    # Загрузка стилей
    with open('resources/styles/style.css', 'r') as f:
        app.setStyleSheet(f.read())

    window = GameWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
