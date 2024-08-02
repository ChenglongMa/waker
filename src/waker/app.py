import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import simpledialog, filedialog

import pystray
import sv_ttk
from PIL import UnidentifiedImageError

from waker.package import __app_name__, __version__, __repo_name__
from waker.components.time_picker import TimePicker
from core.model import Waker, WakerState, WakerObserver, CustomJSONEncoder
from core.utils import *


class App(WakerObserver):
    def __init__(self, config: dict):
        # Get the configuration
        self.app_path = os.path.abspath(sys.argv[0])
        self.save_to_config = True
        self.config = config
        self.theme = self.config.get("Theme", "light")
        self.font_family = self.config.get("FontFamily", DEFAULT_UI_FONT)
        self.language = self.config.get("Language", DEFAULT_LANGUAGE)
        if self.language not in AVAILABLE_LANGUAGES:
            self.language = DEFAULT_LANGUAGE

        self.default_icons = {
            WakerState.ACTIVE: get_asset("active.png"),
            WakerState.SCHEDULED: get_asset("scheduled.png"),
            WakerState.INACTIVE: get_asset("inactive.png")
        }

        self.icons = {**self.default_icons, **self.config.get("IconFiles", {})}
        self.waker = Waker(self, self.config)
        self.waker.add_observer(self)

        # Initialize the root window
        self.root = tk.Tk()
        if self.config.get("MinimizeOnStartup", True):
            self.root.withdraw()
        if "dark" in self.theme.lower():
            sv_ttk.use_dark_theme()
        else:
            sv_ttk.use_light_theme()
        change_font(self.font_family)
        self.root.title(f"{__app_name__} v{__version__}")
        self.window_width = 400
        self.window_height = 500
        self.control_padding = 10
        self.layout_padding = 12

        self.language_var = tk.StringVar(value=self.language)
        self.language_var.trace("w", self.change_language)
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.position_top = int(self.screen_height / 2 - self.window_height / 2)
        self.position_right = int(self.screen_width / 2 - self.window_width / 2)
        self.root.geometry(f"{self.window_width}x{self.window_height}+{self.position_right}+{self.position_top}")
        self.root.iconbitmap(get_asset("icon.ico"))
        self.root.minsize(self.window_width, self.window_height)
        self.root.maxsize(self.window_width + 50, self.window_height + 50)

        # Create the UI components
        self.create_menu_bar()
        self.create_main_switch_groupbox()
        self.create_wake_up_interval_groupbox()
        self.create_schedule_groupbox()
        self.create_bottom_bar()

        # Create the tray app
        self.tray_app: pystray.Icon = self.create_tray_app()
        self.tray_thread = threading.Thread(target=self.tray_app.run)

        self.root.pack_propagate(True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_minimizing)

    def get_label(self, key, default_value=None):
        return get_label(key, self.language, default_value)

    def create_tray_app(self) -> pystray.Icon:
        icon_file = self.icons.get(self.waker.state, WakerState.ACTIVE)
        return pystray.Icon(
            name=__app_name__,
            icon=Image.open(icon_file),
            title=f"{__app_name__} v{__version__}",
            menu=self.create_tray_menu()
        )

    def on_window_minimizing(self, force_minimize=False):
        print("Window is now minimized")
        if force_minimize or self.minimize_on_close.get():
            self.save_config()
            self.root.after(0, self.root.withdraw)
        else:
            self.on_window_closing(self.tray_app)

    def on_window_restoring(self, icon: pystray.Icon = None, item=None):
        self.root.after(0, self.root.deiconify)

    def update_title(self, title):
        self.root.title(f"{title} v{__version__}")
        state_title = f"{title} - {self.waker.state}"
        self.tray_app.title = state_title
        self.main_switch.config(text=state_title)

    def update(self, state: WakerState):
        self.refresh_tray_icon()
        self.update_title(__app_name__)
        self.refresh_icon()

    def set_enabled(self, item):
        current_state = self.main_switch_var.get()
        self.main_switch_var.set(not current_state)

    def set_launch_at_login(self, *args):
        set_autorun(__app_name__, self.app_path, self.launch_at_login.get())
        self.config["LaunchAtLogin"] = self.launch_at_login.get()

    def create_tray_menu(self):
        return pystray.Menu(
            pystray.MenuItem(self.get_label("show_main_window"), self.on_window_restoring, default=True),
            pystray.MenuItem(self.get_label("enabled"), self.set_enabled, checked=lambda item: self.config.get("Enabled", True)),
            pystray.MenuItem(self.get_label("help"), self.show_about),
            pystray.MenuItem(self.get_label("exit"), self.on_window_closing)
        )

    def reset_app_name_icon(self):
        self.update_title(__app_name__)
        self.icons = self.default_icons
        self.refresh_icon()
        self.refresh_tray_icon()
        del self.config["IconFiles"]

    def set_custom_name(self):
        new_title = simpledialog.askstring(self.get_label("set_custom_app_name"), self.get_label("set_custom_app_name_prompt"))
        if new_title:
            self.update_title(new_title)

    def set_custom_icon(self, icon_type: WakerState):
        icon_file = filedialog.askopenfilename(
            title=self.get_label("set_custom_app_icon"),
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.ico;*.bmp;*.tif;*.webp"),
                ("All files", "*.*")
            ]
        )
        if icon_file and os.path.exists(icon_file):
            try:
                self.refresh_icon(icon_file)
                self.refresh_tray_icon(icon_file)
                self.icons[icon_type] = icon_file
                self.config["IconFiles"] = self.icons
            except UnidentifiedImageError as e:
                messagebox.showerror(self.get_label("error"), self.get_label("invalid_image_format"))

    def create_menu_bar(self):
        self.menu_bar = tk.Menu(self.root)
        self.setting_menu = tk.Menu(self.menu_bar, tearoff=0)

        self.setting_menu.add_command(label=self.get_label("set_custom_app_name"), command=self.set_custom_name)
        self.icon_menu = tk.Menu(self.setting_menu, tearoff=0)
        # self.icon_menu.add_command(label=self.get_label("set_default_icon"), command=lambda: self.set_custom_icon("default"))
        self.icon_menu.add_command(label=self.get_label("set_custom_active_icon"), command=lambda: self.set_custom_icon(WakerState.ACTIVE))
        self.icon_menu.add_command(label=self.get_label("set_custom_scheduled_icon"), command=lambda: self.set_custom_icon(WakerState.SCHEDULED))
        self.icon_menu.add_command(label=self.get_label("set_custom_inactive_icon"), command=lambda: self.set_custom_icon(WakerState.INACTIVE))
        self.setting_menu.add_cascade(label=self.get_label("set_custom_app_icon"), menu=self.icon_menu)
        self.setting_menu.add_command(label=self.get_label("reset_app_name_icon"), command=self.reset_app_name_icon)
        self.setting_menu.add_separator()

        self.setting_menu.add_command(label=self.get_label("edit_corpus"), command=edit_corpus)
        self.setting_menu.add_separator()
        self.lang_menu = tk.Menu(self.setting_menu, tearoff=0)
        self.lang_menu.add_radiobutton(label="English", variable=self.language_var, value="en_US")
        self.lang_menu.add_radiobutton(label="简体中文", variable=self.language_var, value="zh_CN")
        self.setting_menu.add_cascade(label=self.get_label("set_language"), menu=self.lang_menu)

        self.setting_menu.add_command(label=self.get_label("set_theme"), command=lambda: self.root.after(0, self.toggle_theme))

        self.minimize_on_startup = tk.BooleanVar(value=self.config.get("MinimizeOnStartup", True))
        self.minimize_on_startup.trace("w", self.on_startup_minimizing_switch_changed)
        self.setting_menu.add_checkbutton(label=self.get_label("minimize_to_tray_on_startup"), variable=self.minimize_on_startup)

        self.minimize_on_close = tk.BooleanVar(value=self.config.get("MinimizeOnClose", True))
        self.minimize_on_close.trace("w", self.on_close_minimizing_switch_changed)
        self.setting_menu.add_checkbutton(label=self.get_label("minimize_to_tray_on_close"), variable=self.minimize_on_close)

        self.launch_at_login = tk.BooleanVar(value=self.config.get("LaunchAtLogin", False))
        self.launch_at_login.trace("w", self.set_launch_at_login)
        self.setting_menu.add_checkbutton(label=self.get_label("set_launch_at_login"), variable=self.launch_at_login)

        self.menu_bar.add_cascade(label=self.get_label("settings"), menu=self.setting_menu)
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label=self.get_label("about"), command=self.show_about)
        self.help_menu.add_command(label=self.get_label("check_update"), command=lambda: check_for_updates(self.no_new_version_fn))
        self.menu_bar.add_cascade(label=self.get_label("help"), menu=self.help_menu)
        self.root.config(menu=self.menu_bar)

    def on_startup_minimizing_switch_changed(self, *args):
        self.config["MinimizeOnStartup"] = self.minimize_on_startup.get()

    def on_close_minimizing_switch_changed(self, *args):
        self.config["MinimizeOnClose"] = self.minimize_on_close.get()

    def on_main_switch_changed(self, *args):
        self.config["Enabled"] = self.main_switch_var.get()
        self.waker.sync_state()

    def refresh_icon(self, icon_file=None):
        icon_file = icon_file or self.icons.get(self.waker.state, WakerState.ACTIVE)
        icon_image = resized_icon(icon_file, 32)
        self.main_switch.config(image=icon_image)
        self.main_switch.image = icon_image

    def refresh_tray_icon(self, icon_file=None):
        icon_file = icon_file or self.icons.get(self.waker.state, WakerState.ACTIVE)
        print("Refreshing tray icon", self.waker.state, icon_file)
        self.tray_app.icon = Image.open(icon_file)

    def create_main_switch_groupbox(self):
        self.main_switch_groupbox = ttk.Frame(self.root, style='Card.TFrame')
        self.main_switch_var = tk.BooleanVar(value=self.config.get("Enabled", True))
        self.main_switch_var.trace("w", self.on_main_switch_changed)
        self.main_switch = ttk.Checkbutton(self.main_switch_groupbox, text=f"{__app_name__} - {self.waker.state}", variable=self.main_switch_var,
                                           style='Switch.TCheckbutton', compound=tk.RIGHT)
        self.refresh_icon()
        self.main_switch.pack(pady=self.control_padding)
        self.main_switch_groupbox.bind("<Button-1>", lambda event: self.main_switch_var.set(not self.main_switch_var.get()))
        self.main_switch_groupbox.pack(side=tk.TOP, fill=tk.BOTH, padx=self.layout_padding, pady=self.layout_padding)

    def on_wake_up_interval_changed(self, *args):
        interval = to_decimal(self.wake_up_interval_var.get(), 1, self.config.get("WakeUpInterval", 4))
        self.wake_up_interval_var.set(interval)
        self.config["WakeUpInterval"] = interval

    def create_wake_up_interval_groupbox(self):
        self.wake_up_interval_groupbox = ttk.Frame(self.root, style='Card.TFrame')
        self.wake_up_interval_input_groupbox = ttk.Frame(self.wake_up_interval_groupbox)
        self.wake_up_interval_var = tk.DoubleVar(value=self.config.get("WakeUpInterval", 4))
        self.wake_up_interval_var.trace("w", self.on_wake_up_interval_changed)
        self.wake_up_interval_label = ttk.Label(self.wake_up_interval_input_groupbox, text=self.get_label("wake_up_interval"))
        self.wake_up_interval_label.pack(side=tk.LEFT, padx=self.control_padding // 5)

        self.time_unit_label = ttk.Label(self.wake_up_interval_input_groupbox, text=self.get_label("mins"))
        self.time_unit_label.pack(side=tk.RIGHT, padx=self.control_padding // 5)

        vcmd = (self.root.register(is_number), '%P')
        self.wake_up_interval_entry = ttk.Spinbox(self.wake_up_interval_input_groupbox, textvariable=self.wake_up_interval_var, width=4, from_=1,
                                                  to=10, validate="key", validatecommand=vcmd)
        self.wake_up_interval_entry.pack(side=tk.RIGHT, padx=self.control_padding // 5)

        self.wake_up_interval_input_groupbox.pack(side=tk.TOP, fill=tk.X, padx=self.control_padding, pady=self.control_padding)
        self.wake_up_interval_scale = ttk.Scale(self.wake_up_interval_groupbox, from_=1, to=10, orient=tk.HORIZONTAL,
                                                variable=self.wake_up_interval_var)
        self.wake_up_interval_scale.pack(side=tk.TOP, padx=self.control_padding, pady=self.control_padding, fill=tk.X)

        self.wake_up_interval_groupbox.pack(side=tk.TOP, fill=tk.X, padx=self.layout_padding, pady=self.layout_padding)

    def on_schedule_switch_changed(self, *args):
        self.config["Scheduled"] = self.schedule_var.get()
        self.waker.sync_state()
        if self.schedule_var.get():
            self.schedule_groupbox.pack(side=tk.TOP, fill=tk.BOTH, padx=self.layout_padding, pady=self.layout_padding)
        else:
            self.schedule_groupbox.pack_forget()

    def on_everyday_switch_changed(self, *args):
        print("Everyday switch changed", args)
        everyday = self.everyday_var.get()
        self.config["Everyday"] = everyday
        self.save_to_config = False
        for day in DEFAULT_WEEKDAY_STATES.keys():
            value = True if everyday else self.config.get("ScheduledDays", DEFAULT_WEEKDAY_STATES)[day]
            self.weekday_vars[day].set(value)
        self.save_to_config = True
        self.waker.sync_state()

    def on_weekday_switch_changed(self, name, index, mode):
        day = name.split("_")[-1]
        print("Weekday switch changed", day, index, mode)
        if self.save_to_config:
            self.config["ScheduledDays"] = self.config.get("ScheduledDays", DEFAULT_WEEKDAY_STATES)
            self.config["ScheduledDays"][day] = self.weekday_vars[day].get()
            self.waker.sync_state()

    def create_week_toggle_buttons(self, parent):
        self.week_frame = ttk.Frame(parent)
        self.weekday_vars = {}
        self.weekday_buttons = []
        for i, key in enumerate(DEFAULT_WEEKDAY_STATES.keys()):
            enabled = self.config.get(f"ScheduledDays", DEFAULT_WEEKDAY_STATES)[key] or self.config.get("Everyday", False)
            self.weekday_vars[key] = tk.BooleanVar(value=enabled, name=f"weekday_{key}")
            self.weekday_vars[key].trace("w", self.on_weekday_switch_changed)
            label = self.get_label(f"weekdays")[i]
            weekday_button = ttk.Checkbutton(self.week_frame, text=label, variable=self.weekday_vars[key], style='Toggle.TButton')
            weekday_button.pack(side=tk.LEFT, padx=self.control_padding // 10, pady=self.control_padding)
            self.weekday_buttons.append(weekday_button)
        self.week_frame.pack(fill=tk.Y, padx=self.layout_padding // 3, pady=self.layout_padding // 3)

    def on_start_time_changed(self, new_hour, new_minute):
        print("Start time changed", new_hour, new_minute)
        self.config["StartTime"] = f"{new_hour:02d}:{new_minute:02d}"
        self.waker.sync_state()

    def on_end_time_changed(self, new_hour, new_minute):
        print("End time changed", new_hour, new_minute)
        self.config["EndTime"] = f"{new_hour:02d}:{new_minute:02d}"
        self.waker.sync_state()

    def on_all_day_switch_changed(self, *args):
        print("All day switch changed", args)
        all_day = self.all_day_var.get()
        self.config["AllDay"] = all_day
        if all_day:
            self.start_time_picker.set_enabled(False)
            self.end_time_picker.set_enabled(False)
            self.start_time_picker.hour_var.set("00")
            self.start_time_picker.minute_var.set("00")
            self.end_time_picker.hour_var.set("23")
            self.end_time_picker.minute_var.set("59")
        else:
            self.start_time_picker.set_enabled(True)
            self.end_time_picker.set_enabled(True)
            start_hour, start_minute, end_hour, end_minute = self.get_default_times()
            self.start_time_picker.hour_var.set(start_hour)
            self.start_time_picker.minute_var.set(start_minute)
            self.end_time_picker.hour_var.set(end_hour)
            self.end_time_picker.minute_var.set(end_minute)
        self.waker.sync_state()

    def get_default_times(self):
        start_time = self.config.get("StartTime", "09:00")
        end_time = self.config.get("EndTime", "18:00")
        start_hour, start_minute = start_time.split(":")
        end_hour, end_minute = end_time.split(":")
        return start_hour, start_minute, end_hour, end_minute

    def create_time_picker(self, parent):
        self.time_frame = ttk.Frame(parent)
        time_picker_margin = 2
        start_hour, start_minute, end_hour, end_minute = self.get_default_times()
        self.start_time_picker = TimePicker(self.time_frame, on_time_select=self.on_start_time_changed,
                                            default_hour=start_hour,
                                            default_minute=start_minute)
        self.start_time_picker.pack(side=tk.LEFT, padx=(0, time_picker_margin))
        self.end_time_picker = TimePicker(self.time_frame, on_time_select=self.on_end_time_changed,
                                          default_hour=end_hour,
                                          default_minute=end_minute)
        self.end_time_picker.pack(side=tk.LEFT, padx=time_picker_margin)

        self.all_day_var = tk.BooleanVar(value=self.config.get("AllDay", False))
        self.all_day_var.trace("w", self.on_all_day_switch_changed)
        self.all_day_switch = ttk.Checkbutton(self.time_frame, text=self.get_label("all_day"),
                                              variable=self.all_day_var)
        self.all_day_switch.pack(side=tk.RIGHT, padx=(time_picker_margin, 0))

        self.time_frame.pack(fill=tk.Y, padx=self.layout_padding // 3, pady=(0, self.layout_padding))

    def create_schedule_groupbox(self):
        self.schedule_switch_groupbox = ttk.Frame(self.root, style='Card.TFrame')
        self.schedule_var = tk.BooleanVar(value=self.config.get("Scheduled", False))
        self.schedule_var.trace("w", self.on_schedule_switch_changed)
        self.schedule_switch = ttk.Checkbutton(self.schedule_switch_groupbox, text=self.get_label("schedule"), variable=self.schedule_var,
                                               style='Switch.TCheckbutton')
        self.schedule_switch.pack(padx=self.control_padding, pady=self.control_padding)
        self.schedule_switch_groupbox.bind("<Button-1>", lambda event: self.schedule_var.set(not self.schedule_var.get()))
        self.schedule_switch_groupbox.pack(side=tk.TOP, fill=tk.BOTH, padx=self.layout_padding, pady=(self.layout_padding, self.control_padding // 2))

        self.schedule_groupbox = ttk.Frame(self.root, style='Card.TFrame')

        self.everyday_var = tk.BooleanVar(value=self.config.get("Everyday", False))
        self.everyday_var.trace("w", self.on_everyday_switch_changed)
        self.everyday_switch = ttk.Checkbutton(self.schedule_groupbox, text=self.get_label("everyday"), variable=self.everyday_var,
                                               style='Switch.TCheckbutton')
        self.everyday_switch.pack(padx=self.control_padding, pady=self.control_padding)

        self.create_week_toggle_buttons(self.schedule_groupbox)
        self.create_time_picker(self.schedule_groupbox)
        if self.schedule_var.get():
            self.schedule_groupbox.pack(side=tk.TOP, fill=tk.BOTH, padx=self.layout_padding, pady=self.layout_padding)

    def create_bottom_bar(self):
        accent_color = THEME_COLOR[self.theme]["accent"]
        bottom_frame = ttk.Frame(self.root)
        self.repo_label = tk.Label(bottom_frame, text=f"GitHub", fg=accent_color, cursor="hand2")
        self.repo_label.pack(side=tk.LEFT, padx=self.control_padding)
        self.repo_label.bind("<Button-1>", lambda event: open_repo_page())

        separator = ttk.Separator(bottom_frame, orient=tk.VERTICAL)
        separator.pack(fill=tk.Y, side=tk.LEFT, padx=self.control_padding)

        self.check_updates_label = tk.Label(bottom_frame, text=self.get_label("check_update"), fg=accent_color, cursor="hand2")
        self.check_updates_label.pack(side=tk.LEFT, padx=self.control_padding)
        self.check_updates_label.bind("<Button-1>", lambda event: check_for_updates(self.no_new_version_fn))

        separator = ttk.Separator(bottom_frame, orient=tk.VERTICAL)
        separator.pack(fill=tk.Y, side=tk.LEFT, padx=self.control_padding)

        self.quit_label = tk.Label(bottom_frame, text=self.get_label("exit"), fg=accent_color, cursor="hand2")
        self.quit_label.pack(side=tk.LEFT, padx=self.control_padding)
        self.quit_label.bind("<Button-1>", self.on_window_closing)

        bottom_frame.pack(side=tk.BOTTOM, anchor=tk.CENTER, pady=self.layout_padding)
        separator = ttk.Separator(self.root, orient=tk.HORIZONTAL)
        separator.pack(side=tk.BOTTOM, fill=tk.X)

    def no_new_version_fn(self):
        messagebox.showinfo(self.get_label("check_update"), self.get_label("no_new_version"))

    def show_about(self, icon=None, item=None):
        pady = self.layout_padding // 2
        self.about_window = tk.Toplevel(self.root)
        self.about_window.title(self.get_label("about"))
        self.about_window.iconbitmap(get_asset("icon.ico"))
        self.about_window.geometry(f"+{self.position_right}+{self.position_top}")
        self.about_window.protocol("WM_DELETE_WINDOW", self.on_about_window_closing)
        self.app_name_label = tk.Label(self.about_window, text=f"{__app_name__} v{__version__}")
        self.app_name_label.pack(padx=self.control_padding, pady=pady)
        accent_color = THEME_COLOR[self.theme]["accent"]

        self.author_label = tk.Label(self.about_window, text=f"{self.get_label('author')}: Chenglong Ma", fg=accent_color, cursor="hand2")
        self.author_label.pack(padx=self.control_padding, pady=pady)
        self.author_label.bind("<Button-1>", lambda event: open_my_homepage())

        self.homepage_label = tk.Label(self.about_window, text=f"GitHub：{__repo_name__}", fg=accent_color, cursor="hand2")
        self.homepage_label.pack(padx=self.control_padding, pady=pady)
        self.homepage_label.bind("<Button-1>", lambda event: open_repo_page())

        self.copyright_label = tk.Label(self.about_window, text="Copyright © 2024 Chenglong Ma. All rights reserved.")
        self.copyright_label.pack(padx=self.control_padding, pady=pady)

    def on_about_window_closing(self):
        self.about_window.destroy()

    def toggle_theme(self):
        sv_ttk.toggle_theme()
        self.theme = sv_ttk.get_theme()
        self.config["Theme"] = self.theme
        accent_color = THEME_COLOR[self.theme]["accent"]
        self.check_updates_label.config(foreground=accent_color)
        self.repo_label.config(foreground=accent_color)
        self.quit_label.config(foreground=accent_color)

    def run(self):
        self.waker.start(self.config)
        self.tray_thread.start()
        self.root.mainloop()
        self.tray_thread.join()

    def save_config(self):
        write_json(CONFIG_FILENAME, self.config, encoder_cls=CustomJSONEncoder)
        print("Configuration file updated")

    def on_window_closing(self, *args):
        self.waker.stop()
        self.tray_app.stop()
        self.save_config()
        self.root.after(0, self.root.destroy)

    def change_language(self, *args):
        # Update the language in the configuration
        language = self.language_var.get()
        self.language = language
        self.config["Language"] = language
        self.save_config()

        if messagebox.askyesno(self.get_label("restart_required"), self.get_label("restart_required_desc")):
            restart()
