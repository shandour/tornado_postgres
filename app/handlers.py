import datetime

import psycopg2
from tornado import web
from sqlalchemy import select, desc, and_, or_
from aiopg.sa import create_engine

from .db import bloggers, posts, messages, likes_dislikes
from .marshmallow_schemata import (
    PostSchema,
    LoginSchema,
    RegisterSchema,
    MessageSchema,
    SearchSchema)


class BaseHandler(web.RequestHandler):
    async def _get_engine(self):
        engine = await create_engine(self.application.settings['database'])
        return engine

    def get_current_user(self):
        user_dict = {'username': self.get_secure_cookie("user"),
                     'user_id': self.get_secure_cookie("user_id")}
        if user_dict['username'] and user_dict['user_id']:
            return user_dict

    def _add_user_cookie_and_redirect(self, user_id, username):
        self.set_secure_cookie('user_id', user_id)
        self.set_secure_cookie('user', username)
        self.redirect('/')


class MainHandler(BaseHandler):
    async def get(self):
        engine = await self._get_engine()
        top_blog = None

        async with engine.acquire() as conn:
            top_blog = await conn.execute(
                select([posts.c.id,
                        posts.c.topic,
                        posts.c.text,
                        posts.c.likes,
                        posts.c.dislikes,
                        bloggers.c.username,
                        bloggers.c.id])
                .select_from(posts.join(bloggers))
                .order_by(desc(posts.c.likes))
                .limit(1))
            top_blog = await top_blog.fetchone()

            if top_blog:
                top_blog = {'post_id': top_blog[0],
                            'topic': top_blog[1],
                            'text': top_blog[2],
                            'likes': top_blog[3],
                            'dislikes': top_blog[4],
                            'blogger_name': top_blog[5],
                            'blogger_id': top_blog[6]}

        self.render('index.html', top_blog=top_blog)


class BlogHandler(BaseHandler):
    async def _get_entries(self, blogger_id):
        engine = await self._get_engine()

        if self.current_user:
            user_likes_id = int(self.current_user['user_id'])
        else:
            user_likes_id = None

        async with engine.acquire() as conn:
            entries_result = await conn.execute(
                select([posts.c.id,
                        posts.c.topic,
                        posts.c.text,
                        posts.c.likes,
                        posts.c.dislikes,
                        likes_dislikes.c.liked])
                .select_from(posts.join(bloggers)
                             .outerjoin(
                                 likes_dislikes,
                                 and_(likes_dislikes.c.blogger_id == user_likes_id,
                                      likes_dislikes.c.post_id == posts.c.id)))
                .where(bloggers.c.id == blogger_id)
                .order_by(desc(posts.c.created)))
            entries = [{'post_id': e[0],
                        'topic': e[1],
                        'text': e[2],
                        'likes': e[3],
                        'dislikes': e[4],
                        'liked': e[5]}
                       for e in await entries_result.fetchall()]
        return entries

    async def get(self, blogger_id):
        current = False
        top = False
        blogger = None
        if blogger_id == 'current':
            current = True
            blogger_id = self.get_secure_cookie('user_id')
            if not blogger_id:
                self.redirect('/login')
                return
        engine = await self._get_engine()

        async with engine.acquire() as conn:
            if blogger_id == 'top':
                entries_result = await conn.execute(
                    "SELECT DISTINCT ON(b.username)"
                    "p.id, p.topic, p.text, p.likes,"
                    "p.dislikes, b.id, b.username"
                    " FROM posts AS p JOIN bloggers"
                    " AS b ON b.id = p.blogger_id"
                    " ORDER BY username, GREATEST(likes, dislikes) LIMIT {}"
                    .format(self.application.settings["top_blogs_number"]))
                entries = [{'post_id': e[0],
                            'topic': e[1],
                            'text': e[2],
                            'likes': e[3],
                            'dislikes': e[4],
                            'blogger_id': e[5],
                            'blogger_username': e[6]}
                           for e in await entries_result.fetchall()]
                top = True
            else:
                blogger_id = int(blogger_id)
                blogger_result = await conn.execute(
                    select([bloggers.c.id, bloggers.c.username])
                    .where(bloggers.c.id == int(blogger_id)))
                blogger = await blogger_result.fetchone()
                if not blogger:
                    raise web.HTTPError(404)
                entries = await self._get_entries(blogger_id)
                blogger = {'id': blogger[0] if not current else 'current',
                           'username': blogger[1]}

            self.render('blog.html',
                        entries=entries,
                        blogger=blogger,
                        current=current,
                        top=top,
                        errors={})

    @web.authenticated
    async def post(self, blogger_id):
        if not blogger_id == "current":
            raise HTTPError(403)

        update_dict, errors = PostSchema().load(
            {k: v[0] for k, v in self.request.body_arguments.items()})

        if errors:
            blogger_id = int(self.current_user['user_id'])
            blogger_username = self.current_user['username'].decode('utf-8')
            entries = await self._get_entries(blogger_id)
            blogger = {'id': blogger_id, 'username': blogger_username}
            self.render("blog.html",
                        entries=entries,
                        blogger=blogger,
                        current=True,
                        top=False,
                        errors=errors)
            return

        engine = await self._get_engine()
        async with engine.acquire() as conn:
            await conn.execute(
                posts
                .insert()
                .values(topic=update_dict['topic'],
                        text=update_dict['content'],
                        blogger_id=int(self.current_user['user_id'])))
            self.redirect('/blogs/current')


