# settings.py
import json
import os

class SettingsManager:
    """
    Manages a unified settings.json file.
    Ensures that settings from different components (main window, parameters editor, etc.)
    are combined and saved without overwriting each other.
    """
    def __init__(self, settings_file="settings.json"):
        self.settings_file = settings_file

    def load_settings(self, component_key):
        """Load settings specific to a component."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    all_settings = json.load(f)
                return all_settings.get(component_key, {})
        except Exception as e:
            print(f"Failed to load settings for {component_key}: {e}")
        return {}

    def save_settings(self, component_key, component_settings):
        """Save settings for a specific component, merging with existing data."""
        try:
            existing_settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    existing_settings = json.load(f)

            if component_key not in existing_settings:
                existing_settings[component_key] = {}

            existing_settings[component_key].update(component_settings)

            with open(self.settings_file, 'w') as f:
                json.dump(existing_settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings for {component_key}: {e}")
