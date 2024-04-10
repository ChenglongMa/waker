import sys
import tkinter as tk
from pynput import mouse

from waker.assets import get_asset


class InvisibleDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        self.overrideredirect(True)

        self.title('Notepad')
        self.iconbitmap(sys.executable)
        # Set window transparency
        self.attributes('-alpha', 0)

        # Keep the window on top
        self.attributes('-topmost', True)
        # self.attributes('-fullscreen', True)
        self.state('zoomed')
        self.deiconify()

        # Create a multi-line text widget
        self.text_widget = tk.Text(self, wrap=tk.WORD)
        self.text_widget.pack(expand=True, fill=tk.BOTH)

        # Start listening for global mouse events
        self.listener = mouse.Listener(on_click=self.hide_window, on_move=self.hide_window, on_scroll=self.hide_window)
        self.listener.start()

        # Set focus on the text widget
        self.text_widget.focus_set()
        self.bind('<FocusOut>', self.hide_window)
        self.bind('<Escape>', self.hide_window)

    def hide_window(self, *args):
        self.destroy()

    def destroy(self):
        self.listener.stop()
        super().destroy()
