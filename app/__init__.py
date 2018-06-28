import os

from tornado import web

from .handlers import (
    MainHandler,
    BlogHandler,
    PostHandler,
    LoginHandler,
    LogoutHandler,
    RegisterHandler,
    InboxHandler,
    BloggerHandler,
    LikesDislikesHandler,
    SearchHandler)


class Application(web.Application):
    def __init__(self, local_settings):
        handlers = [
            (r"/", MainHandler),
            (r'/blogs/([0-9]+|current|top)', BlogHandler),
            (r'/blogs/([0-9]+|current)/posts/([0-9]+)(/edit)*', PostHandler),
            (r'/posts/([0-9])+', LikesDislikesHandler),
            (r'/blogger/([0-9]+|current)/profile', BloggerHandler),
            (r'/inbox', InboxHandler),
            (r'/inbox/compose', InboxHandler),
            (r'/inbox/([0-9]+)', InboxHandler),
            (r'/search', SearchHandler),
            (r'/login', LoginHandler),
            (r'/logout', LogoutHandler),
            (r'/register', RegisterHandler)
        ]

        settings = {
            "template_path": os.path.join(
                os.path.dirname(__file__), "../templates"),
            "static_path": os.path.join(os.path.dirname(__file__),
                                        "../static"),
            "xsrf_cookies": True,
            "login_url": "/login"
        }

        settings.update(local_settings)

        super().__init__(handlers, **settings)
