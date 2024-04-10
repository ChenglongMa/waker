import json
import os
import random
import re
import subprocess
import sys
import webbrowser
import winreg
from tkinter import font

import easygui
from PIL import Image, ImageTk
from github import Github

from waker.assets import get_asset
from waker.package import __code__, __author_website__, __repo_name__, __version__

DEFAULT_UI_FONT = 'Microsoft YaHei UI'

THEME_COLOR = {
    "dark": {
        "warning_bg": "#333333",
        "warning_fg": "white",
        "border": "#927934",
        "border_inactive": "#463714",
        "hover_bg": "#C89B3C",
        "hover_fg": "#010A13",
        "accent": "#C89B3C",
    },
    "light": {
        "warning_bg": "#F0E6D2",
        "warning_fg": "#010A13",
        "border": "#927934",
        "border_inactive": "#463714",
        "hover_bg": "#C89B3C",
        "hover_fg": "#010A13",
        "accent": "blue",
    }
}

HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".waker")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILENAME = os.path.join(CONFIG_DIR, "config.json")
AVAILABLE_LANGUAGES = ['en_US', 'zh_CN']
DEFAULT_LANGUAGE = 'en_US'


def change_font(font_family):
    for font_name in font.names():
        _font = font.nametofont(font_name)
        _font.config(family=font_family)


def open_repo_page():
    webbrowser.open(__code__)


def open_my_homepage():
    webbrowser.open(__author_website__)


def open_web(url):
    webbrowser.open(url)


def get_updates(repo_name, current_version):
    try:
        g = Github(retry=None)
        repo = g.get_repo(repo_name)

        latest_release = repo.get_latest_release()
        if latest_release.tag_name > current_version:
            return latest_release.tag_name, latest_release.html_url
    except Exception as e:
        pass

    return None, None


def check_for_updates(no_new_version_callback=None, language=DEFAULT_LANGUAGE):
    def get_str(key, default_value=None):
        return get_label(key, language, default_value)

    new_version, html_url = get_updates(__repo_name__, __version__)

    if new_version:
        decision = easygui.buttonbox(
            msg=f"{get_str('new_version_found')}: {new_version}\n{get_str('ask_for_update')}",
            title=get_str("new_version_found"),
            choices=list(map(get_str, ["go_to_download", "dont_download"])))
        if decision.lower() == get_str("go_to_download").lower():
            webbrowser.open(html_url)
            sys.exit()
        else:
            print("User chose not to download the new version.")
    else:
        no_new_version_callback = no_new_version_callback or print
        no_new_version_callback()


def read_json(file_path):
    try:
        if not os.path.exists(file_path):
            return {}
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}


def write_json(file_path, data, encoder_cls=None):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, cls=encoder_cls)


I18N = read_json(get_asset('i18n.json'))


def get_label(key, language, default_value=None):
    if language not in AVAILABLE_LANGUAGES:
        language = DEFAULT_LANGUAGE
    return I18N[language].get(key.lower(), default_value)


def is_number(num_str):
    return num_str == "" or num_str.isdigit()


def to_decimal(value, precision=1, default=0):
    try:
        number = float(value)
    except ValueError:
        match = re.search(r"(\d+\.\d+)", value)
        if match:
            number = float(match.group(1))
        else:
            return default

    rounded_number = round(number, precision)
    return rounded_number


def resized_icon(icon_path, max_size=(50, 50)):
    if not os.path.exists(icon_path):
        raise FileNotFoundError(f"Icon file not found: {icon_path}")
    if isinstance(max_size, int):
        max_size = (max_size, max_size)
    icon_image = Image.open(icon_path)
    original_width, original_height = icon_image.size
    if max_size is None or original_width <= max_size[0] and original_height <= max_size[1]:
        return ImageTk.PhotoImage(icon_image)
    ratio = min(max_size[0] / original_width, max_size[1] / original_height)
    new_size = (int(original_width * ratio), int(original_height * ratio))
    new_icon = icon_image.resize(new_size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(new_icon)


def set_autorun(app_name, app_path, enabled=True):
    """
    Set the program to run on startup
    :param app_name: program name
    :param app_path: program path
    :param enabled: enable or disable autorun
    """
    try:
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
                print(f"{app_name} set to run on startup.")
            else:
                winreg.DeleteValue(key, app_name)
                print(f"{app_name} removed from startup.")
    except Exception as e:
        print(f"Error setting {app_name} to run on startup: {e}")


def restart():
    """Restarts the current program."""
    app = sys.executable
    os.execl(app, app, *sys.argv)


def wake_screen():
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000002)
