import random
import os


# 当前路径
current_path = os.path.dirname(__file__)

user_agents = [i.strip() for i in open(os.path.join(current_path, 'useragents.txt'), "r").readlines()]

is_django = os.getenv('DJANGO_SETTINGS_MODULE', None) != None

if is_django:
    from api.models import Config

def get_headers():
    ua = random.choice(user_agents)
    headers = {
        'User-Agent': ua,
    }
    if is_django:
        config = Config.objects.get(pk=1)
        config_h = config.headers
        for key, value in config_h.items():
            headers[key] = value
    return headers

def get_cookies():
    cookies = {
    }
    if is_django:
        config = Config.objects.get(pk=1)
        config_c = config.cookies
        for key, value in config_c.items():
            cookies[key] = value
    return cookies

def get_timeout():
    if is_django:
        config = Config.objects.get(pk=1)
        return config.timeout
    else:
        return 10

if __name__ == '__main__':
    print()
    print(get_headers())
