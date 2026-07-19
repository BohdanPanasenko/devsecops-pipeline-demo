-- Minimal schema for the DevSecOps demo app.
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS items;

CREATE TABLE users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE items (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    owner TEXT NOT NULL
);

INSERT INTO users (username, password) VALUES ('alice', 'password123');
INSERT INTO users (username, password) VALUES ('bob', 'hunter2');

INSERT INTO items (name, owner) VALUES ('Laptop', 'alice');
INSERT INTO items (name, owner) VALUES ('Keyboard', 'alice');
INSERT INTO items (name, owner) VALUES ('Monitor', 'bob');
