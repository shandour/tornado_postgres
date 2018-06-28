from tornado import ioloop

from app import Application
from local_settings import local_settings_dict

if __name__ == "__main__":
    app = Application(local_settings_dict)
    app.listen(8888)
    ioloop.IOLoop.current().start()
