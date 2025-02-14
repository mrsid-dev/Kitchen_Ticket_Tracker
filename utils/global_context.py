from jnius import autoclass
import json
import os

class GlobalContext:
    _current_user = None

    if os.name == "posix" and "ANDROID_ARGUMENT" in os.environ:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        app_context = PythonActivity.mActivity.getApplicationContext()
        user_file = os.path.join(app_context.getExternalFilesDir(None).getAbsolutePath(), "current_user.json")
    else:
        user_file = "./current_user.json"  # Fallback for PC/Mac testing

    @staticmethod
    def set_current_user(user):
        """Set the current logged-in user and save it to a file."""
        GlobalContext._current_user = user

        # Ensure the directory exists
        os.makedirs(os.path.dirname(GlobalContext.user_file), exist_ok=True)

        # Save user to a file
        with open(GlobalContext.user_file, "w", encoding="utf-8") as f:
            json.dump(user, f)

    @staticmethod
    def get_current_user():
        """Get the current logged-in user from memory or file."""
        if GlobalContext._current_user:
            return GlobalContext._current_user

        # Try loading from file if memory is empty
        if os.path.exists(GlobalContext.user_file):
            try:
                with open(GlobalContext.user_file, "r") as f:
                    data = f.read().strip()  # Read file content and strip whitespace
                    if not data:  # If the file is empty
                        print("current_user.json is empty.")
                        return None
                    GlobalContext._current_user = json.loads(data)  # Load JSON
                    if GlobalContext._current_user is None:  # If it's explicitly 'null'
                        print("current_user.json contains null.")
                        return None
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error loading current_user.json: {e}")
                return None  # Return None if file is corrupt or invalid

        return GlobalContext._current_user