class PostHandler(BaseHandler):
    async def get(self, blogger_id, post_id, edit_flag):
        current = False
        if self.current_user:
            user_likes_id = int(self.current_user['user_id'])
        else:
            user_likes_id = None

        if blogger_id == 'current':
            current = True
            if not user_likes_id:
                raise HTTPError(404)
        elif blogger_id != 'current' and edit_flag:
            raise HTTPError(403)

        engine = await self._get_engine()

        async with engine.acquire() as conn:
            post_result = await conn.execute(
                select([posts.c.id,
                        posts.c.topic,
                        posts.c.text,
                        posts.c.likes,
                        posts.c.dislikes,
                        posts.c.created,
                        posts.c.edited,
                        bloggers.c.id,
                        bloggers.c.username,
                        likes_dislikes.c.liked])
                .select_from(
                    posts.join(bloggers)
                         .outerjoin(
                             likes_dislikes,
                             and_(likes_dislikes.c.blogger_id == user_likes_id,
                                  likes_dislikes.c.post_id == posts.c.id)))
                .where(posts.c.id == post_id))
            p = await post_result.fetchone()

            post = {'post_id': p[0],
                    'topic': p[1],
                    'text': p[2],
                    'likes': p[3],
                    'dislikes': p[4],
                    'created': p[5],
                    'edited': p[6],
                    'blogger_id': p[7],
                    'blogger_username': p[8],
                    'liked': p[9]}

            if not post:
                raise web.HTTPError(404)
            self.render('post.html', post=post, current=current)

    @web.authenticated
    async def put(self, blogger_id, post_id, edit_flag):
        blogger_id = int(blogger_id)
        post_id = int(post_id)

        if edit_flag:
            raise web.HTTPError(400)
        elif not blogger_id == int(self.current_user['user_id']):
                raise web.HTTPError(403)

        update_dict, errors = PostSchema().load(
           {k: v[0] for k, v in self.request.body_arguments.items()})

        if errors:
            self.clear()
            self.set_status(400)
            self.finish(errors)
            return

        engine = await self._get_engine()

        async with engine.acquire() as conn:
            await conn.execute(
                posts.update()
                .where(posts.c.id == post_id)
                .values(topic=update_dict['topic'],
                        text=update_dict['content'],
                        edited=datetime.datetime.utcnow()))
        self.clear()
        self.set_status(204)
        self.flush()


