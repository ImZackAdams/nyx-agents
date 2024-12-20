import json
import os

class StateManager:
    def __init__(self, state_file, logger):
        self.state_file = state_file
        self.logger = logger
        self.last_processed_ids = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as file:
                    return json.load(file)
            except Exception as e:
                self.logger.error(f"Error loading state file: {e}")
        return {}

    def save_state(self):
        try:
            with open(self.state_file, "w") as file:
                json.dump(self.last_processed_ids, file)
            self.logger.info("Reply state saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving state file: {e}")
