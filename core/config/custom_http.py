import random
import os

# 当前路径
current_path = os.path.dirname(__file__)

user_agents = [i.strip() for i in open(os.path.join(current_path, 'useragents.txt'), "r").readlines()]

def get_headers():
    ua = random.choice(user_agents)
    headers = {
        'Accept': 'text/html,application/xhtml+xml,'
                  'application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': ua,
    }
    return headers

def get_cookies():
    cookies = {
        'me': '14Finger'
    }
if __name__ == '__main__':
    print()
    print(user_agents)