class LikesDislikesHandler(BaseHandler):
    @web.authenticated
    async def put(self, post_id):
        attitude = self.get_query_argument('attitude', None)

        if attitude in ['like', 'dislike']:
            new_attitude_dct = await self._calculate_reaction(
                attitude, post_id)
            self.clear()
            self.set_status(200)
            self.finish(new_attitude_dct)
            return
        else:
            raise web.HTTPError(400)

    async def _calculate_reaction(self, attitude, post_id):
        user_id = int(self.current_user['user_id'])
        attitude_function = (self._like_post if attitude == 'like'
                             else self._dislike_post)

        engine = await self._get_engine()
        async with engine.acquire() as conn:
            current_status_result = await conn.execute(
                select([likes_dislikes.c.liked])
                .where(and_(
                    likes_dislikes.c.post_id == post_id,
                    likes_dislikes.c.blogger_id == user_id)))
            current_status = await current_status_result.fetchone()

            if not current_status:
                return await attitude_function(conn, user_id, post_id)
            elif not current_status[0]:
                return await attitude_function(conn, user_id, post_id,
                                               current_status='disliked')
            else:
                return await attitude_function(conn, user_id, post_id,
                                               current_status='liked')

    async def _like_post(self, conn, user_id, post_id, current_status=None):
        if not current_status:
            await conn.execute(
                likes_dislikes
                .insert()
                .values(blogger_id=user_id,
                        post_id=post_id,
                        liked=True))
            await conn.execute(
                posts.update()
                .values(likes=(posts.c.likes + 1))
                .where(posts.c.id == post_id))

            return {'likes': 1, 'dislikes': 0}

        elif current_status == 'disliked':
            await conn.execute(
                posts
                .update()
                .values(likes=(posts.c.likes + 1),
                        dislikes=(posts.c.dislikes - 1))
                .where(posts.c.id == post_id))
            await conn.execute(
                likes_dislikes
                .update()
                .values(liked=True)
                .where(and_(likes_dislikes.c.blogger_id == user_id,
                            likes_dislikes.c.post_id == post_id)))

            return {'likes': 1, 'dislikes': -1}

        else:
            await conn.execute(
                posts
                .update()
                .values(likes=(posts.c.likes - 1))
                .where(posts.c.id == post_id))
            await conn.execute(
                likes_dislikes
                .delete()
                .where(and_(likes_dislikes.c.blogger_id == user_id,
                            likes_dislikes.c.post_id == post_id)))

            return {'likes': -1, 'dislikes': 0}

    async def _dislike_post(self, conn, user_id, post_id, current_status=None):
        if not current_status:
            await conn.execute(
                likes_dislikes
                .insert()
                .values(blogger_id=user_id,
                        post_id=post_id,
                        liked=False))
            await conn.execute(
                posts
                .update()
                .values(dislikes=(posts.c.dislikes + 1))
                .where(posts.c.id == post_id))

            return {'likes': 0, 'dislikes': 1}

        elif current_status == 'disliked':
            await conn.execute(
                posts
                .update()
                .values(dislikes=(posts.c.dislikes - 1))
                .where(posts.c.id == post_id))
            await conn.execute(
                likes_dislikes
                .delete()
                .where(and_(likes_dislikes.c.blogger_id == user_id,
                            likes_dislikes.c.post_id == post_id)))

            return {'likes': 0, 'dislikes': -1}

        else:
            await conn.execute(
                posts
                .update()
                .values(likes=(posts.c.likes - 1),
                        dislikes=(posts.c.dislikes + 1))
                .where(posts.c.id == post_id))
            await conn.execute(
                likes_dislikes
                .update()
                .values(liked=False)
                .where(and_(likes_dislikes.c.blogger_id == user_id,
                            likes_dislikes.c.post_id == post_id)))

            return {'likes': -1, 'dislikes': 1}


