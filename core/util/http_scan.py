import re
import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED, as_completed
from urllib.parse import urlsplit
from core.util.custom_http import get_webInfo, get_simple_webInfo
from core.util.spider import *


is_django = os.getenv('DJANGO_SETTINGS_MODULE', None) != None
if is_django:
    from api.models import Config
    from django.db import connections

class ThreadPool(object):
    def __init__(self):
        if is_django:
            db_ready = False
            re_count = 500
            while not db_ready and re_count > 0:
                try:
                    cursor = connections['default'].cursor()
                    db_ready = True
                except:
                    print("数据库连接失败，sql文件较大，可能正在创建中（与cpu速度有关），等待5秒后重试")
                    time.sleep(5)
                    re_count -= 1
            try:
                config = Config.objects.get(pk=1)
            except:
                config = Config.objects.create(id=1)
            thread_num = config.thread_num
        else:
            thread_num = os.cpu_count() if os.cpu_count() < 10 else os.cpu_count() * 2 + 4
        self.executor = ThreadPoolExecutor(thread_num)


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

    def close(self):
        self.executor.shutdown()

thread_pool = ThreadPool()
batch_thread_pool = ThreadPool()
finger_thread_pool = ThreadPool()
lock = threading.Lock()
batch_lock = threading.Lock()

def recreate_thread_pool():
    '''
    重新创建全局线程池
    :return:
    '''
    global thread_pool
    global batch_thread_pool
    global finger_thread_pool
    global lock, batch_lock
    thread_pool.close()
    batch_thread_pool.close()
    finger_thread_pool.close()
    lock = threading.Lock()
    batch_lock = threading.Lock()
    thread_pool = ThreadPool()
    batch_thread_pool = ThreadPool()
    finger_thread_pool = ThreadPool()


def regex_compare(regex, value):
    if re.search(regex, value, re.S | re.I):
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
        if method == regex_compare:
            header_text = ''
            for key, value in data['header'].items():
                header_text += key + ':' + value + '\n'
            if method(val, header_text):
                return True
        else:
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
        if val.lower() == md5_right:
            return True
    return False


def finger_1scan(url: str, finger: dict, data: dict, browser: bool = False):
    '''
    对单个url用单个指纹扫描
    :param url:
    :param finger:
        {
            ...
            app: {

            }
        }
    :param data: 首页的数据 方便匹配首页指纹而不用再次请求
    :param browser: 是否模拟浏览器
    :return:
    '''
    method = finger['method']
    if method == 'md5':
        if finger.get('path', None):
            result=urlsplit(url)
            par_path = result.path[:result.path.rfind('/')] if result.path.startswith('/') else ''
            url = f"{result.scheme}://{result.netloc}{par_path}{finger['path']}"
        data = get_simple_webInfo(url)
        if data['exception']:
            return False
    else:
        if finger.get('path', None):
            result=urlsplit(url)
            par_path = result.path[:result.path.rfind('/')] if result.path.startswith('/') else ''
            url = f"{result.scheme}://{result.netloc}{par_path}{finger['path']}"
            data = get_webInfo(url, browser)
            if data['exception'] or data['status'] == 404:
                return False
    return parse_finger(data, method, finger)


def finger_1scan0(url: str, finger: dict, data: dict, browser: bool = False):
    '''
    对单个url用单个指纹扫描
    :param url:
    :param finger:
        {
            ...
            app: {

            }
        }
    :param data: 首页的数据 方便匹配首页指纹而不用再次请求
    :param browser: 是否模拟浏览器
    :return:
    '''
    return finger, finger_1scan(url, finger, data, browser)

def test_finger(test_finger: dict):
    '''测试指纹是否正确'''
    if 'checkUrls' in test_finger:
        urls = test_finger['checkUrls'] # 测试的url列表
        del test_finger['checkUrls']
    else:
        return True
    tasks = []
    for url in urls:
        url = url['value']
        tasks.append(thread_pool.submit_task(test_url, url, test_finger))
    for future in as_completed(tasks):
        if not future.result():
            return False
    return True

def test_url(url, test_finger: dict):
    data = {}
    if not test_finger.get('path', None):
        data = get_webInfo(url)
        if data['exception']:
            return False
    if not finger_1scan(url, test_finger, data):
        data = get_webInfo(url, True)
        if data['exception']:
            return False
        if not finger_1scan(url, test_finger, data, True):
            return False
        else:
            return True
    else:
        return True

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

def finger_scan0(targer_url: str, fingers: list, setting: dict):
    urls, res = finger_scan(targer_url, fingers, setting)
    return {
        'url': targer_url,
        'result': (
            urls,
            res
        )
    }

def get_fingers(url, fingers, res, browser):
    data = get_webInfo(url, browser)    # 先获取首页内容，方便匹配大量的首页指纹
    if data['exception']:
        return res
    tasks = []
    for finger in fingers:
        if finger.get('path', None):
            tasks.append(finger_thread_pool.submit_task(finger_1scan0, url, finger, data, browser))
        else:
            if finger_1scan(url, finger, data, browser):
                lock.acquire()
                if finger['app']['name'] in res:
                    res[finger['app']['name']]['count'] += 1
                else:
                    res[finger['app']['name']] = finger['app']
                    res[finger['app']['name']]['count'] = 1
                lock.release()
    for future in as_completed(tasks):
        result = future.result()
        finger = result[0]
        if result[1]:
            lock.acquire()
            if finger['app']['name'] in res:
                res[finger['app']['name']]['count'] += 1
            else:
                res[finger['app']['name']] = finger['app']
                res[finger['app']['name']]['count'] = 1
            lock.release()



def finger_batch_scan(target_urls: list, fingers: list, setting: dict):
    '''
    多线程批量扫描指纹
    :param target_urls:
    :param fingers:
    :param setting:
    :return:
    '''
    tasks = []
    res = []
    for target_url in target_urls:
        tasks.append(batch_thread_pool.submit_task(finger_scan0, target_url, fingers, setting))
    for future in as_completed(tasks):
        res.append(future.result())
    return res


if __name__ == '__main__':
    setting = {
        'browser': False,
        'spider': False,
        'only_spider': False
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
