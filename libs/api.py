# -------------------------------------------------------------------------

import config as cfg
import requests as rq
import json


# -------------------------------------------------------------------------

def get_token(login: str, password: str):
    url = cfg.HOST_NAME + '/api/v2/auth'
    auth = (login, password)

    headers = {
        'accept': 'application/json',
        'x-app-key': cfg.APP_KEY
    }

    try:
        resp = rq.post(url, headers=headers, auth=auth)
        data = json.loads(resp.text)
        cfg.ACCESS_TOKEN = data['access_token']
        return resp.status_code

    except Exception:
        print('Не удалось выполнить авторизацию аккаунта ' + login + '!')

    return 401


def get_finances():
    url = cfg.HOST_NAME + '/api/v1/accounts/finances'

    headers = {
        'accept': 'application/json',
        'x-app-key': cfg.APP_KEY,
        'Authorization': 'Bearer ' + cfg.ACCESS_TOKEN
    }

    resp = rq.get(url=url, headers=headers)
    data = json.loads(resp.text)
    return data['finances']

# -------------------------------------------------------------------------
