import re
import hashlib
from urllib.parse import urlsplit
from core.util.custom_http import get_webInfo, get_simple_webInfo


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


def finger_scan(url: str, fingers: list):
    '''
    对该url做全指纹扫描
    :param url:
    :param fingers:
    :return:
    '''
    res = {}
    data = get_webInfo(url)
    if data['exception']:
        return res
    for finger in fingers:
        if finger_1scan(url, finger, data):
            if finger['app']['name'] in res:
                res[finger['app']['name']]['count'] += 1
            else:
                res[finger['app']['name']] = finger['app']
                res[finger['app']['name']]['count'] = 1
    # 对结果进行匹配次数的排序
    res = sorted(res.values(), key=lambda x: x['count'], reverse=True)
    return res



if __name__ == '__main__':
    url = "http://www.4399.com"
    fingers = [
        {
            'method': 'keyword',
            'value': '4399',
            'location': 'body',
            'app': {
                'name': 'iis'
            }
        },
        {
            'method': 'md5',
            'value': '7189a6af137bc44bdaf94e0f4c3d8dfe',
            'path': '/favicon.ico',
            'app': {
                'name': 'iis'
            }
        },
        {
            'method': 'md5',
            'value': '7189a6af137bc44bdaf94e0f4c3d8dfe',
            'path': '/favicon.ico',
            'app': {
                'name': 'win'
            }
        }
    ]
    print(finger_scan(url, fingers))
