import os
import subprocess

current_path = os.path.dirname(__file__)

import platform

rad_file = 'rad.exe'
if platform.system().lower() == 'windows':
    rad_file = 'rad.exe'
elif platform.system().lower() == 'linux':
    rad_file = 'rad'

def crawl_site(url: str) -> list:
    '''
    调用rad爬取站点
    :param url: 爬取到的url列表
    :return:
    '''
    cmd = f"{os.path.join(current_path, 'rad.exe')} -c {os.path.join(current_path, 'rad_config.yml')} -t {url} "
    p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE)
    out,err = p.communicate()
    res = []
    for line in out.splitlines():
        s = line.decode()
        if s.startswith('GET') or s.startswith('POST'):
            res.append(s[s.find(' ') + 1:])
    p.wait()
    return res


if __name__ == '__main__':
    print(len(crawl_site('https://typemill.net/')))