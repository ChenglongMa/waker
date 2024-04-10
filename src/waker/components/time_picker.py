import tkinter as tk
from tkinter import ttk


class TimePicker(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        self.on_hour_select_arg = kwargs.pop("on_hour_select", None)
        self.on_minute_select_arg = kwargs.pop("on_minute_select", None)
        self.on_time_select_arg = kwargs.pop("on_time_select", None)
        self.default_hour = kwargs.pop("default_hour", "00")
        self.default_minute = kwargs.pop("default_minute", "00")
        super().__init__(parent, *args, **kwargs)

        var_type = tk.StringVar
        self.hour_var = var_type()
        self.hour_cb = ttk.Combobox(self, width=2, textvariable=self.hour_var, state="readonly")
        self.hour_cb['values'] = [f'{i:02d}' for i in range(24)]
        self.hour_cb.current(0)
        self.hour_cb.bind("<<ComboboxSelected>>", self.on_hour_select)
        self.hour_cb.pack(side=tk.LEFT, padx=(0, 2))
        self.hour_var.set(self.default_hour)

        self.minute_var = var_type()
        self.minute_cb = ttk.Combobox(self, width=2, textvariable=self.minute_var, state="readonly")
        self.minute_cb['values'] = [f'{i:02d}' for i in range(0, 60, 5)]
        self.minute_cb.current(0)
        self.minute_cb.bind("<<ComboboxSelected>>", self.on_minute_select)
        self.minute_cb.pack(side=tk.LEFT)
        self.minute_var.set(self.default_minute)

    def set_enabled(self, enabled):
        self.hour_cb['state'] = "readonly" if enabled else tk.DISABLED
        self.minute_cb['state'] = "readonly" if enabled else tk.DISABLED

    def on_hour_select(self, event):
        print(f"Selected hour: {self.hour_var.get()}")
        if self.on_hour_select_arg:
            self.on_hour_select_arg(event)
        self.on_time_select(event)

    def on_minute_select(self, event):
        print(f"Selected minute: {self.minute_var.get()}")
        if self.on_minute_select_arg:
            self.on_minute_select_arg(event)
        self.on_time_select(event)

    def on_time_select(self, event):
        print(f"Selected time: {self.hour_var.get()}:{self.minute_var.get()}")
        if self.on_time_select_arg:
            self.on_time_select_arg(int(self.hour_var.get()), int(self.minute_var.get()))