class LoginHandler(BaseHandler):
    def get(self):
        if self.current_user:
            self.redirect('/')
        self.render('login.html', errors={})

    async def post(self):
        data, errors = LoginSchema().load(
            {k: v[0] for k, v in self.request.body_arguments.items()})
        if errors:
            self.render('login.html',
                        errors=errors)

        engine = await self._get_engine()
        async with engine.acquire() as conn:
            blogger = await conn.execute(
                select([bloggers.c.id, bloggers.c.username])
                .where((bloggers.c.email == data['email']) &
                       (bloggers.c.password == data['password'])))
            blogger = await blogger.fetchone()
            if blogger:
                self._add_user_cookie_and_redirect(str(blogger[0]),
                                                   str(blogger[1]))
            else:
                self.render('login.html',
                            errors={
                                'password': ['Password or email incorrect'],
                                'email': ['Password or email incorrect']})


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user_id')
        self.clear_cookie('user')
        self.redirect('/')


class RegisterHandler(BaseHandler):
    def get(self):
        self.render('register.html', errors={}, data={})

    async def post(self):
        data, errors = RegisterSchema().load(
            {k: v[0] for k, v in self.request.body_arguments.items()})

        if errors:
            self.render('register.html', errors=errors, data=data)
            return

        engine = await self._get_engine()

        async with engine.acquire() as conn:
            blogger_register_result = await conn.execute(
                bloggers.insert().values(
                    username=data['username'],
                    email=data['email'],
                    password=data['password'])
                .returning(bloggers.c.id, bloggers.c.username))

            blogger_username_id = await blogger_register_result.fetchone()
            self._add_user_cookie_and_redirect(
                str(blogger_username_id[0]),
                blogger_username_id[1])


class InboxHandler(BaseHandler):
    @web.authenticated
    async def get(self, message_id=None):
        if self.request.uri.endswith('/compose'):
            self.render('compose_message.html', errors=[])
            return

        engine = await self._get_engine()
        user_id = int(self.current_user['user_id'])

        async with engine.acquire() as conn:
            if message_id:
                message_id = int(message_id)
                where_clause = (messages.c.id == message_id)
                limit = 1
            else:
                status = self.get_query_argument('status', None)
                sentby = self.get_query_argument('sentby', None)
                
                if status and sentby:
                    if sentby == 'others':
                        if status == 'read':
                            whr = and_(messages.c.unread == False,
                                       messages.c.addressee_id == user_id)
                        elif status == 'unread':
                            whr = and_(messages.c.unread == True,
                                       messages.c.addressee_id == user_id)
                        else:
                            whr = (messages.c.addressee_id == user_id)
                    elif sentby == "you":
                        whr = (messages.c.author_id == user_id)
                else:
                        whr = or_(messages.c.author_id == user_id,
                                  messages.c.addressee_id == user_id)
                limit = None

            messages_result = await conn.execute(
                select([messages.c.id,
                        messages.c.topic,
                        messages.c.sent,
                        messages.c.text,
                        messages.c.addressee_id,
                        messages.c.addressee_name,
                        messages.c.author_id,
                        messages.c.author_name,
                        messages.c.unread])
                .where(whr)
                .limit(limit)
                .order_by(messages.c.sent))

            messages_lst = [
                {'message_id': m[0],
                 'message_topic': m[1],
                 'message_sent': m[2],
                 'message_text': m[3],
                 'message_addressee_id': m[4],
                 'message_addressee_username': m[5],
                 'message_author_id': m[6],
                 'message_author_username': m[7],
                 'message_unread': m[8]}
                for m in await messages_result.fetchall()]

            if message_id:
                self.render('inbox_message.html', message=messages_lst[0])
            else:
                self.render('inbox.html', messages=messages_lst)

    @web.authenticated
    async def post(self):
        if not self.request.uri.endswith('/compose'):
            raise web.HTTPError(400)

        data, errors = MessageSchema().load(
            {k: v[0] for k, v in self.request.body_arguments.items()})
        if errors:
            self.render('compose_message.html', errors=errors, data=data)
            return

        engine = await self._get_engine()

        async with engine.acquire() as conn:
            bloggers_clmn = (bloggers.c.email
                             if '@' and '.' in data['addressee']
                             else bloggers.c.username)
            addressee_result = await conn.execute(
                select([bloggers.c.id, bloggers.c.username])
                .where(bloggers_clmn == data['addressee']))
            a = await addressee_result.fetchone()

            addressee = {'user_id': a[0], 'username': a[1]}

            await conn.execute(
                messages.insert().values(
                    topic=message_dict['topic'],
                    text=message_dict['content'],
                    author_id=int(self.current_user['user_id']),
                    author_name=self.current_user['username'].decode('utf-8'),
                    addressee_id=addressee['user_id'],
                    addressee_name=addressee['username']))

            self.redirect('/inbox')

    @web.authenticated
    async def put(self, message_id):
        engine = await self._get_engine()

        if self.request.arguments.get('value')[0].decode('utf-8') == 'read':
            boolean_unread = False
        else:
            boolean_unread = True

        async with engine.acquire() as conn:
            await conn.execute(
                messages.update().where(
                    and_(messages.c.id == int(message_id),
                         messages.c.addressee_id == int(
                             self.current_user['user_id'])))
                .values(unread=boolean_unread)
            )
            self.write('')


