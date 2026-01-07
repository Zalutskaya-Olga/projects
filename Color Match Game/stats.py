from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel
from ui.stats_dialog import Ui_StatsDialog
import json
import os

class StatsDialog(QDialog, Ui_StatsDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.stats_file = "stats.json"
        self.stats_data = self.load_stats()

        self.init_ui()

    def load_stats(self):
        if os.path.exists(self.stats_file):
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {
            "games_played": 0,
            "total_score": 0,
            "best_score": 0,
            "correct_answers": 0,
            "wrong_answers": 0,
            "accuracy": 0,
            "history": []
        }

    def save_stats(self):
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats_data, f)

    def init_ui(self):
        self.update_stats_display()

    def update_stats_display(self):
        stats = self.stats_data
        accuracy = (stats["correct_answers"] / (stats["correct_answers"] + stats["wrong_answers"])) * 100 if (stats["correct_answers"] + stats["wrong_answers"]) > 0 else 0

        self.games_played_label.setText(f"Games Played: {stats['games_played']}")
        self.total_score_label.setText(f"Total Score: {stats['total_score']}")
        self.best_score_label.setText(f"Best Score: {stats['best_score']}")
        self.accuracy_label.setText(f"Accuracy: {accuracy:.1f}%")

        # Очищаем историю перед обновлением
        self.history_list.clear()

        # Добавляем последние 10 игр
        for game in stats["history"][-10:]:
            self.history_list.addItem(
                f"Score: {game['score']}, Correct: {game['correct']}, Wrong: {game['wrong']}, Time: {game['time']}"
            )

    def add_game_result(self, score, correct, wrong, time_spent):
        self.stats_data["games_played"] += 1
        self.stats_data["total_score"] += score
        self.stats_data["best_score"] = max(self.stats_data["best_score"], score)
        self.stats_data["correct_answers"] += correct
        self.stats_data["wrong_answers"] += wrong

        game_data = {
            "score": score,
            "correct": correct,
            "wrong": wrong,
            "time": time_spent
        }
        self.stats_data["history"].append(game_data)

        self.save_stats()
        self.update_stats_display()
