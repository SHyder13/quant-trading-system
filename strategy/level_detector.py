class LevelDetector:
    def __init__(self, level_calculator):
        self.level_calculator = level_calculator
        self.levels = {}

    def update_levels(self, intraday_data):
        """Triggers the calculation of all key levels and stores them."""

        self.levels = self.level_calculator.calculate_all_levels(intraday_data)
        print(f"Levels updated: {self.levels}")
        return self.levels
