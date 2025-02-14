from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from screens.add_cook_screen import AddCookScreen
from screens.performance_menu_screen import PerformanceMenuScreen
from screens.clock_logs_screen import ClockLogsScreen
from utils.customboxlayouts import RoundedButton, ColoredBoxLayout, BoxLayout
from kivy.uix.gridlayout import GridLayout


class ManagerScreen(Screen):
    def __init__(self, app, **kwargs):
        """
        Initializes the ManagerScreen with access to the main app for screen switching.

        :param app: Reference to the main app instance for calling screen management methods.
        """
        super().__init__(**kwargs)
        self.app = app  # Reference to the main app for screen switching

        from kivy.uix.anchorlayout import AnchorLayout

        # Main layout with background color
        self.layout = ColoredBoxLayout(
            orientation="vertical",
            color=(0.118, 0.231, 0.208, 1),
            padding=(0, 0, 0, 30)  # Keep bottom padding for the Clock Out button
        )

        # Create an AnchorLayout to force the title to the very top
        header_container = AnchorLayout(anchor_y="top")

        # Header container (BoxLayout)
        header = BoxLayout(size_hint=(1, None), height=100)

        # Title label
        title_label = Label(
            text="Manager Dashboard",
            font_size=50,
            color=(0.894, 0.898, 0.914, 1),
            size_hint=(1, None),
            height=100,
            bold=True,
            halign="center",
            valign="middle",
            underline=True
        )
        title_label.bind(
            size=lambda instance, value: setattr(instance, "text_size", value))  # Ensures proper text wrapping

        # Add label to header
        header.add_widget(title_label)

        # Add header to the anchor container
        header_container.add_widget(header)

        # Add header container FIRST so it stays at the very top
        self.layout.add_widget(header_container)

        button_grid = GridLayout(cols=2, spacing=20, size_hint=(0.9, None), pos_hint={"center_x": 0.5, "center_y": 0.6})
        button_width = 0.4  # Percentage of screen width
        button_height = 0.25  # Percentage of screen height

        # Adding buttons to the grid
        button_grid.add_widget(RoundedButton(
            text="[size=30][b]Clock Logs[/b][/size]\n[font=fonts/MaterialIcons-Regular.ttf][size=120]\uf1bb[/size][/font]",
            size_hint=(0.45, None),  # Adjust dynamically (takes 45% of available width)
            height="450",  # Use dp for scaling properly
            color=(0.894, 0.898, 0.914, 1),  # Light text color
            background_color=(0.651, 0.4, 0.267, 1),
            radius=30,
            on_press=lambda _: self.app.add_or_switch(self.manager, "clock_logs", ClockLogsScreen),
            markup=True,
            halign="center",
        ))
        button_grid.add_widget(RoundedButton(
            text="[size=30][b]Performance Page[/b][/size]\n[font=fonts/MaterialIcons-Regular.ttf][size=120]\ue0ee[/size][/font]",
            size_hint=(0.45, None),  # Adjust dynamically (takes 45% of available width)
            height="450",  # Use dp for scaling properly
            color=(0.894, 0.898, 0.914, 1),
            background_color=(0.714, 0.569, 0.129, 1),
            radius=30,
            markup=True,
            halign="center",
            on_press=lambda _: self.app.add_or_switch(self.manager, "performance_menu", PerformanceMenuScreen)
        ))
        button_grid.add_widget(RoundedButton(
            text="[size=30][b]Add Cook[/b][/size]\n[font=fonts/MaterialIcons-Regular.ttf][size=120]\ue7fe[/size][/font]",
            size_hint=(0.45, None),  # Adjust dynamically (takes 45% of available width)
            height="450",  # Use dp for scaling properly
            color=(0.894, 0.898, 0.914, 1),
            background_color=(0.373, 0.392, 0.408, 1),
            radius=30,
            markup=True,
            halign="center",
            on_press=lambda _: self.app.add_or_switch(self.manager, "add_cook", AddCookScreen)
        ))
        button_grid.add_widget(Widget(size_hint=(None, None), size=(button_width, button_height)))  # Blank for symmetry

        # Set grid size
        button_grid.size_hint_y = None
        button_grid.height = 950  # Adjust as needed


        # Add the button grid to the layout
        self.layout.add_widget(button_grid)

        # Spacer between the grid and the Clock Out button
        middle_spacer = Widget(size_hint_y=None, height=150)
        self.layout.add_widget(middle_spacer)

        # Clock Out button
        self.clock_out_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=45]\ue9ba[/size][/font] [size=40][b]Clock Out[/b][/size]",
            radius=30,
            color=(0.894, 0.898, 0.914, 1),  # Light text color
            size_hint=(0.9, None),
            height=150,  # Width and height
            background_color=(0.541, 0.29, 0.29, 1),  # Bright red
            markup=True
        )
        self.clock_out_button.bind(on_press=self.clock_out)

        # Add Clock Out button to the layout
        self.layout.add_widget(self.clock_out_button)
        self.clock_out_button.pos_hint = {"center_x": 0.5, "y": 0.05}  # Fixed near the bottom

        # Add the main layout to the screen
        self.add_widget(self.layout)

    def clock_out(self, instance):
        # Get the corresponding login screen
        login_screen = self.manager.get_screen("kitchen_login")
        login_screen.clear_pin(None)  # Clear the entered PIN

        # Transition back to the login screen
        self.manager.transition.direction = "right"
        self.manager.current = "kitchen_login"
