from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from datetime import datetime
from utils.customboxlayouts import RoundedBoxLayout, RoundedButton, ColoredBoxLayout
import sqlite3, pytz
from db.db_initialization import db_path


class ClockLogsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Main Layout
        main_layout = ColoredBoxLayout(orientation="vertical", spacing=10, padding=20, color=(0.118, 0.231, 0.208, 1))
        self.add_widget(main_layout)

        # Header (Title)
        header = BoxLayout(size_hint=(1, None), height=50)
        self.title_label = Label(text="Clock-In Logs", font_size=50, size_hint=(1, None), height=40, bold=True, underline=True)
        header.add_widget(self.title_label)
        main_layout.add_widget(header)

        # Scrollable Middle Content
        scrollable_container = BoxLayout(orientation="vertical", size_hint=(1, 1), padding=10)
        scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.data_container = BoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        self.data_container.bind(minimum_height=self.data_container.setter("height"))
        scroll_view.add_widget(self.data_container)
        scrollable_container.add_widget(scroll_view)
        main_layout.add_widget(scrollable_container)

        # Footer (Buttons)
        footer = BoxLayout(orientation="horizontal", size_hint=(1, None), height=150, spacing=10)
        self.back_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=45]\ue2ea[/size][/font] [size=40][b]Back[/b][/size]",
            size_hint_y=None,
            height=150,
            background_normal="",
            background_color=(0.541, 0.29, 0.29, 1),  # Bright red
            markup=True
        )
        self.back_button.bind(on_press=self.go_back)
        footer.add_widget(self.back_button)

        main_layout.add_widget(footer)

        # Populate clock logs initially
        self.populate_logs()

    def on_pre_enter(self, *args):
        """Refresh logs every time the screen is entered."""
        self.populate_logs()

    def populate_logs(self):
        """Fetch and display clock-in logs from the database."""
        self.data_container.clear_widgets()

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Query clock logs
            cursor.execute('''
                SELECT employee_name, clock_in_time, clock_out_time, status
                FROM clock_logs
                ORDER BY clock_in_time DESC
            ''')
            results = cursor.fetchall()
            conn.close()

            if not results:
                self.data_container.add_widget(Label(text="No clock-in logs found!", font_size=18))
                return

            # Define timezone adjustment and formats
            date_format = "%a %b %d"  # Format for the day header
            time_format = "%I:%M%p"  # Format for clock-in and clock-out times

            # Group logs by day
            logs_by_date = {}
            for employee_name, clock_in, clock_out, status in results:
                # Parse and adjust clock-in time
                clock_in_dt = self.parse_iso_datetime(clock_in)
                formatted_clock_in = clock_in_dt.strftime(time_format)  # Now shows correct local time
                clock_in_date = clock_in_dt.strftime(date_format)  # Group by this date

                # Parse and adjust clock-out time if available
                if clock_out:
                    clock_out_dt = self.parse_iso_datetime(clock_out)
                    formatted_clock_out = clock_out_dt.strftime(time_format)
                else:
                    formatted_clock_out = "N/A"

                # Group logs by date
                logs_by_date.setdefault(clock_in_date, []).append(
                    (employee_name, formatted_clock_in, formatted_clock_out, status))

            # Display logs grouped by date
            for log_date, logs in logs_by_date.items():
                # Create a grid for logs within a ScrollView
                grid = GridLayout(cols=4, spacing=10, size_hint_y=None, padding=[20, 10, 20, 10])
                grid.bind(minimum_height=grid.setter("height"))

                # Add headers
                headers = ["Name", "Clock-In", "Clock-Out", "Status"]
                for header in headers:
                    grid.add_widget(Label(text=header, bold=True, size_hint_y=None, height=40, underline=True))

                # Add log entries
                for employee_name, clock_in, clock_out, status in logs:
                    grid.add_widget(Label(text=employee_name, size_hint_y=None, height=40))
                    grid.add_widget(Label(text=clock_in, size_hint_y=None, height=40))
                    grid.add_widget(Label(text=clock_out, size_hint_y=None, height=40))
                    grid.add_widget(Label(text=status, size_hint_y=None, height=40))

                # Wrap the grid in a ScrollView for individual day scrolling
                day_scroll_view = ScrollView(size_hint=(1, None), height=300)  # Adjust height as needed
                day_scroll_view.add_widget(grid)

                # Create a container for the rounded box
                container = BoxLayout(orientation="vertical", size_hint=(0.95, None))

                # Add a properly sized date label inside the rounded box
                date_label = Label(
                    text=f"[b]{log_date}[/b]",
                    size_hint_y=None,
                    height=50,
                    markup=True,
                    bold=True,
                    color=(0.714, 0.569, 0.129, 1),
                    underline=True
                )

                # Wrap the ScrollView and date label in a rounded box
                rounded_box = RoundedBoxLayout(
                    orientation="vertical",
                    size_hint=(0.95, None),
                    padding=30,
                    spacing=10,
                    color=(0.204, 0.408, 0.373, 1),  # Green background
                    valign="left",
                )
                rounded_box.add_widget(date_label)
                rounded_box.add_widget(day_scroll_view)  # Add the ScrollView here

                # Outer container for visual distinction
                rounded_box_outter = RoundedBoxLayout(
                    orientation="vertical",
                    size_hint=(1, None),
                    padding=2,
                    spacing=2,
                    color=(0.247, 0.475, 0.424, 1)
                )

                # Set the container height dynamically
                container.height = day_scroll_view.height + 120  # ScrollView height + date label height + padding
                container.add_widget(rounded_box_outter)
                rounded_box_outter.add_widget(rounded_box)

                # Add the container to the main data container
                self.data_container.add_widget(container)

        except Exception as e:
            self.data_container.add_widget(Label(
                text=f"Error loading logs: {e}",
                font_size=18,
                color=(1, 0, 0, 1),
                size_hint=(1, None),
                height=40
            ))

    @staticmethod
    def parse_iso_datetime(iso_string):
        """Parse UTC timestamp with +00:00 and convert to local time."""
        if not iso_string:
            return datetime.now(pytz.utc).astimezone(pytz.timezone("US/Eastern"))

        eastern = pytz.timezone("US/Eastern")

        try:
            utc_dt = datetime.fromisoformat(iso_string)  # ✅ Parses ISO format with +00:00 automatically
            return utc_dt.astimezone(eastern)  # ✅ Convert UTC → EST/EDT
        except ValueError:
            return datetime.now(pytz.utc).astimezone(eastern)  # ✅ Default fallback

    def go_back(self, instance):
        """Navigate back to the manager screen."""
        self.manager.current = "manager_screen"

    def on_leave(self, *args):
        """Clear all widgets to fully reset the screen when leaving."""
        self.data_container.clear_widgets()
