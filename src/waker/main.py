from waker.app import App
from waker.utils import read_json, check_for_updates, CONFIG_FILENAME

if __name__ == '__main__':
    check_for_updates()

    config = read_json(CONFIG_FILENAME) or {}

    app = App(config)
    app.run()
