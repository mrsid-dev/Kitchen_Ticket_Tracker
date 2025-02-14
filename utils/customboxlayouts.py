from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.stencilview import StencilView
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.image import Image

class ColoredBoxLayout(BoxLayout):
    def __init__(self, color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self.color = color
        with self.canvas.before:
            # Set the initial color and draw the rectangle
            self.bg_color = Color(*self.color)
            self.rect = Rectangle(size=self.size, pos=self.pos)

        # Bind size and position changes to update the rectangle
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos


class RoundedBoxLayout(StencilView):
    def __init__(self, radius=30, color=(1, 1, 1, 1), dynamic_height=False, **kwargs):
        super().__init__()

        self.radius = radius
        self.color = color
        self.dynamic_height = dynamic_height  # Enable dynamic height if needed

        # Extract BoxLayout-specific properties
        boxlayout_kwargs = {key: kwargs.pop(key) for key in ['orientation', 'padding', 'spacing'] if key in kwargs}

        # Create the internal BoxLayout
        self.layout = BoxLayout(**boxlayout_kwargs)
        super().add_widget(self.layout)

        # Draw the shadow and background
        with self.canvas.before:
            # Main background
            Color(*self.color)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[self.radius])

        # Bind size and position changes to update the rectangles
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, *args):
        """Update the size and position of the shadow and main background."""
        # Main background
        self.rect.size = self.size
        self.rect.pos = self.pos

        # Ensure the internal layout matches the size and position
        self.layout.size = self.size
        self.layout.pos = self.pos

    def add_widget(self, widget, **kwargs):
        """Forward widgets to the internal BoxLayout."""
        self.layout.add_widget(widget, **kwargs)
        if self.dynamic_height:
            self._update_height()

    def remove_widget(self, widget):
        """Forward widget removal to the internal BoxLayout."""
        self.layout.remove_widget(widget)
        if self.dynamic_height:
            self._update_height()

    def _update_height(self):
        """Update the height of the RoundedBoxLayout based on the internal layout's content."""
        if self.dynamic_height and self.layout.size_hint_y is None:
            self.height = (
                sum(child.height + self.layout.spacing for child in self.layout.children)
                + self.layout.padding[1] * 2
            )

class RoundedButton(Button):
    def __init__(self, radius=30, background_color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)

        self.radius = radius
        self.is_active = False  # Track if this button is the active one
        self.default_bg_color = background_color
        self.default_text_color = kwargs.get("color", (1, 1, 1, 1))  # Default text color
        self.active_bg_color = (0.714, 0.569, 0.129, 1)  # Gold background when active
        self.active_text_color = (1, 1, 1, 1)  # White text when active

        # Compute disabled colors
        self.disabled_bg_color = self._get_darker_duller_color(background_color)
        self.disabled_text_color = (0.7, 0.7, 0.7, 1)  # Gray text for disabled state

        self.color = self.default_text_color
        self.font_name = kwargs.get("font_name", "Roboto")
        self.font_size = kwargs.get("font_size", 20)

        # Remove the default button background image
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)  # Fully transparent

        # Draw the rounded rectangle background
        with self.canvas.before:
            self.color_instruction = Color(*self.default_bg_color)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[self.radius])

        # Bind size and position changes to update the rectangle
        self.bind(size=self._update_rect, pos=self._update_rect, text=self._update_text,
                  state=self._update_state, disabled=self._update_state)

    def set_active(self, is_active):
        """Set the button as active or inactive."""
        self.is_active = is_active
        if is_active:
            self.color_instruction.rgba = self.active_bg_color  # Make background gold
            self.color = self.active_text_color  # Make text white
        else:
            self.color_instruction.rgba = self.default_bg_color  # Reset background
            self.color = self.default_text_color  # Reset text color

    def _update_rect(self, *args):
        """Update the size and position of the rounded rectangle."""
        self.rect.size = self.size
        self.rect.pos = self.pos

    def _update_text(self, *args):
        """Ensure text properties stay updated."""
        self.font_name = self.font_name
        self.font_size = self.font_size

    def _update_state(self, *args):
        """Ensure the button keeps its state when pressed or disabled."""
        if self.disabled:
            self.color_instruction.rgba = self.disabled_bg_color  # Use calculated duller background
            self.color = self.disabled_text_color  # Gray out text
        elif self.is_active:
            self.color_instruction.rgba = self.active_bg_color  # Keep active button gold
            self.color = self.active_text_color  # Keep active text white
        elif self.state == "down":
            self.color_instruction.rgba = (
                self.default_bg_color[0] * 0.9,
                self.default_bg_color[1] * 0.9,
                self.default_bg_color[2] * 0.9,
                self.default_bg_color[3]
            )
        else:
            self.color_instruction.rgba = self.default_bg_color  # Reset background when not active
            self.color = self.default_text_color  # Reset text color

    def _get_darker_duller_color(self, color):
        """Make the color darker and duller for the disabled state."""
        luminance = sum(color[:3]) / 3
        dull_factor = 0.25
        dark_factor = 0.75
        return (
            color[0] * dark_factor + (luminance - color[0]) * dull_factor,
            color[1] * dark_factor + (luminance - color[1]) * dull_factor,
            color[2] * dark_factor + (luminance - color[2]) * dull_factor,
            color[3],
        )
