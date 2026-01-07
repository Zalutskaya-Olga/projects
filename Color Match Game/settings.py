from PyQt5.QtWidgets import QDialog
from ui.settings_dialog import Ui_SettingsDialog

class SettingsDialog(QDialog, Ui_SettingsDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # Настройки по умолчанию
        self.elements_count = 4
        self.colors_count = 2
        self.diff_type = "color"
        self.time_limit = 0

        self.init_ui()

    def init_ui(self):
        self.elements_combo.addItems(["4", "6", "9", "12", "16"])
        self.colors_combo.addItems(["2", "3"])
        self.diff_type_combo.addItems(["color", "color+shape"])
        self.time_limit_combo.addItems(["No limit", "5 sec", "7 sec", "10 sec", "15 sec"])

        self.buttonBox.accepted.connect(self.accept_settings)
        self.buttonBox.rejected.connect(self.reject)

    def accept_settings(self):
        self.elements_count = int(self.elements_combo.currentText())
        self.colors_count = int(self.colors_combo.currentText())
        self.diff_type = self.diff_type_combo.currentText()

        time_text = self.time_limit_combo.currentText()
        if time_text == "No limit":
            self.time_limit = 0
        else:
            self.time_limit = int(time_text.split()[0])

        self.accept()
