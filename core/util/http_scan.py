import re
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from urllib.parse import urlsplit
from core.util.custom_http import get_webInfo, get_simple_webInfo
from core.util.spider import *

class ThreadPool(object):
    def __init__(self):
        self.executor = ThreadPoolExecutor(min(32, os.cpu_count() + 4))

    def submit_task(self, fn, *args, **kwargs):
        """
        异步执行任务
        :param fn:
        :param args:
        :param kwargs:
        :return:
        """
        future = self.executor.submit(fn, *args, **kwargs)
        return future

thread_pool = ThreadPool()
lock = threading.Lock()

def regex_compare(regex, value):
    if re.search(regex, value, re.S):
        return True
    return False


def keyword_compare(key, value):
    if key.lower() in value.lower():
        return True
    return False


def query(method, val, location, data):
    '''

    :param method: 比较方法
    :param val: 指纹值
    :param location: 指纹位置
    :param data: http响应字典
    :return:
    '''
    if location == 'body':
        if method(val, data['body']):
            return True
    elif location == 'header':
        for key, value in data['header'].items():
            if method(val, key) or method(val, value):
                return True
    elif location == 'url':
        if method(val, data['url']):
            return True
        for url in data['location']:
            if method(val, url):
                return True
    elif location == 'title':
        if method(val, data['title']):
            return True
    else:
        return False


def parse_finger(data: dict, method, kwargs):
    '''
    用http请求结果（字典格式）解析出指纹信息
    :param data: 字典
    :param method: 探测方法
    :param kwargs: 探测参数
    :return: 指纹信息字典
    '''
    if method == "keyword":
        val = kwargs['value'].lower()
        location = kwargs['location']
        return query(keyword_compare, val, location, data)
    elif method == "regex":
        val = kwargs['value'].lower()
        location = kwargs['location']
        return query(regex_compare, val, location, data)
    elif method == "md5":
        val = kwargs['value'].lower()
        md5_right = hashlib.md5(data['content']).hexdigest()
        print(md5_right)
        if val.lower() == md5_right:
            return True
    return False


def finger_1scan(url: str, finger: dict, data: dict):
    '''
    对单个url用单个指纹扫描
    :param url:
    :param finger:
        {
            ...
            app: {

            }
        }
    :return:
    '''
    method = finger['method']
    if method == 'md5':
        result=urlsplit(url)
        par_path = result.path[:result.path.rfind('/')] if result.path.startswith('/') else ''
        url = f"{result.scheme}://{result.netloc}{par_path}{finger['path']}"
        data = get_simple_webInfo(url)
        if data['exception']:
            return False
    return parse_finger(data, method, finger)


def finger_scan(targer_url: str, fingers: list, setting: dict):
    '''
    对该url做全指纹扫描
    :param url:
    :param fingers:
    :return:
    '''
    res = {}
    browser = setting['browser']   # 是否开启模拟浏览器
    spider = setting['spider']  # 是否开启爬虫
    only_spider = setting['only_spider']    # 仅使用爬虫
    urls = []
    if not only_spider:
        if spider:
            urls = crawl_site(targer_url)   # 先爬再扫
        else:
            urls.append(targer_url)
        tasks = []
        for url in urls:
            # 每个url创建一个线程去匹配指纹
            # get_fingers(url, fingers, res, browser)
            tasks.append(thread_pool.submit_task(get_fingers, url, fingers, res, browser))
        # 等待所有任务执行完成
        wait(tasks, return_when=ALL_COMPLETED)
        # 对结果进行匹配次数的排序
        res = sorted(res.values(), key=lambda x: x['count'], reverse=True)
    else:
        urls = crawl_site(targer_url)
    urls_res = []
    count = 1
    for url in urls:
        urls_res.append({
            'id': count,
            'url': url
        })
        count += 1
    return urls_res, res


def get_fingers(url, fingers, res, browser):
    data = get_webInfo(url, browser)
    if data['exception']:
        return res
    for finger in fingers:
        if finger_1scan(url, finger, data):
            lock.acquire()
            if finger['app']['name'] in res:
                res[finger['app']['name']]['count'] += 1
            else:
                res[finger['app']['name']] = finger['app']
                res[finger['app']['name']]['count'] = 1
            lock.release()




if __name__ == '__main__':
    setting = {
        'browser': False
    }
    url = "http://localhost:3000/"
    fingers = [
        {
            'method': 'md5',
            'value': '1ba2ae710d927f13d483fd5d1e548c9b',
            'path': '/favicon.ico',
            'app': {
                'name': 'vue'
            }
        }
    ]
    print(finger_scan(url, fingers, setting))
