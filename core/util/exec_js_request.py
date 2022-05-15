from bs4 import BeautifulSoup
from requests_html import HTML
from requests_html import HTMLSession
# from core.config.custom_http import *

import sys
import json
import base64

def base64_decode(s: str):
    return json.loads(base64.b64decode(s.encode('utf-8')))

url = sys.argv[1]
headers = base64_decode(sys.argv[2])
cookies = base64_decode(sys.argv[3])
timeout = int(sys.argv[4])

def parse_response(url, response, js_exec = False):
    '''
    解析响应包内容
    :param url:
    :param response:
    :return:
    '''
    if not js_exec:
        response.encoding = response.apparent_encoding if response.encoding == 'ISO-8859-1' else response.encoding
        response.encoding = "utf-8" if response.encoding is None else response.encoding
        html = response.content.decode(response.encoding,"ignore")
    else:
        html = response.html.html
    size = len(response.text)
    title = get_title(html).strip().replace('\r', '').replace('\n', '')
    status = response.status_code
    server = response.headers["Server"] if "Server" in response.headers else ""
    server = "" if len(server) > 50 else server
    history = response.history
    locations = [i.headers['location'].lower() for i in history]
    data = {
        "url": url,
        "title": title,
        "body": html,
        "status": status,
        "Server": server,
        "size": size,
        "header": dict(response.headers),
        "location": locations,
        "exception": False
    }
    return data

def get_title(html):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.title
    if title and title.text:
        return title.text
    if soup.h1:
        return soup.h1.text
    if soup.h2:
        return soup.h2.text
    if soup.h3:
        return soup.h3.text
    desc = soup.find('meta', attrs={'name': 'description'})
    if desc:
        return desc['content']

    word = soup.find('meta', attrs={'name': 'keywords'})
    if word:
        return word['content']

    text = soup.text
    if len(text) <= 200:
        return text
    return ''


with HTMLSession() as session:
    res = session.get(url, timeout=timeout, headers=headers,
                      cookies=cookies, verify=False, allow_redirects=True)
    h: HTML = res.html
    h.render(timeout=timeout * 5, sleep=1)
    data = parse_response(url, res, True)
    # print(data)
    print(json.dumps(data))