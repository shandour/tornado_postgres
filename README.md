A simplistic blog application, using Tornado, aiopg and aiopg.sa, and Marshmallow.

The 2 relevant entities are Bloggers and Posts. Bloggers can write/edit posts, like/dislikes posts, write messages to other bloggers and receive messages addressed to them.

To have it work create a local_settings.py file which is to have a local_settings_dict variable, minimally including such entries as: 'cookie_secret', 'database', 'schema_path'; 'top_blogs_number' (so that BlogHandler can know what number of popular blogs are to be displayed)