class BloggerHandler(BaseHandler):
    async def get(self, blogger_id):
        current = True if blogger_id == "current" else False
        if current and not self.current_user:
            raise web.HTTPError(403)
        # to prevent user from viewing his own profile
        # in a guest mode and send messages to himself
        elif not current and (int(blogger_id) ==
                              int(self.current_user['user_id'])):
            self.redirect('/blogger/current/profile')
        elif current:
            blogger_id = self.current_user['user_id']
        engine = await self._get_engine()

        async with engine.acquire() as conn:
            blogger_result = await conn.execute(
                select([bloggers.c.id,
                        bloggers.c.username,
                        bloggers.c.email])
                .where(bloggers.c.id == int(blogger_id)))
            b = await blogger_result.fetchone()
            blogger = {
                'blogger_id': b[0],
                "blogger_username": b[1],
                "blogger_email": b[2]
            }

        self.render('profile.html', blogger=blogger, current=current)


class SearchHandler(BaseHandler):
    async def get(self):
        bloggers_flag = topics_flag = False
        data, errors = SearchSchema().load({
            'option': self.get_query_arguments('option'),
            'query': self.get_query_argument('query')
        })

        if errors:
            self.render('result_page.html',
                        results=None,
                        errors=errors)
            return

        if len(data['option']) == 2:
            bloggers_flag = topics_flag = True
        elif data['option'] == 'bloggers':
            bloggers_flag = True
        elif data['option'] == 'topics':
            topics_flag = True

        engine = await self._get_engine()

        async with engine.acquire() as conn:
            search_topics = search_bloggers = None
            results = {}

            if bloggers_flag:
                search_bloggers_result = await conn.execute(
                    select([bloggers.c.id, bloggers.c.username])
                    .where(bloggers.c.username.like('%{}%'.format(query))))
                search_bloggers = await search_bloggers_result.fetchall()

            if topics_flag:
                search_topics_result = await conn.execute(
                    select([posts.c.id, posts.c.topic, posts.c.blogger_id])
                    .where(posts.c.topic.like('%{}%'.format(query)))
                    .order_by(posts.c.created))
                search_topics = await search_topics_result.fetchall()

            if search_bloggers:
                results["bloggers"] = [
                    {'id': i[0],
                     'username': i[1]}
                    for i in search_bloggers
                ]

            if search_topics:
                results["posts"] = [
                    {'id': i[0],
                     'topic': i[1],
                     'blogger_id': i[2]}
                    for i in search_topics
                ]

            self.render('result_page.html',
                        results=results,
                        errors=None)
