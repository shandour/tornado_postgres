DROP TABLE IF EXISTS bloggers;
CREATE TABLE bloggers (
      id SERIAL PRIMARY KEY,
      username VARCHAR(200) UNIQUE NOT NULL,
      email VARCHAR(100) NOT NULL,
      password VARCHAR(100) NOT NULL
);


DROP TABLE IF EXISTS posts;
CREATE TABLE posts (
       id SERIAL PRIMARY KEY,
       topic VARCHAR(100),
       text TEXT NOT NULL,
       created TIMESTAMP,
       edited TIMESTAMP,
       likes INT,
       dislikes INT,
       blogger_id INT NOT NULL REFERENCES bloggers(id)
);


DROP TABLE IF EXISTS messages;
CREATE TABLE messages (
       id SERIAL PRIMARY KEY,
       topic VARCHAR(100),
       sent TIMESTAMP,
       text TEXT NOT NULL,
       author_id INT NOT NULL REFERENCES bloggers(id),
       author_name VARCHAR(200) NOT NULL REFERENCES bloggers(username),
       addressee_id INT NOT NULL REFERENCES bloggers(id),
       addressee_name VARCHAR(200) NOT NULL REFERENCES bloggers(username),
       unread BOOLEAN
);


DROP TABLE IF EXISTS likes_dislikes;
CREATE TABLE likes_dislikes (
       blogger_id INT NOT NULL REFERENCES bloggers(id),
       post_id INT NOT NULL REFERENCES posts(id),
       liked BOOLEAN
);


CREATE INDEX ON bloggers(username);
CREATE INDEX ON posts(topic);
CREATE INDEX ON posts(created);
CREATE INDEX ON posts(likes, dislikes);
CREATE INDEX ON messages(unread);
