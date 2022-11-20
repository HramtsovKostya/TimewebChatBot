# -------------------------------------------------------------------------

import config as cfg
import json

from os import path


# -------------------------------------------------------------------------

def load_users():
    users = []

    if path.exists(cfg.USERS):
        with open(cfg.USERS, 'r') as f:
            users = json.load(f)

    return users


def save_users(users: list):
    with open(cfg.USERS, 'w') as f:
        json.dump(users, f)


def add_user(user: dict):
    users = load_users()
    users.append(user)
    save_users(users)


def del_user(sel_user: dict):
    users = load_users()
    users.remove(sel_user)
    save_users(users)


def edit_user(new_user: dict):
    users = load_users()

    index = users.index([u for u in users if u['login'] == new_user['login']][0])
    users[index] = new_user

    save_users(users)

# -------------------------------------------------------------------------
