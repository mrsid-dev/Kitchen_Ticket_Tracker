import sqlite3, os, json
from datetime import datetime, timezone
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from utils.customboxlayouts import RoundedButton, ColoredBoxLayout
from utils.global_context import GlobalContext
from kivy.uix.popup import Popup
from db.db_initialization import db_path


LAST_USER_FILE = "last_user.json"

def save_last_logged_in(cook_name, cook_pin):
    """Save the last logged-in cook to a file."""
    data = {"name": cook_name, "pin": cook_pin}
    with open(LAST_USER_FILE, "w") as file:
        json.dump(data, file)

def get_last_logged_in():
    """Load the last logged-in cook from file."""
    try:
        with open(LAST_USER_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class KitchenLoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entered_pin = ""
        self.current_user = ""
        self.build_ui()  # Ensure UI is created immediately

    def build_ui(self):
        """Set up the UI for the login screen."""
        self.layout = ColoredBoxLayout(
            orientation="vertical",
            spacing=20,
            padding=(20, 50, 20, 50),
            color=(0.169, 0.329, 0.298, 1)
        )
        self.add_widget(self.layout)

        # Spacer
        self.layout.add_widget(Widget(size_hint_y=1))

        # Instruction Label
        self.instruction_label = Label(
            text="Enter Employee PIN:",
            size_hint=(1, None),
            height=60,
            font_size=40,
            color=(0.506, 0.522, 0.565, 1),
            bold=True
        )
        self.layout.add_widget(self.instruction_label)

        # PIN Display
        self.pin_display = Label(
            text="",
            size_hint=(1, None),
            height=100,
            font_size=75,
            color=(0.894, 0.898, 0.914, 1)
        )
        self.layout.add_widget(self.pin_display)

        # PIN Pad Layout
        pin_pad_layout = GridLayout(cols=3, size_hint=(1, None), height=600, spacing=10)

        for digit in "123456789":
            button = RoundedButton(
                text=digit,
                size_hint=(1, None),
                height=150,
                background_color=(0.373, 0.392, 0.408, 1),
                color=(0.894, 0.898, 0.914, 1),
                font_size=30,
                bold=True
            )
            button.bind(on_press=self.add_digit)
            pin_pad_layout.add_widget(button)

        # Centering 0 button
        pin_pad_layout.add_widget(Widget(size_hint=(0.33, None), height=100))  # Empty placeholder
        button_0 = RoundedButton(
            text="0",
            size_hint=(1, None),
            height=150,
            background_color=(0.373, 0.392, 0.408, 1),
            color=(0.894, 0.898, 0.914, 1),
            font_size=30,
            bold=True,
        )
        button_0.bind(on_press=self.add_digit)
        pin_pad_layout.add_widget(button_0)
        pin_pad_layout.add_widget(Widget(size_hint=(0.33, None), height=100))  # Empty placeholder

        self.layout.add_widget(pin_pad_layout)

        # Spacer
        self.layout.add_widget(Widget(size_hint_y=1))

        # Login & Clear Buttons
        action_layout = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=150,
            spacing=20,
        )

        # Login Button
        self.login_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=45]\uea77[/size][/font]   [size=40][b]Clock In[/b][/size]",
            size_hint=(1, None),
            height=150,
            background_normal="",
            background_color=(0.235, 0.435, 0.388, 1),
            color=(0.894, 0.898, 0.914, 1),
            markup=True
        )
        self.login_button.bind(on_press=self.verify_pin)
        action_layout.add_widget(self.login_button)

        # Clear Button
        self.clear_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=45]\ue14a[/size][/font]   [size=40][b]Clear[/b][/size]",
            size_hint=(1, None),
            height=150,
            background_normal="",
            background_color=(0.541, 0.29, 0.29, 1),
            color=(0.894, 0.898, 0.914, 1),
            markup=True
        )
        self.clear_button.bind(on_press=self.clear_pin)
        action_layout.add_widget(self.clear_button)

        self.layout.add_widget(action_layout)

    def add_digit(self, instance):
        if len(self.entered_pin) < 5:
            self.entered_pin += instance.text
            self.entered_pin = self.entered_pin[:5]  # Force max 5 digits
            self.pin_display.text = "*" * len(self.entered_pin)

    def clear_pin(self, instance):
        """Clear the entered PIN."""
        self.entered_pin = ""
        self.pin_display.text = ""

    def verify_pin(self, instance):
        """Check the database for the entered PIN and log clock-in."""
        pin = self.entered_pin
        if not pin:
            self.instruction_label.text = "PIN cannot be empty."
            return

        manager_credentials = {
            "0000": "Manager",
        }

        try:
            if pin in manager_credentials:
                self.current_user = manager_credentials[pin]
                GlobalContext.set_current_user({"name": self.current_user, "role": "Manager"})
                self.manager.transition.direction = "left"
                self.manager.current = "manager_screen"
                self.entered_pin = ""
                self.pin_display.text = ""
                return

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM cooks WHERE pin = ?", (pin,))
            result = cursor.fetchone()

            if result:
                employee_name = result[0]
                self.current_user = employee_name
                GlobalContext.set_current_user({"name": employee_name, "role": "Cook"})
                clock_in_time = datetime.now(timezone.utc).isoformat()
                cursor.execute('''
                    INSERT INTO clock_logs (employee_name, clock_in_time, status)
                    VALUES (?, ?, ?)
                ''', (employee_name, clock_in_time, "Clocked In"))
                conn.commit()

                # ✅ Check the last logged-in user BEFORE updating
                last_user = get_last_logged_in()

                if last_user and last_user["pin"] != self.entered_pin:
                    self.manager.get_screen("kitchen_panel").clear_tickets()

                # ✅ NOW save the new user AFTER clearing if needed
                save_last_logged_in(self.current_user, self.entered_pin)

                self.manager.transition.direction = "left"
                kitchen_screen = self.manager.get_screen("kitchen_panel")
                kitchen_screen.cook_name = employee_name
                kitchen_screen.entered_pin = pin
                kitchen_screen.cook_label.text = f"[color=#E4E5E9][b]Cook:[/b][/color]\n[color=#818590]{employee_name}[/color]"
                self.manager.current = "kitchen_panel"
                self.entered_pin = ""
                self.pin_display.text = ""
            else:
                self.instruction_label.text = "Invalid PIN. Please try again."
                self.entered_pin = ""
                self.pin_display.text = ""

            conn.close()
        except Exception as e:
            print(f"Error in verify_pin: {e}")
            self.instruction_label.text = "An error occurred. Please try again."
            self.clear_pin(instance)

    def update_bg(self, instance, *args):
        self.bg_rect.size = instance.size
        self.bg_rect.pos = instance.pos

    def request_manager_approval(self, on_approval):
        """Show a popup requesting manager approval."""
        popup_layout = BoxLayout(orientation="vertical", spacing=20, padding=20)

        # Instruction label
        instruction_label = Label(
            text="Enter Manager PIN:",
            size_hint=(1, None),
            height=60,
            font_size=40,
            color=(0.894, 0.898, 0.914, 1),
            bold=True,
        )
        popup_layout.add_widget(instruction_label)

        # PIN display
        pin_display = Label(
            text="",
            size_hint=(1, None),
            height=60,
            font_size=50,
            color=(0.894, 0.898, 0.914, 1),
        )
        popup_layout.add_widget(pin_display)

        # Add a spacer to ensure proper positioning
        popup_layout.add_widget(Widget(size_hint=(1, None), height=20))  # Spacer

        # PIN pad layout
        pin_pad_layout = GridLayout(cols=3, spacing=10, size_hint=(1, None), height=400)
        entered_pin = []

        def add_digit(instance):
            if len(entered_pin) < 5:
                entered_pin.append(instance.text)
                pin_display.text = "*" * len(entered_pin)

        def clear_pin(instance):
            entered_pin.clear()
            pin_display.text = ""

        for digit in "123456789":
            button = RoundedButton(
                text=digit,
                font_size=40,
                bold=True,
                size_hint=(1, None),
                height=100,
                background_color=(0.302, 0.486, 0.443, 1),
                color=(0.894, 0.898, 0.914, 1),
            )
            button.bind(on_press=add_digit)
            pin_pad_layout.add_widget(button)

        # Add the 0 button centered at the bottom
        pin_pad_layout.add_widget(Widget(size_hint=(0.33, None), height=100))  # Empty placeholder
        button_0 = RoundedButton(
            text="0",
            font_size=40,
            bold=True,
            size_hint=(1, None),
            height=100,
            background_color=(0.302, 0.486, 0.443, 1),
            color=(0.894, 0.898, 0.914, 1),
        )
        button_0.bind(on_press=add_digit)
        pin_pad_layout.add_widget(button_0)
        pin_pad_layout.add_widget(Widget(size_hint=(0.33, None), height=100))  # Empty placeholder

        popup_layout.add_widget(pin_pad_layout)

        # Add another spacer below the pin pad
        popup_layout.add_widget(Widget(size_hint=(1, None), height=20))  # Spacer

        # Approval and Cancel buttons
        action_layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=100, spacing=20)

        def approve(instance):
            entered_pin_str = "".join(entered_pin)
            manager_credentials = {
                "34": "Greg",
                "168": "Quinn",
                "90": "Carol",
                "130": "Toby",
                "79": "Sara",
            }
            if entered_pin_str in manager_credentials:
                on_approval(True)  # Notify success
                popup.dismiss()
            else:
                instruction_label.text = "Invalid PIN. Try again."
                clear_pin(instance)

        def cancel(instance):
            on_approval(False)  # Notify failure
            popup.dismiss()

        approve_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=45]\ue5ca[/size][/font]  [size=40][b]Approve[/b][/size]",
            size_hint=(1, None),
            height=100,
            background_color=(0.235, 0.435, 0.388, 1),
            color=(0.894, 0.898, 0.914, 1),
            markup=True
        )
        approve_button.bind(on_press=approve)
        action_layout.add_widget(approve_button)

        cancel_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=45]\ue5cd[/size][/font]   [size=40][b]Cancel[/b][/size]",
            size_hint=(1, None),
            height=100,
            background_color=(0.541, 0.29, 0.29, 1),
            color=(0.894, 0.898, 0.914, 1),
            markup=True
        )
        cancel_button.bind(on_press=cancel)
        action_layout.add_widget(cancel_button)

        popup_layout.add_widget(action_layout)

        # Create the popup
        popup = Popup(
            title="Manager Approval",
            title_size=50,
            content=popup_layout,
            size_hint=(0.8, None),
            height=1000,
            auto_dismiss=False,
            separator_color=(0.169, 0.329, 0.298, 1),
            title_align='center'
        )
        popup.open()

    def on_leave(self, *args):
        self.instruction_label.text = "Enter Employee PIN:"
