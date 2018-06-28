from datetime import datetime

import sqlalchemy as sa


metadata = sa.MetaData()

bloggers = sa.Table('bloggers', metadata,
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('username', sa.String(200), unique=True),
                    sa.Column('email', sa.String(100), unique=True),
                    sa.Column('password', sa.String(100)))

posts = sa.Table('posts', metadata,
                 sa.Column('id', sa.Integer, primary_key=True),
                 sa.Column('topic', sa.String(100)),
                 sa.Column('text', sa.Text),
                 sa.Column('created', sa.DateTime, default=datetime.utcnow),
                 sa.Column('edited', sa.DateTime, default=datetime.utcnow),
                 sa.Column('likes', sa.Integer, default=0),
                 sa.Column('dislikes', sa.Integer, default=0),
                 sa.Column('blogger_id', sa.ForeignKey(bloggers.c.id)))

messages = sa.Table('messages', metadata,
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('topic', sa.String(100)),
                    sa.Column('text', sa.Text),
                    sa.Column('sent', sa.DateTime, default=datetime.utcnow),
                    sa.Column('author_id', sa.ForeignKey(bloggers.c.id)),
                    sa.Column('author_name', sa.String(200)),
                    sa.Column('addressee_id', sa.ForeignKey(bloggers.c.id)),
                    sa.Column('addressee_name', sa.String(200)),
                    sa.Column('unread', sa.Boolean, default=True))

# to track if certain user(s) liked/disliekd certain post(s);
# liked=False stands for a dislike
likes_dislikes = sa.Table('likes_dislikes', metadata,
                          sa.Column('blogger_id',
                                    sa.ForeignKey(bloggers.c.id)),
                          sa.Column('post_id', sa.ForeignKey(posts.c.id)),
                          sa.Column('liked', sa.Boolean))
