import sqlite3, os, pytz
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.clock import Clock
from datetime import datetime, timezone
from kivy.core.window import Window
from screens.kitchen_login_screen import KitchenLoginScreen
from screens.kitchen_panel_screen import KitchenPanel
from screens.manager_screen import ManagerScreen
from screens.clock_logs_screen import ClockLogsScreen
from utils.global_context import GlobalContext
from db.db_initialization import init_database
from kivy.utils import platform

if platform == "android":
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    app_context = PythonActivity.mActivity.getApplicationContext()

    # ✅ Store database in `/files/` instead of `/files/data/`
    db_folder = app_context.getExternalFilesDir(None).getAbsolutePath()
else:
    db_folder = "./"  # Fallback for PC/Mac testing

# ✅ Ensure the folder exists
if not os.path.exists(db_folder):
    os.makedirs(db_folder, exist_ok=True)
    print(f"Created directory: {db_folder}")

# ✅ Define the database path
db_path = os.path.join(db_folder, "kitchen_tracker.db")

# Set window size for testing on PC
Window.size = (720, 1520)  # Moto G Play resolution in portrait mode

class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.image = Image(source="splash_screen.png", fit_mode="fill")
        self.layout.add_widget(self.image)
        self.add_widget(self.layout)

    def on_enter(self):
        """Automatically switch to login screen after a delay."""
        Clock.schedule_once(self.switch_to_login, 2.5)  # Show splash screen for 2.5 seconds

    def switch_to_login(self, dt):
        self.manager.transition.direction = "up"
        self.manager.current = "kitchen_login"


class TicketApp(App):
    def build(self):
        init_database()

        self.screen_manager = ScreenManager()

        # Add Splash Screen first
        self.screen_manager.add_widget(SplashScreen(name="splash_screen"))
        self.screen_manager.add_widget(KitchenLoginScreen(name="kitchen_login"))
        self.screen_manager.add_widget(KitchenPanel(name="kitchen_panel"))
        self.screen_manager.add_widget(ManagerScreen(name="manager_screen", app=self))
        self.screen_manager.add_widget(ClockLogsScreen(name="clock_logs"))

        return self.screen_manager

    def on_start(self):
        """Runs after the app fully loads"""
        Clock.schedule_once(lambda dt: setattr(self.screen_manager, "current", "splash_screen"), 0.1)
        Clock.schedule_once(lambda dt: self.restore_logged_in_user(),3.0)  # ✅ Run AFTER splash transition (adjust time)
        self.schedule_auto_clock_out()

    def restore_logged_in_user(self):
        """Restore the last logged-in user from file storage or database."""

        # Step 1: Check if user data exists in the persistent file
        current_user = GlobalContext.get_current_user()

        if current_user and isinstance(current_user, dict):
            print(f"User restored from file: {current_user}")

            # ✅ STOP IMMEDIATELY if the user is a Manager
            if current_user.get("role") == "Manager":
                print("User is a Manager. Skipping further restoration.")
                return  # 🔴 Prevents checking for another active user

        # Step 2: If no stored user, check the database (only if NOT a Manager)
        if not os.path.exists(db_path):
            print("Database not found, requiring new login.")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # ✅ Step 2A: Get the most recent logged-in employee (if no manager is set)
        cursor.execute('''
            SELECT employee_name FROM clock_logs
            WHERE clock_out_time IS NULL
            ORDER BY clock_in_time DESC LIMIT 1
        ''')
        result = cursor.fetchone()

        if result:
            employee_name = result[0]

            # ✅ Step 2B: Now, use the name to find the role and PIN in the `cooks` table
            cursor.execute('''
                SELECT pin FROM cooks WHERE name = ?
            ''', (employee_name,))
            pin_result = cursor.fetchone()

            if pin_result:
                pin = pin_result  # ✅ Fetch role too
            else:
                print(f"Warning: No role or PIN found for {employee_name}, setting as None.")
                pin = None

            # ✅ Store user data (including role) in GlobalContext
            user_data = {"name": employee_name, "pin": pin}
            GlobalContext.set_current_user(user_data)

            print(f"User restored from database: {employee_name} (PIN: {pin})")

            # ✅ Switch to the correct screen
            self.add_or_switch(self.screen_manager, "kitchen_panel", KitchenPanel)

            # ✅ Update the UI
            self.update_cook_label(employee_name, pin)
        else:
            print("No active user found, requiring new login.")

        conn.close()

    def update_cook_label(self, cook_name, pin):
        """Updates the cook label in the Kitchen Panel Screen and sets PIN when applicable."""
        try:
            kitchen_panel = self.screen_manager.get_screen("kitchen_panel")
            kitchen_panel.cook_label.text = f"[color=#E4E5E9][b]Cook:[/b][/color]\n[color=#818590]{cook_name}[/color]"

            if self.screen_manager.has_screen("kitchen_login"):
                kitchen_login = self.screen_manager.get_screen("kitchen_login")

                if pin:  # ✅ Only set the PIN if it exists
                    kitchen_login.entered_pin = pin
                    print(f"PIN {pin} set in kitchen login screen")
                else:
                    print(f"No PIN needed for {cook_name} (likely a Manager).")

            kitchen_panel.entered_pin = pin if pin else ""  # ✅ Avoids errors when PIN is missing

        except Exception as e:
            print(f"Error updating cook label or PIN: {e}")

    def add_or_switch(self, screen_manager, screen_name, screen_class):
        if not screen_manager.has_screen(screen_name):
            screen_manager.add_widget(screen_class(name=screen_name))
        screen_manager.current = screen_name

    def schedule_auto_clock_out(self):
        """Schedules an automatic clock-out check at 11:00 PM every day."""
        now = datetime.now()
        target_time = now.replace(hour=23, minute=00, second=0, microsecond=0)  # 11:00 PM

        # If it's already past 11:00 PM today, schedule for tomorrow
        if now > target_time:
            target_time = target_time.replace(day=now.day + 1)

        delay_seconds = (target_time - now).total_seconds()

        print(f"Auto clock-out scheduled in {delay_seconds / 60:.2f} minutes.")
        Clock.schedule_once(lambda dt: self.auto_clock_out(), delay_seconds)

    def auto_clock_out(self):
        """Automatically clocks out any cooks still logged in at 11:00 PM local time (converted to UTC)."""
        print("Running auto clock-out...")

        if not os.path.exists(db_path):
            print("Database not found, cannot process auto clock-out.")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # ✅ Find all cooks still clocked in (clock_out_time IS NULL)
        cursor.execute('''
            SELECT id, employee_name FROM clock_logs
            WHERE clock_out_time IS NULL
        ''')
        active_users = cursor.fetchall()

        if not active_users:
            print("No active cooks to clock out.")
        else:
            # ✅ Set local time to 11:00 PM
            local_tz = pytz.timezone("America/New_York")  # Change this to your timezone!
            local_time = datetime.now(local_tz).replace(hour=23, minute=0, second=0, microsecond=0)

            # ✅ Convert to UTC
            clock_out_time_utc = local_time.astimezone(pytz.utc).isoformat()

            for user_id, employee_name in active_users:
                cursor.execute('''
                    UPDATE clock_logs
                    SET clock_out_time = ?, status = 'Clocked Out'
                    WHERE id = ?
                ''', (clock_out_time_utc, user_id))
                print(f"Clocked out {employee_name} at {clock_out_time_utc} UTC.")

            conn.commit()

        conn.close()

        # ✅ Reschedule for the next day
        self.schedule_auto_clock_out()


if __name__ == "__main__":
    TicketApp().run()
