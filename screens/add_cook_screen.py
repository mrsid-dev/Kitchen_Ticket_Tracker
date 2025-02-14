from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.uix.anchorlayout import AnchorLayout
from utils.customboxlayouts import RoundedButton
import sqlite3
from db.db_initialization import db_path  # ✅ Import the correct path


class AddCookScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.side = None  # Track the active side

        # Set green background color
        with self.canvas.before:
            Color(0.118, 0.231, 0.208, 1)  # Green background color
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self.update_background, pos=self.update_background)

        # **Main Layout (Vertical Box)**
        self.layout = BoxLayout(orientation="vertical", spacing=10, padding=(20, 20, 20, 20))
        self.add_widget(self.layout)

        # **Title Container at the Top**
        title_container = AnchorLayout(anchor_y="top", size_hint_y=None, height=120)

        # **Title Label**
        title_label = Label(
            text="[b][u]Add a Cook[/u][/b]",
            font_size=50,
            markup=True,
            size_hint=(1, None),
            height=120,
            color=(0.894, 0.898, 0.914, 1),  # Light gray color
            halign="center",
            valign="middle"
        )
        title_label.bind(size=lambda instance, value: setattr(instance, "text_size", value))  # Proper text wrapping

        title_container.add_widget(title_label)
        self.layout.add_widget(title_container)

        # **Middle Content Layout (Takes Up Available Space)**
        content_layout = BoxLayout(orientation="vertical", spacing=10, size_hint=(1, 1))

        # **Message Label**
        self.message_label = Label(
            text="",
            size_hint=(1, None),
            height=60,  # Reduce height slightly
            color=(0.894, 0.898, 0.914, 1)
        )
        content_layout.add_widget(self.message_label)

        # **Cook Name Input**
        content_layout.add_widget(Label(
            text="Enter Cook Name:",
            size_hint=(1, None),
            height=60,
            font_size=35,
            color=(0.894, 0.898, 0.914, 1)  # Light gray
        ))
        self.name_input = TextInput(
            size_hint=(1, None),
            font_size=50,
            height=100,
            background_color=(0.247, 0.475, 0.424, 1),
            foreground_color=(0.894, 0.898, 0.914, 1)
        )
        content_layout.add_widget(self.name_input)

        # **PIN Input**
        content_layout.add_widget(Label(
            text="Enter Cook PIN:",
            size_hint=(1, None),
            height=60,
            font_size=35,
            color=(0.894, 0.898, 0.914, 1)
        ))
        self.pin_input = TextInput(
            size_hint=(1, None),
            font_size=50,
            height=100,
            input_filter="int",
            input_type="number",
            background_color=(0.247, 0.475, 0.424, 1),
            foreground_color=(0.894, 0.898, 0.914, 1)
        )
        content_layout.add_widget(self.pin_input)

        # **Spacer Widget to Keep Content Centered**
        content_layout.add_widget(Widget(size_hint_y=1))

        # **Add Middle Content Layout**
        self.layout.add_widget(content_layout)

        # **Button Layout (At the Bottom)**
        button_layout = BoxLayout(orientation="horizontal", spacing=20, size_hint=(1, None), height=120)

        # **Save Button**
        save_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=45]\ue145[/size][/font]  [size=40][b]Add[/b][/size]",
            size_hint=(1, None),
            height=120,
            background_color=(0.235, 0.435, 0.388, 1),  # Bright green
            color=(0.894, 0.898, 0.914, 1),
            markup=True
        )
        save_button.bind(on_press=self.save_cook)
        button_layout.add_widget(save_button)

        # **Cancel Button**
        cancel_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=45]\ue5cd[/size][/font]  [size=40][b]Cancel[/b][/size]",
            size_hint=(1, None),
            height=120,
            background_color=(0.541, 0.29, 0.29, 1),
            color=(0.894, 0.898, 0.914, 1),
            markup=True
        )
        cancel_button.bind(on_press=self.cancel_action)
        button_layout.add_widget(cancel_button)

        # **Add Button Layout at the Bottom**
        self.layout.add_widget(button_layout)

    def update_background(self, *args):
        """Update background size and position."""
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

    def save_cook(self, instance):
        """Save the new cook to the database."""
        name = self.name_input.text.strip()
        pin = self.pin_input.text.strip()

        if not name or not pin:
            self.show_message("Both name and PIN are required.", error=True)
            return

        try:
            from db.db_initialization import db_path  # ✅ Use the correct database path
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Insert the new cook into the cooks table
            cursor.execute("INSERT INTO cooks (pin, name) VALUES (?, ?)", (int(pin), name))
            conn.commit()
            self.show_message(f"Cook {name} added successfully!", error=False)

            # Clear inputs and return to the previous screen
            self.name_input.text = ""
            self.pin_input.text = ""
            self.manager.current = "kitchen_login"
        except sqlite3.IntegrityError:
            conn.rollback()  # ✅ Rollback transaction to prevent lock issues
            self.show_message(f"Error: A cook with PIN {pin} already exists.", error=True)
        finally:
            conn.close()  # ✅ Always close the database connection

    def cancel_action(self, instance):
        """Return to the appropriate login panel based on the side."""
        self.manager.current = "manager_screen"

    def show_message(self, message, error=True):
        """Display a message on the screen."""
        self.message_label.text = message
        self.message_label.color = (0.894, 0.898, 0.914, 1) if not error else (0.541, 0.29, 0.29, 1)

    def on_leave(self, *args):
        """Reset the screen state when leaving."""
        self.message_label.text = ""
