import random
from bs4 import BeautifulSoup
import requests
from core.config.custom_http import *

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

def parse_response(url, response):
    '''
    解析响应包内容
    :param url:
    :param response:
    :return:
    '''
    response.encoding = response.apparent_encoding if response.encoding == 'ISO-8859-1' else response.encoding
    response.encoding = "utf-8" if response.encoding is None else response.encoding
    html = response.content.decode(response.encoding,"ignore")
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
        "header": response.headers,
        "locations": locations,
    }
    return data


def get_webInfo(url):
    try:
        with requests.get(url, timeout=10, headers=get_headers(),
                          cookies=get_cookies(), verify=False, allow_redirects=True) as res:
            return parse_response(url, res)
    except Exception as e:
        return {
            "url": url,
            "status": str(e)
        }

if __name__ == '__main__':
    print(get_webInfo("http://one.hubu.edu.cn/#/index"))