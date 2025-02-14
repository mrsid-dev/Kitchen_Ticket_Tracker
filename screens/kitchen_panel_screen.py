import sqlite3, datetime, pytz, time, os, json
from kivy.utils import platform
from datetime import datetime, timezone
from utils.global_context import GlobalContext
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from utils.customboxlayouts import ColoredBoxLayout, RoundedBoxLayout, RoundedButton
from db.db_initialization import db_path


if platform == "android":
    from android.permissions import request_permissions, Permission
    from jnius import autoclass

    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

    # ✅ Get Android's external app storage directory (same as `db_folder`)
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    app_context = PythonActivity.mActivity.getApplicationContext()
    storage_folder = app_context.getExternalFilesDir(None).getAbsolutePath()

else:
    storage_folder = "./"  # Fallback for PC/Mac testing

# ✅ Ensure the folder exists
if not os.path.exists(storage_folder):
    os.makedirs(storage_folder, exist_ok=True)

# ✅ Define the path for last_user.json
LAST_USER_FILE = os.path.join(storage_folder, "last_user.json")

def get_last_logged_in():
    """Load the last logged-in cook from file."""
    try:
        with open(LAST_USER_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def clear_last_logged_in():
    """Clear the last logged-in user file."""
    if os.path.exists(LAST_USER_FILE):
        os.remove(LAST_USER_FILE)


class KitchenPanel(Screen):
    ticket_storage = []  # Stores ticket data
    displayed_ticket_ids = set()  # Tracks which tickets have been added to the UI
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cook_name = ""
        self.ticket_count = 0
        self.timers = {}
        self.entered_pin = ""

        # Schedule auto logout at 10:45 PM
        self.schedule_auto_logout()

        # Main layout
        self.layout = ColoredBoxLayout(orientation="vertical", spacing=10, padding=15, color=(0.118, 0.231, 0.208, 1))
        self.add_widget(self.layout)

        # Real-Time Performance Section
        self.performance_section = BoxLayout(orientation="horizontal", size_hint=(1, None), height=100, spacing=20)
        self.cook_label = Label(text="[color=#E4E5E9][b]Cook:[/b][/color]\n[color=#818590][Not Logged In][/color]", font_size=30, markup=True, halign="center")
        self.avg_label = Label(text="[color=#E4E5E9][b]Average:[/b][/color]\n[color=#818590]--:--[/color]", markup=True, halign="center", font_size=30)
        self.fastest_label = Label(text="[color=#E4E5E9][b]Shortest:[/b][/color]\n[color=#818590]--:--[/color]", markup=True, halign="center", font_size=30)
        self.slowest_label = Label(text="[color=#E4E5E9][b]Longest:[/b][/color]\n[color=#818590]--:--[/color]", markup=True, halign="center", font_size=30)
        self.tickets_label = Label(text="[color=#E4E5E9][b]Tickets:[/b][/color]\n[color=#818590]--[/color]", markup=True, halign="center", font_size=30)
        self.performance_section.add_widget(self.cook_label)
        self.performance_section.add_widget(self.avg_label)
        self.performance_section.add_widget(self.fastest_label)
        self.performance_section.add_widget(self.slowest_label)
        self.performance_section.add_widget(self.tickets_label)
        self.layout.add_widget(self.performance_section)

        # Main container (acts as a background)
        self.ticket_list = RoundedBoxLayout(
            orientation="vertical",
            size_hint=(1, 0.6),  # Ensures the entire block fits in the UI
            spacing=10,
            color=(0.169, 0.329, 0.298, 1),
            padding=[10, 10, 10, 10]
        )

        # ScrollView (now inside ticket_list)
        self.scroll = ScrollView(
            size_hint=(1, 1),  # Take full height of the ticket_list
            do_scroll_x=False,
            do_scroll_y=True,
            scroll_type=['bars', 'content'],  # Allow scrolling with bar and touch
            effect_cls="ScrollEffect"
        )

        # Container inside ScrollView that holds tickets
        self.ticket_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,  # Allow height to grow dynamically
            height=10,  # Start at a small height so scrolling works
            spacing=10,
        )

        # Add ticket container to ScrollView
        self.scroll.add_widget(self.ticket_container)
        # Add ScrollView to ticket_list (now acts as a background)
        self.ticket_list.add_widget(self.scroll)
        # Add ticket_list to main layout
        self.layout.add_widget(self.ticket_list)

        # Buttons layout
        buttons_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=130, spacing=20, padding=10)

        # Add ticket button
        self.add_ticket_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=50]\ue8b0[/size][/font]   [size=45][b]Add Ticket[/b][/size]",
            radius=30,
            color=(0.894, 0.898, 0.914, 1),
            size_hint_x=0.5,
            background_normal="",
            background_color=(0.235, 0.435, 0.388, 1),  # Bright green (#219f6e)
            markup=True
        )
        self.add_ticket_button.bind(on_press=self.add_ticket)
        buttons_layout.add_widget(self.add_ticket_button)

        # Clock out button
        self.clock_out_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=50]\ue9ba[/size][/font] [size=45][b]Clock Out[/b][/size]",
            radius=30,
            color=(0.894, 0.898, 0.914, 1),
            size_hint_x=0.5,
            background_normal="",
            background_color=(0.541, 0.29, 0.29, 1),
            disabled=False,
            markup=True
        )
        self.clock_out_button.bind(on_press=self.clock_out)
        buttons_layout.add_widget(self.clock_out_button)

        self.layout.add_widget(buttons_layout)

        # Start real-time performance updates
        self.update_stats()

    def update_stats(self):
        """Update real-time performance stats for the logged-in cook."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get current local date in YYYY-MM-DD format
        local_tz = pytz.timezone("America/New_York")  # Change to your actual timezone
        local_now = datetime.now(local_tz)
        today_local = local_now.strftime("%Y-%m-%d")

        # Query stats for the logged-in cook, only for today (local timezone)
        cursor.execute("""
            SELECT 
                MIN(time_taken) AS fastest,
                MAX(time_taken) AS slowest,
                AVG(time_taken) AS average,
                COUNT(*) AS ticket_count
            FROM tickets
            WHERE cook_pin = (
                SELECT pin FROM cooks WHERE name = ?
            ) AND date(datetime(date)) = ?
        """, (self.cook_name, today_local))

        stats = cursor.fetchone()
        conn.close()

        if stats:
            fastest, slowest, average, ticket_count = stats
            self.fastest_label.text = f"[color=#E4E5E9][b]Shortest:[/b][/color]\n[color=#818590]{self.format_time(fastest)}[/color]" if fastest else "[color=#E4E5E9][b]Shortest:[/b][/color]\n[color=#818590]--:--[/color]"
            self.slowest_label.text = f"[color=#E4E5E9][b]Longest:[/b][/color]\n[color=#818590]{self.format_time(slowest)}[/color]" if slowest else "[color=#E4E5E9][b]Longest:[/b][/color]\n[color=#818590]--:--[/color]"
            self.avg_label.text = f"[color=#E4E5E9][b]Average:[/b][/color]\n[color=#818590]{self.format_time(average)}[/color]" if average else "[color=#E4E5E9][b]Average:[/b][/color]\n[color=#818590]--:--[/color]"
            self.tickets_label.text = f"[color=#E4E5E9][b]Tickets:[/b][/color]\n[color=#818590]{ticket_count}[/color]" if ticket_count else "[color=#E4E5E9][b]Tickets:[/b][/color]\n[color=#818590]--[/color]"

    @staticmethod
    def format_time(seconds):
        """Convert seconds to minute:second format."""
        if seconds is None:
            return "--:--"
        minutes, seconds = divmod(int(seconds), 60)
        return f"{minutes}:{seconds:02d}"

    def check_timers(self):
        """Disables Clock Out button if any timers are running."""
        active_timers = any(ticket["running"] for ticket in self.timers.values())
        self.clock_out_button.disabled = active_timers

    def add_ticket(self, instance):
        """Add a ticket and start its timer."""

        if not self.entered_pin:
            print("Error: PIN is not set. Cannot add ticket.")
            return

        self.ticket_count += 1
        ticket_id = self.ticket_count
        start_time = time.time()
        self.timers[ticket_id] = {"start_time": start_time, "running": True}
        time_elapsed = [0]  # Mutable list to track elapsed time
        ticket_metadata = {"ticket_id": ticket_id, "cook_pin": self.entered_pin}

        self.check_timers()

        # Outer container for swipe functionality
        swipe_container = BoxLayout(
            orientation="horizontal",
            size_hint=(0.99, None),  # Make it 90% of available width
            height=130,
        )
        swipe_container.pos_hint = {"center_x": 0.5}  # Center the swipe container

        # Main Ticket Layout (your original design)
        ticket_layout_outer = RoundedBoxLayout(
            radius=30,
            color=(0.247, 0.475, 0.424, 1),
            orientation="horizontal",
            padding=2,
            spacing=2,
            size_hint=(0.99, None),  # Reduce width further to 85% of available space
            height=129,
        )

        ticket_layout = RoundedBoxLayout(
            radius=30,
            color=(0.204, 0.408, 0.373, 1),
            orientation="horizontal",
            padding=10,
            size_hint=(1, None),  # Make the main ticket slightly smaller
            height=125,
        )

        # Ticket Info Label
        ticket_label = Label(
            text=f"[b][u]Ticket[/u][/b]:\nOpen",
            color=(0.894, 0.898, 0.914, 1),
            size_hint=(0.25, 1),
            halign="center",
            valign="middle",
            bold=True,
            font_size=30,
            markup=True
        )
        ticket_label.bind(size=lambda instance, value: ticket_label.setter("text_size")(instance, value))
        ticket_layout.add_widget(ticket_label)

        # Timer Label
        timer_label = Label(
            text="[b][u]Time:[/u][/b]\n0:00",
            color=(0.894, 0.898, 0.914, 1),
            size_hint=(0.5, 1),
            halign="center",
            valign="middle",
            font_size=30,
            markup=True
        )
        timer_label.bind(size=lambda instance, value: timer_label.setter("text_size")(instance, value))
        ticket_layout.add_widget(timer_label)

        # Order Out Button
        order_out_button = RoundedButton(
            text="[font=fonts/MaterialIcons-Regular.ttf][size=60]\ueb49[/size][/font]\n[size=30][b]Order[/b][/size]",
            radius=30,
            size_hint=(0.2, 1),
            halign="center",
            background_color=(0.714, 0.569, 0.129, 1),
            color=(0.894, 0.898, 0.914, 1),
            markup=True
        )

        # Order Out logic
        def order_out_callback(instance):
            """Handles Order Out action, logs ticket data, and stops the timer."""
            elapsed_time = self.get_elapsed_time(ticket_id)
            minutes, seconds = divmod(elapsed_time, 60)
            timer_label.text = f"[b][u]Time:[/u][/b]\n{minutes}:{seconds:02d}"

            # 🔹 Stop tracking and ensure the timer is stopped
            if ticket_id in self.timers:
                self.timers[ticket_id]["running"] = False  # Mark timer as stopped
                if f"timer_{ticket_id}" in self.timers:
                    Clock.unschedule(self.timers[f"timer_{ticket_id}"])
                    del self.timers[f"timer_{ticket_id}"]  # Remove from tracking

            # 🔹 Ensure the order out button is disabled
            order_out_button.disabled = True

            # 🔹 Store the completed ticket
            KitchenPanel.ticket_storage.append({
                "ticket_id": ticket_id,
                "time_elapsed": elapsed_time,
            })

            # Preserve "Handed Off:\nCook Name" but change (Open) to (Sold)
            if "Handed Off" in ticket_label.text:
                cook_name = ticket_label.text.replace("[b][u]Handed Off:[/u][/b]\n[size=24]", "").replace(" (Open)[/size]", "").strip()
                final_label_text = f"[b][u]Handed Off:[/u][/b]\n[size=24]{cook_name} (Sold)[/size]"
            else:
                final_label_text = "[b][u]Ticket[/u][/b]:\nSold"

            # Update UI
            ticket_label.text = final_label_text
            timer_label.text = f"[b][u]Time:[/u][/b]\n{minutes}:{seconds:02d}"
            ticket_label.color = (0.506, 0.522, 0.565, 1)
            timer_label.color = (0.506, 0.522, 0.565, 1)
            ticket_label.color = (0.506, 0.522, 0.565, 1)

            # 🔹 Save ticket data
            if elapsed_time >= 120:
                self.log_ticket(self.entered_pin, elapsed_time)
                self.update_stats()

            self.check_timers()  # 🔹 Update button state
            hide_actions()
            swipe_container.unbind(on_touch_move=on_touch_move)

        order_out_button.bind(on_press=order_out_callback)
        ticket_layout.add_widget(order_out_button)

        ticket_layout_outer.add_widget(ticket_layout)

        # Hidden Action Layout (initially collapsed)
        action_layout = BoxLayout(
            orientation="horizontal",
            size_hint=(None, None),  # Disable size hints for explicit control
            width=0,  # Start fully collapsed
            height=130,
            spacing=10,  # Remove unnecessary spacing between elements
            padding=[10, 0, 0, 0],  # Add 10px padding to the left
        )
        temp_button = RoundedButton(
            text="[size=20][b]Hand Off[/b][/size]\n[font=fonts/MaterialIcons-Regular.ttf][size=60]\ue769[/size][/font]",
            radius=30,
            size_hint=(None, None),
            width=110,
            height=120,
            halign="center",
            valign="middle",
            background_color=(0.651, 0.4, 0.267, 1),
            color=(1, 1, 1, 1),
            pos_hint={'center_y': 0.5, 'center_x': 0.5},  # Center vertically
            markup=True
        )

        def hand_off_ticket(instance):
            """Handle ticket hand-off."""
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name, pin FROM cooks")  # Fetch all cooks
            cooks = cursor.fetchall()
            conn.close()

            if not cooks:
                print("No cooks are currently clocked in.")
                return

            # Create the popup layout
            popup_layout = BoxLayout(orientation="vertical", spacing=10, padding=(10, 10, 10, 10))  # Minimal padding

            # Create the popup
            popup = Popup(
                title="Select a cook to hand this ticket to...",  # Title
                title_size=30,  # Title size
                title_align='center',
                content=popup_layout,
                size_hint=(0.8, None),  # Dynamic height
                height=850,  # Adjusted popup height
                auto_dismiss=False,
                separator_color=(0.169, 0.329, 0.298, 1),
            )

            # Add a spacer to lower the ScrollView
            spacer = Label(size_hint_y=None, height=20)  # Add space below the title
            popup_layout.add_widget(spacer)

            # Add a scrollable list for cooks
            scroll_view = ScrollView(size_hint=(1, None), size=(400, 600))  # Reduce height for better fit
            list_layout = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=(0, 0, 0, 0))
            list_layout.bind(minimum_height=list_layout.setter("height"))

            for cook_name, cook_pin in cooks:
                cook_button = RoundedButton(
                    text=cook_name,
                    font_size=50,
                    bold=True,
                    size_hint=(1, None),
                    height=100,
                    background_color=(0.302, 0.486, 0.443, 1),  # Green background
                    color=(1, 1, 1, 1),  # White text
                )
                cook_button.bind(
                    on_release=lambda btn_instance, cook_data=(cook_name, cook_pin): dropdown_selected(cook_data)
                )
                list_layout.add_widget(cook_button)

            scroll_view.add_widget(list_layout)
            popup_layout.add_widget(scroll_view)

            # Create a cancel button
            cancel_button = RoundedButton(
                text="[font=fonts/MaterialIcons-Regular.ttf][size=45]\ue5cd[/size][/font]   [size=40][b]Cancel[/b][/size]",
                size_hint=(1, None),
                height=100,
                background_color=(0.541, 0.29, 0.29, 1),  # Red background
                color=(1, 1, 1, 1),  # White text
                markup=True
            )

            # Bind to both dismiss the popup and call hide_actions
            def cancel_and_hide_actions(instance):
                popup.dismiss()
                hide_actions()

            cancel_button.bind(on_release=cancel_and_hide_actions)
            popup_layout.add_widget(cancel_button)

            def dropdown_selected(cook_data):
                selected_cook_name, selected_cook_pin = cook_data
                popup.dismiss()

                def on_approval(approved):
                    if approved:
                        # Restart the timer and assign the ticket to the new cook
                        time_elapsed[0] = 0  # Reset the timer
                        ticket_label.text = f"[b][u]Handed Off:[/u][/b]\n[size=24]{selected_cook_name} (Open)[/size]"
                        ticket_metadata["cook_pin"] = selected_cook_pin
                        hide_actions()

                # Request manager approval
                login_screen = self.manager.get_screen("kitchen_login")
                login_screen.request_manager_approval(on_approval)

            popup.open()

        # Replace the Temp button logic
        temp_button.bind(on_press=lambda _: hand_off_ticket(temp_button))
        action_layout.add_widget(temp_button)

        # Cancel Button
        cancel_button = RoundedButton(
            text="[size=20][b]Cancel[/b][/size]\n[font=fonts/MaterialIcons-Regular.ttf][size=70]\ue872[/size][/font]",
            radius=30,
            size_hint=(None, None),
            width=110,
            height=120,
            halign="center",
            valign="middle",
            background_color=(0.541, 0.29, 0.29, 1),  # Red color
            color=(1, 1, 1, 1),  # White text
            pos_hint={'center_y': 0.5, 'center_x': 0.5},  # Center vertically
            markup=True
        )

        def cancel_ticket(instance):
            """Handle ticket cancellation with manager approval."""

            def on_approval(approved):
                if approved:
                    # Stop the timer
                    minutes, seconds = divmod(self.get_elapsed_time(ticket_id), 60)

                    if ticket_id in self.timers:
                        self.timers[ticket_id]["running"] = False  # 🔹 Stop the timer
                        if f"timer_{ticket_id}" in self.timers:
                            Clock.unschedule(self.timers[f"timer_{ticket_id}"])
                            del self.timers[f"timer_{ticket_id}"]  # Remove from tracking

                    # 🔹 Update UI
                    timer_label.text = f"[b][u]Time:[/u][/b]\n{minutes}:{seconds:02d}"
                    ticket_label.text = "[b][u]Ticket:[/u][/b]\nCanceled"
                    timer_label.color = (0.506, 0.522, 0.565, 1)
                    ticket_label.color = (0.506, 0.522, 0.565, 1)

                    # 🔹 Disable the Order Out button
                    order_out_button.disabled = True

                    # 🔹 Remove swipe gestures and hide actions
                    hide_actions()
                    swipe_container.unbind(on_touch_move=on_touch_move)

                    self.check_timers()  # 🔹 Update button state

            # 🔹 Request manager approval
            login_screen = self.manager.get_screen("kitchen_login")
            login_screen.request_manager_approval(on_approval)

        # Bind the Cancel button to the cancel_ticket function
        cancel_button.bind(on_press=cancel_ticket)
        action_layout.add_widget(cancel_button)

        def reveal_actions():
            anim = Animation(width=235, duration=0.2)  # Set target width for revealing
            anim.start(action_layout)

        def hide_actions():
            anim = Animation(width=0, duration=0.2)  # Collapse back to 0
            anim.start(action_layout)

        def on_touch_move(instance, touch, *args):
            """Allow scrolling while keeping swipe gestures."""
            if swipe_container.collide_point(*touch.pos):
                dx = touch.dx  # Horizontal movement
                dy = touch.dy  # Vertical movement

                if abs(dx) > abs(dy):  # If horizontal movement is greater, trigger swipe
                    if dx < -20:  # Swipe left to reveal buttons
                        reveal_actions()
                    elif dx > 20:  # Swipe right to hide buttons
                        hide_actions()
                    return True  # Consume event for swiping
                else:
                    return self.scroll.on_touch_move(touch)  # Allow vertical scrolling

        swipe_container.bind(on_touch_move=on_touch_move)

        # Add layouts to the swipe container (ORDER CHANGED)
        swipe_container.add_widget(ticket_layout_outer)  # Main ticket layout (first)
        swipe_container.add_widget(action_layout)  # Hidden buttons (second)

        # Add the swipeable ticket to the scrollable container
        self.ticket_container.add_widget(swipe_container)

        # Update the ticket_container height dynamically
        self.ticket_container.height = sum(child.height for child in self.ticket_container.children) + 20

        # Ensure scrolling works by setting scroll to the bottom
        self.scroll.scroll_y = 0
        # Start the timer update
        Clock.schedule_interval(lambda dt: self.update_timer_display(ticket_id, timer_label), 1)

    def clock_out(self, instance):
        """Handle clock-out and reset the screen."""
        if GlobalContext.get_current_user():
            self.log_clock_out()

        # Clear session details
        self.cook_name = ""
        self.entered_pin = ""  # Clear the entered PIN
        self.cook_label.text = "[Not Logged In]"
        self.ticket_count = 0
        self.timers = {}

        # Ensure the login screen's PIN is cleared
        login_screen = self.manager.get_screen("kitchen_login")
        if hasattr(login_screen, "entered_pin"):
            login_screen.entered_pin = ""  # Clear the PIN on the login screen
            login_screen.clear_pin(None)  # Call the clear_pin method to update the display

        # Reset the global user context
        GlobalContext.set_current_user(None)

        # Navigate back to the login screen
        self.manager.transition.direction = "right"
        self.manager.current = "kitchen_login"

    def log_clock_out(self):
        """Logs the clock-out for the currently logged-in user."""
        current_user = GlobalContext.get_current_user()
        if not current_user:
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Find the latest clock-in for this user
        cursor.execute('''
            SELECT id FROM clock_logs
            WHERE employee_name = ? AND clock_out_time IS NULL
            ORDER BY clock_in_time DESC LIMIT 1
        ''', (current_user["name"],))
        result = cursor.fetchone()

        if result:
            log_id = result[0]
            clock_out_time = datetime.now(timezone.utc).isoformat()

            # Update the clock-out
            cursor.execute('''
                UPDATE clock_logs
                SET clock_out_time = ?, status = ?
                WHERE id = ?
            ''', (clock_out_time, "Clocked Out", log_id))
            conn.commit()

            GlobalContext.set_current_user(None)  # Clear the logged-in user

        conn.close()

    def schedule_auto_logout(self):
        """Schedules automatic logout at 10:45 PM."""
        now = datetime.now()
        target_time = now.replace(hour=22, minute=45, second=0, microsecond=0)  # 10:45 PM

        # If it's already past 10:45 PM, schedule for tomorrow
        if now > target_time:
            target_time = target_time.replace(day=now.day + 1)

        delay_seconds = (target_time - now).total_seconds()
        print(f"Auto logout scheduled in {delay_seconds / 60:.2f} minutes.")
        Clock.schedule_once(lambda dt: self.auto_logout_user(), delay_seconds)

    def auto_logout_user(self):
        """Automatically logs out the current user at 10:45 PM."""
        print("Auto logout triggered for active user.")

        # ✅ Get the currently logged-in user
        user_data = GlobalContext.get_current_user()

        if not user_data:
            print("No active user found. No logout needed.")
            return

        cook_name = user_data.get("name")
        if not cook_name:
            print("Current user has no name stored. Logout skipped.")
            return

        print(f"Logging out {cook_name} at 10:45 PM...")

        # ✅ Set local time to 11:00 PM
        local_tz = pytz.timezone("America/New_York")  # Change this to your timezone!
        local_time = datetime.now(local_tz).replace(hour=22, minute=45, second=0, microsecond=0)

        # ✅ Convert to UTC
        clock_out_time_utc = local_time.astimezone(pytz.utc).isoformat()

        # ✅ Update `clock_logs` to set `clock_out_time`
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE clock_logs
            SET clock_out_time = ?
            WHERE employee_name = ? AND clock_out_time IS NULL
        ''', (clock_out_time_utc, cook_name))

        conn.commit()
        conn.close()

        # ✅ Clear session data and redirect to login
        GlobalContext.set_current_user(None)
        print(f"{cook_name} has been logged out.")

        # ✅ Reset UI elements
        self.cook_name = ""
        self.entered_pin = ""
        self.cook_label.text = "[color=#E4E5E9][b]Cook:[/b][/color]\n[color=#818590][Not Logged In][/color]"

        # ✅ Redirect to login screen
        self.manager.current = "kitchen_login"

    def get_elapsed_time(self, ticket_id):
        """Returns the elapsed time in seconds since the ticket started."""
        if ticket_id not in self.timers:
            return 0

        ticket = self.timers[ticket_id]
        if ticket["running"]:
            return int(time.time() - ticket["start_time"])
        return 0

    def update_timer_display(self, ticket_id, timer_label):
        """Updates the ticket's timer label using elapsed time from the start timestamp."""
        if ticket_id not in self.timers or not self.timers[ticket_id].get("running"):
            return

        elapsed_time = self.get_elapsed_time(ticket_id)
        minutes, seconds = divmod(elapsed_time, 60)
        timer_label.text = f"[b][u]Time:[/u][/b]\n{minutes}:{seconds:02d}"

    def log_ticket(self, cook_pin, total_time):
        """Logs completed tickets to the database."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        utc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # 🔹 Fix: Ensure cook_pin is correctly extracted
        if isinstance(cook_pin, tuple):  # Check if it's a tuple
            cook_pin = cook_pin[0]  # Extract the first value

        cursor.execute(
            "INSERT INTO tickets (cook_pin, date, time_taken) VALUES (?, ?, ?)",
            (int(cook_pin), utc_time, total_time)
        )
        conn.commit()
        conn.close()

    def on_pause(self):
        """Handles app pause by storing active ticket timestamps."""
        paused_tickets = {
            tid: {"start_time": ticket["start_time"]}
            for tid, ticket in self.timers.items()
            if ticket.get("running") and ticket.get("start_time")
        }

        with open("paused_tickets.json", "w") as file:
            import json
            json.dump(paused_tickets, file)
        return True

    def on_resume(self):
        """Restores active tickets and ensures the ScrollView remains at the bottom."""
        if os.path.exists("paused_tickets.json"):
            with open("paused_tickets.json", "r") as file:
                paused_tickets = json.load(file)

            for ticket_id, data in paused_tickets.items():
                ticket_id = int(ticket_id)
                if ticket_id in self.timers:
                    self.timers[ticket_id]["start_time"] = data["start_time"]
                else:
                    self.timers[ticket_id] = {"start_time": data["start_time"], "running": True}

                if f"timer_{ticket_id}" not in self.timers:
                    self.timers[f"timer_{ticket_id}"] = Clock.schedule_interval(
                        lambda dt, tid=ticket_id: self.update_timer_display(tid), 1
                    )

            os.remove("paused_tickets.json")

        # 🔹 Apply forced layout update, then scroll to bottom
        Clock.schedule_once(self.force_scroll_update, 0.1)

    def force_scroll_update(self, dt):
        """Forces the ScrollView to scroll to the bottom after a UI refresh."""
        self.ticket_container.height = sum(child.height for child in self.ticket_container.children) + 20
        self.ticket_container.do_layout()  # 🔹 Refresh UI manually

        # 🔹 Temporarily disable scrolling, move to bottom, then re-enable it
        self.scroll.do_scroll_y = False  # Disable scrolling to prevent override
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'do_scroll_y', True), 0.2)

    def clear_tickets(self):
        """Clear all ticket UI elements and reset stored tickets."""
        for child in list(self.ticket_container.children):
            self.ticket_container.remove_widget(child)
        self.ticket_container.height = 10  # Reset UI height
        KitchenPanel.ticket_storage.clear()
        self.displayed_ticket_ids.clear()
