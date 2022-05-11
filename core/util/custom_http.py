import json
import random
import subprocess
import base64
from bs4 import BeautifulSoup
import requests
from core.config.custom_http import *
from requests_html import HTML
from requests_html import HTMLSession
import asyncio
from multiprocessing import Process, Queue
# 当前路径
current_path = os.path.dirname(__file__)

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
        "header": response.headers,
        "location": locations,
        "exception": False
    }
    return data


def get_webInfo(url, js_exec = False):
    '''
    获取http详细响应字典
    :param url:
    :return:
    '''
    try:
        if not js_exec:
            with requests.get(url, timeout=10, headers=get_headers(),
                              cookies=get_cookies(), verify=False, allow_redirects=True) as res:
                return parse_response(url, res)
        else:
            cmd = f"python {os.path.join(current_path, 'exec_js_request.py')} {url}"
            p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE)
            out,err = p.communicate()
            for line in out.splitlines():
                return json.loads(line.decode())
    except Exception as e:
        return  {
            "url": url,
            "status": str(e),
            "exception": True
        }




def get_simple_webInfo(url):
    '''
    获取http简单的响应字典
    :param url:
    :return:
    '''
    try:
        with requests.get(url, timeout=10, headers=get_headers(),
                          cookies=get_cookies(), verify=False, allow_redirects=True) as res:
            return {
                "url": url,
                "status": res.status_code,
                "content": res.content,
                "exception": False
            }
    except Exception as e:
        return {
            "url": url,
            "status": str(e),
            "exception": True
        }


if __name__ == '__main__':
    url = "http://localhost:3000/"


    d = get_webInfo(url, True)
    print(d)

