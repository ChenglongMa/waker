import platform
import threading
import time

import psutil
import pyautogui
import pymsgbox
import pystray
from PIL import Image

from waker.package import __app_name__, __package_name__


def get_idle_time():
    this_os = platform.system()
    if this_os == "Linux":
        return get_idle_time_unix_os()
    elif this_os == "Darwin":
        return get_idle_time_mac_os()
    elif this_os == "Windows":
        return get_idle_time_win_os()
    else:
        raise NotImplementedError(f"Platform '{this_os}' is not supported.")


def get_idle_time_unix_like_os() -> float:
    idle_time = psutil.cpu_times().idle
    return idle_time


def get_idle_time_unix_os():
    import subprocess

    idle_time = subprocess.check_output("xprintidle", shell=True).decode("utf-8")
    return float(idle_time) / 1000.0


def get_idle_time_mac_os():
    import subprocess

    idle_time = subprocess.check_output("ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF/1000000000; exit}'",
                                        shell=True).decode("utf-8")
    return float(idle_time)


def get_idle_time_win_os():
    import ctypes

    class LastInputInfo(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint),
                    ("dwTime", ctypes.c_ulong)]

    last_input_info = LastInputInfo()
    last_input_info.cbSize = ctypes.sizeof(last_input_info)

    user32 = ctypes.windll.user32
    user32.GetLastInputInfo(ctypes.byref(last_input_info))

    millis = ctypes.windll.kernel32.GetTickCount() - last_input_info.dwTime
    return millis / 1000.0


def wake_up():
    pyautogui.press('alt')


class Waker:

    def __init__(self):
        super().__init__()
        self.menu_running_text = "Stop"
        self.is_running = False
        self._thread = None
        self.wake_up_interval = 5 * 60  # unit: seconds
        self.check_interval = 5
        self.lock = threading.Lock()
        self.os = platform.system()
        self.icon_suffix = "win" if self.os == "Windows" else "mac"

    def run(self):
        while self.is_running:
            idle_time = get_idle_time()
            print("Idle time:", idle_time)
            if idle_time > self.wake_up_interval:
                print("System is idle for more than", self.wake_up_interval, "seconds.")
                with self.lock:
                    wake_up()
            time.sleep(self.check_interval)

    def on_start(self, icon: pystray.Icon, item: pystray.MenuItem):
        self.on_stop(icon, item, show_message=False)
        icon.icon = Image.open(f"ui/active_{self.icon_suffix}.png")
        icon.title = f"{__app_name__} - Active"
        icon.notify(message="Waker is now running 🌞.", title=__app_name__)
        self.is_running = True
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def on_stop(self, icon: pystray.Icon, item: pystray.MenuItem, show_message=True):
        print("Stopping Waker.")
        if show_message:
            icon.icon = Image.open(f"ui/inactive_{self.icon_suffix}.png")
            icon.title = f"{__app_name__} - Inactive"
            icon.notify(message="Waker is now sleeping 🌛.", title=__app_name__)
        self.is_running = False
        if self._thread:
            self._thread.join()

    def on_toggle_running(self, icon: pystray.Icon, item: pystray.MenuItem):
        if self.is_running:
            self.on_stop(icon, item)
            self.menu_running_text = "Start"
        else:
            self.on_start(icon, item)
            self.menu_running_text = "Stop"
        icon.update_menu()

    def on_set_interval(self, icon: pystray.Icon, item: pystray.MenuItem):
        print("Setting wake-up interval.")
        interval = pymsgbox.prompt(
            text="Enter wake-up interval (in minutes):",
            title=__app_name__,
            default=str(self.wake_up_interval / 60.0),
            root=None,
            timeout=None
        )
        print("Interval:", interval)
        if interval is None:
            return
        try:
            self.wake_up_interval = float(interval) * 60
            icon.notify(message=f"Wake-up interval set to {interval} minutes.", title=__app_name__)
        except ValueError:
            icon.notify(message="Invalid input. Please enter a valid number.", title=__app_name__)

    def on_exit(self, icon: pystray.Icon, item: pystray.MenuItem):
        self.on_stop(icon, item)
        icon.stop()


def main():
    waker = Waker()
    image = Image.open("ui/active_win.png")
    menu = pystray.Menu(
        pystray.MenuItem(lambda text: waker.menu_running_text, waker.on_toggle_running),
        pystray.MenuItem("Wake-up Interval", waker.on_set_interval),
        pystray.MenuItem("Exit", waker.on_exit),
    )
    icon = pystray.Icon(name=__package_name__, icon=image, title=__app_name__, menu=menu)
    waker.on_start(icon, menu.items[0])
    icon.run()


if __name__ == "__main__":
    main()
