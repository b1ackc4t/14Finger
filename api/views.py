from concurrent.futures import ThreadPoolExecutor

from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .csrf import CsrfExemptSessionAuthentication
from .serializers import *
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import FileResponse
from django.db.models import Q

from .models import *
from core.util.http_scan import finger_scan, finger_batch_scan, recreate_thread_pool, test_finger
import _14Finger.settings as setting

import json
import threading
import time
import io
# Create your views here.



class UserRegisterView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    def post(self, request, format=None):
        '''
        普通用户注册
        :param request:
        :param format:
        :return:
        '''
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            User.objects.create_user(username=serializer.validated_data['username'],
                                     password=serializer.validated_data['password'],
                                     email=serializer.validated_data['email'])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """
        获取当前登录的用户
        :param request:
        :return:
        """
        res = {
            'username': request.user.username,
            'id': request.user.id,
            'role': request.user.role
        }
        return Response(res)

class UserLogin(APIView):
    # 关闭csrf
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def post(self, request):
        '''
        使用用户名或者邮箱登录
        :param request:
        :return:
        '''
        username = request.data.get('username', "")
        password = request.data.get('password', "")
        email = request.data.get('email', "")
        user = authenticate(request, username=username, password=password, email=email)
        if user:
            login(request, user)
            return Response("登录成功", status=status.HTTP_200_OK)
        else:
            return Response("账户或密码错误", status=status.HTTP_401_UNAUTHORIZED)


class UserLogout(APIView):
    # 关闭csrf
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    def get(self, request):
        '''
        退出登录状态
        :param request:
        :return:
        '''
        logout(request)
        return Response("退出成功", status=status.HTTP_200_OK)


class UserRankView(APIView):
    # 关闭csrf
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    def get(self, request):
        users = User.objects.all()
        serializers = UserDetailSerializer(users, many=True)
        data = serializers.data
        for user in data:
            fingers = Finger.objects.filter(user_id=user['id']).filter(is_right=True)
            user['finger_num'] = fingers.count()
            s = set()
            for finger in fingers:
                app_id = finger.app.id
                if app_id not in s:
                    s.add(app_id)
            user['app_num'] = len(s)
        data = sorted(data, key=lambda x: x['app_num'], reverse=True)
        r = 1
        for user in data:
            user['rank'] = r
            r += 1
        return Response(data)


class UserAdminView(APIView):
    # 关闭csrf
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    def test_func(self):
        return self.request.user.role == 'admin'

    def get(self, request):
        '''
        管理员分页获取用户信息
        :param request:
        :return:
        '''
        if request.GET.get('id', None) == None:
            key = request.GET.get('key', "")
            value = request.GET.get('value', "")
            users = User.objects.all()
            if key == 'username':
                users = users.filter(username__icontains=value)
            elif key == 'email':
                users = users.filter(email__icontains=value)
            elif key == 'role':
                users = users.filter(role__icontains=value)
            users = users.order_by('id')
            page = PageNumberPagination()
            page_data = page.paginate_queryset(queryset=users, request=request, view=self)
            serializers = UserDetailSerializer(page_data, many=True)
            return page.get_paginated_response(serializers.data)
        else:
            user = User.objects.get(id=request.GET['id'])
            serializer = UserDetailSerializer(user)
            return Response(serializer.data)

    def post(self, request):
        '''
        修改用户信息
        :param request:
        :return:
        '''
        data = request.data
        user = User(id=data['id'], username=data['username'], email=data['email'], role=data['role'])
        if data.get('password', None) != None:
            if data['password']:
                user.set_password(data.get('password', None))
                user.save(force_update=True)
                return Response("修改成功")
        user.save(force_update=True, update_fields=['username', 'email', 'role'])
        return Response("修改成功")

    def delete(self, request):
        id = request.GET['id']
        user = User(id=id)
        user.delete()
        return Response("删除成功")


class FactoryMultiHandle(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    def get(self, request):
        '''
        获取所有通过审核的厂商信息
        :param request:
        :return:
        '''
        factorys = Factory.objects.filter(is_right=True)
        serializers = FactorySimpleSerializer(factorys, many=True)
        return Response(serializers.data, status=status.HTTP_200_OK)


class AppMultiHandle(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    def get(self, request):
        '''
        获取所有通过审核的应用的信息
        :param request:
        :return:
        '''
        apps = App.objects.filter(is_right=True)
        serializers = AppSimpleSerializer(apps, many=True)
        return Response(serializers.data, status=status.HTTP_200_OK)


class FingerMultiHandle(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def get(self, request):
        '''
        分页时间降序获取所有通过审核的指纹的信息
        :param request:
        :return:
        '''
        app_type = request.GET.get('app_type', None)
        key = request.GET.get('key', "")
        value = request.GET.get('value', "")
        fingers = Finger.objects.filter(is_right=True)
        if app_type:
            fingers = fingers.filter(app__app_type__icontains=app_type)
        if key == 'app_name':
            fingers = fingers.filter(app__name__icontains=value)
        elif key == 'fac_name':
            fingers = fingers.filter(app__factory__name__icontains=value)
        elif key == 'app_desc':
            fingers = fingers.filter(app__app_desc__icontains=value)
        else:
            fingers = fingers.filter(Q(app__name__icontains=value)|
                                     Q(app__factory__name__icontains=value)|
                                     Q(app__app_desc__icontains=value))
        fingers = fingers.order_by('-add_time')
        page = PageNumberPagination()
        page_data = page.paginate_queryset(queryset=fingers, request=request, view=self)
        serializers = FingerSimpleSerializer(page_data, many=True)
        return page.get_paginated_response(serializers.data)


class FingerCheckHandle(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def test_func(self):
        return self.request.user.is_authenticated

    def post(self, request):
        '''
        测试指纹
        :param request:
        :return:
        '''
        if not test_finger(request.data):
            return Response("测试url匹配指纹失败，指纹可能是错误的！", status=status.HTTP_417_EXPECTATION_FAILED)
        return Response("测试通过！")


class FingerSingleHandle(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def test_func(self):
        return self.request.user.is_authenticated

    def post(self, request):
        '''
        用户提交指纹
        :param request:
        :return:
        '''
        serializer = FingerDetailSerializer(data=clear_data(request.data))
        if serializer.is_valid():
            data = serializer.validated_data
            data['user'] = request.user
            # 已存在的应用
            if request.GET.get('app_id', None) != None:
                app = App.objects.get(id=request.GET['app_id'])
                finger = Finger.objects.create(**data, app=app)
            # 已存在的厂商，应用不存在
            elif request.GET.get('factory_id', None) != None:
                fac = Factory.objects.get(id=request.GET['factory_id'])
                app = App.objects.create(**data['app'], factory=fac)
                data['app'] = app
                finger = Finger.objects.create(**data)
            # 厂商和应用都不存在
            else:
                fac = Factory.objects.create(**data['app']['factory'])
                data['app']['factory'] = fac
                app = App.objects.create(**data['app'])
                data['app'] = app
                finger = Finger.objects.create(**data)
            return Response(FingerDetailSerializer(finger).data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def clear_data(data: dict):
    if 'path' in data:
        if not data['path']:
            del data['path']
    if 'app' in data:
        if 'app_desc' in data['app']:
            if not data['app']['app_desc']:
                del data['app']['app_desc']
    return data

class FingerSuperSubmitHandle(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def test_func(self):
        return self.request.user.role == 'admin'

    def post(self, request):
        '''
        管理员免审核提交指纹
        :param request:
        :return:
        '''

        serializer = FingerDetailSerializer(data=clear_data(request.data))
        if serializer.is_valid():
            data = serializer.validated_data
            data['user'] = request.user
            # 已存在的应用
            if request.GET.get('app_id', None) != None:
                app = App.objects.get(id=request.GET['app_id'])
                finger = Finger.objects.create(**data, app=app)
            # 已存在的厂商，应用不存在
            elif request.GET.get('factory_id', None) != None:
                fac = Factory.objects.get(id=request.GET['factory_id'])
                app = App.objects.create(**data['app'], factory=fac)
                data['app'] = app
                finger = Finger.objects.create(**data)
            # 厂商和应用都不存在
            else:
                fac = Factory.objects.create(**data['app']['factory'])
                data['app']['factory'] = fac
                app = App.objects.create(**data['app'])
                data['app'] = app
                finger = Finger.objects.create(**data)
            finger = Finger(id=finger.id, is_right=True)
            finger.save(update_fields=['is_right'])
            appid = Finger.objects.get(id=finger.id).app.id
            app = App(id=appid, is_right=True)
            app.save(update_fields=['is_right'])
            facid = App.objects.get(id=app.id).factory.id
            fac = Factory(id=facid, is_right=True)
            fac.save(update_fields=['is_right'])
            return Response(FingerDetailSerializer(finger).data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FingerSingleQuery(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def test_func(self):
        return self.request.user.is_authenticated

    def post(self, request):
        '''
        查询单个url指纹的接口
        :param request:
        :return:
        '''
        url = request.POST['url']   # 获取单个url
        setting = json.loads(request.POST['setting'])
        fingers_model = Finger.objects.filter(is_right=1)
        if setting.get('only_home', True):
            fingers_model = fingers_model.filter(Q(path=None)|Q(path=''))
        fingers = FingerQuerySerializer(fingers_model, many=True)
        urls, res = finger_scan(url, fingers.data, setting)
        if res:
            return Response({'spider': urls, 'finger': res})
        else:
            return Response({'spider': urls, 'finger': []})


class FingerMultiAdminHandle(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def test_func(self):
        return self.request.user.role == 'admin'

    def get(self, request):
        app_type = request.GET.get('app_type', None)
        key = request.GET.get('key', "")
        value = request.GET.get('value', "")
        fingers = Finger.objects.all()
        if app_type:
            fingers = fingers.filter(app__app_type__icontains=app_type)
        if key == 'app_name':
            fingers = fingers.filter(app__name__icontains=value)
        elif key == 'fac_name':
            fingers = fingers.filter(app__factory__name__icontains=value)
        elif key == 'app_desc':
            fingers = fingers.filter(app__app_desc__icontains=value)
        elif key == 'not_right':
            fingers = fingers.filter(is_right=False)
            fingers = fingers.filter(Q(app__name__icontains=value)|
                                     Q(app__factory__name__icontains=value)|
                                     Q(app__app_desc__icontains=value))
        else:
            fingers = fingers.filter(Q(app__name__icontains=value)|
                                     Q(app__factory__name__icontains=value)|
                                     Q(app__app_desc__icontains=value))
        fingers = fingers.order_by('-add_time')
        page = PageNumberPagination()
        page_data = page.paginate_queryset(queryset=fingers, request=request, view=self)
        serializers = FingerSimpleAdminSerializer(page_data, many=True)
        return page.get_paginated_response(serializers.data)

    def post(self, request):
        '''
        审核指纹操作
        :param request:
        :return:
        '''
        action = request.POST['action']
        id = request.POST['id']
        if action == 'pass':
            finger = Finger(id=id, is_right=True)
            finger.save(update_fields=['is_right'])
            appid = Finger.objects.get(id=finger.id).app.id
            app = App(id=appid, is_right=True)
            app.save(update_fields=['is_right'])
            facid = App.objects.get(id=app.id).factory.id
            fac = Factory(id=facid, is_right=True)
            fac.save(update_fields=['is_right'])
        elif action == 'cancel':
            finger = Finger(id=id, is_right=False)
            finger.save(update_fields=['is_right'])
        elif action == 'delete':
            finger = Finger(id=id)
            appid = Finger.objects.get(id=finger.id).app.id
            finger.delete()
            if Finger.objects.filter(app_id=appid).count() == 0:
                app = App(id=appid)
                facid = App.objects.get(id=app.id).factory.id
                app.delete()
                if App.objects.filter(factory_id=facid).count() == 0:
                    Factory(id=facid).delete()
        return Response('操作成功')


class FingerSingleAdminHandle(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def test_func(self):
        return self.request.user.role == 'admin'

    def get(self, request):
        id = request.GET['id']
        finger = Finger.objects.get(id=id)
        serializer = FingerDetailAdminSerializer(finger)
        return Response(serializer.data)

    def post(self, request):
        '''
        管理员修改指纹信息
        :param request:
        :return:
        '''
        serializer = FingerDetailAdminSerializer(data=clear_data(request.data))
        serializer.is_valid()
        data = serializer.data
        fac = Factory(**data['app']['factory'])
        fac.save(force_update=True, update_fields=['name', 'official_site', 'rel_par_company', 'rel_son_company', 'country'])
        data['app']['factory'] = fac
        app = App(**data['app'])
        app.save(force_update=True, update_fields=['name', 'app_layer', 'is_open', 'app_type', 'app_industry', 'app_lang', 'app_desc', 'factory'])
        data['app'] = app
        Finger(**data).save(force_update=True, update_fields=['value', 'method', 'location', 'app', 'path'])
        return Response("修改成功")


def background_scan(urls, setting, id):
    fingers_model = Finger.objects.filter(is_right=1)
    if setting.get('only_home', True):
        fingers_model = fingers_model.filter(Q(path=None)|Q(path=''))
    fingers = FingerQuerySerializer(fingers_model, many=True)
    start = timezone.now()
    res = finger_batch_scan(urls, fingers.data, setting)
    end = timezone.now()
    consume = (end - start).seconds
    bq = BatchQuery(id=id, status="success", res_json=res, all_time=consume)
    bq.save(update_fields=['status', 'res_json', 'all_time'])


class FingerBatchQuery(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def test_func(self):
        return self.request.user.is_authenticated

    def get(self, request):
        '''
        查询用户所有的任务，管理员能查所有任务
        :param request:
        :return:
        '''
        if self.request.user.role == 'admin':
            batch_querys = BatchQuery.objects.all().order_by('-add_time')
        else:
            id = self.request.user.id
            batch_querys = BatchQuery.objects.filter(user_id=id).order_by('-add_time')
        serializers = BatchQuerySerializer(batch_querys, many=True)
        return Response(serializers.data)

    def post(self, request):
        '''
        查询多个url指纹的接口
        :param request:
        :return:
        '''
        urls: str = request.POST['urls']   # 获取单个url
        urls_l = [url.strip() for url in urls.split('\n')]
        setting = json.loads(request.POST['setting'])

        date = timezone.now()
        batch_query_info = BatchQuery(name=f"scan-{date.year}-{date.month}-{date.day}-{date.hour}-{date.minute}-{date.second}",
                                      user=request.user, url_num=len(urls_l))
        batch_query_info.save()

        # t = threading.Thread(target=background_scan, args=(urls_l, fingers.data, setting, batch_query_info.id), kwargs={})
        # t.setDaemon(True)
        # t.start()

        pool = ThreadPoolExecutor(1)
        pool.submit(background_scan, urls_l, setting, batch_query_info.id)


        return Response("任务添加成功")


class FingerBatchAction(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def test_func(self):
        return self.request.user.is_authenticated

    def get(self, request):
        '''
        下载批量扫描结果
        :param request:
        :return:
        '''
        id = request.GET['id']
        batch_query = BatchQuery.objects.get(id=id)
        d = batch_query.res_json
        f = io.BytesIO(json.dumps(d, indent=4, ensure_ascii=False).encode('utf-8'))
        response = FileResponse(f)
        response['Content-Type'] = 'application/octet-stream'
        filename = 'attachment; filename=' + '{}.json'.format(batch_query.name)
        # TODO 设置文件名的包含中文编码方式
        response['Content-Disposition'] = filename.encode('utf-8', 'ISO-8859-1')
        return response

    def delete(self, request):
        '''
        删除某个扫描任务
        :param request:
        :return:
        '''
        id = request.GET['id']
        batch_query = BatchQuery(id=id)
        batch_query.delete()
        return Response("删除成功")


class ConfigView(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    def test_func(self):
        return self.request.user.role == 'admin'

    def get(self, request):
        is_default = request.GET.get('is_default', None)
        if is_default:
            config = {
                'rad_config': """exec_path: ""                     # 启动chrome的路径
disable_headless: false           # 禁用无头模式
force_sandbox: false              # 强制开启sandbox；为 false 时默认开启沙箱，但在容器中会关闭沙箱。为true时强制启用沙箱，可能导致在docker中无法使用。
enable_image: false               # 启用图片显示
parent_path_detect: true          # 是否启用父目录探测功能
proxy: ""                         # 代理配置
user_agent: ""                    # 请求user-agent配置
domain_headers:                   # 请求头配置:[]{domain,map[headerKey]HeaderValue}
- domain: '*'                     # 为哪些域名设置header，glob语法
  headers: {}                     # 请求头，map[key]value
max_depth: 10                     # 最大页面深度限制
navigate_timeout_second: 10       # 访问超时时间，单位秒
load_timeout_second: 10           # 加载超时时间，单位秒
retry: 0                          # 页面访问失败后的重试次数
page_analyze_timeout_second: 300  # 页面分析超时时间，单位秒
max_interactive: 10             # 单个页面最大交互次数
max_interactive_depth: 10         # 页面交互深度限制
max_page_concurrent: 10           # 最大页面并发（不大于10）
max_page_visit: 100              # 总共允许访问的页面数量
max_page_visit_per_site: 10     # 每个站点最多访问的页面数量
element_filter_strength: 0        # 过滤同站点相似元素强度，1-7取值，强度逐步增大，为0时不进行跨页面元素过滤
new_task_filter_config:           # 检查某个链接是否应该被加入爬取队列
  hostname_allowed: []            # 允许访问的 Hostname，支持格式如 t.com、*.t.com、1.1.1.1、1.1.1.1/24、1.1-4.1.1-8
  hostname_disallowed: []         # 不允许访问的 Hostname，支持格式如 t.com、*.t.com、1.1.1.1、1.1.1.1/24、1.1-4.1.1-8
  port_allowed: []                # 允许访问的端口, 支持的格式如: 80、80-85
  port_disallowed: []             # 不允许访问的端口, 支持的格式如: 80、80-85
  path_allowed: []                # 允许访问的路径，支持的格式如: test、*test*
  path_disallowed: []             # 不允许访问的路径, 支持的格式如: test、*test*
  query_key_allowed: []           # 允许访问的 Query Key，支持的格式如: test、*test*
  query_key_disallowed: []        # 不允许访问的 Query Key, 支持的格式如: test、*test*
  fragment_allowed: []            # 允许访问的 Fragment, 支持的格式如: test、*test*
  fragment_disallowed: []         # 不允许访问的 Fragment, 支持的格式如: test、*test*
  post_key_allowed: []            # 允许访问的 Post Body 中的参数, 支持的格式如: test、*test*
  post_key_disallowed: []         # 不允许访问的 Post Body 中的参数, 支持的格式如: test、*test*
request_send_filter_config:       # 检查某个请求是否应该被发送
  hostname_allowed: []            # 允许访问的 Hostname，支持格式如 t.com、*.t.com、1.1.1.1、1.1.1.1/24、1.1-4.1.1-8
  hostname_disallowed: []         # 不允许访问的 Hostname，支持格式如 t.com、*.t.com、1.1.1.1、1.1.1.1/24、1.1-4.1.1-8
  port_allowed: []                # 允许访问的端口, 支持的格式如: 80、80-85
  port_disallowed: []             # 不允许访问的端口, 支持的格式如: 80、80-85
  path_allowed: []                # 允许访问的路径，支持的格式如: test、*test*
  path_disallowed: []             # 不允许访问的路径, 支持的格式如: test、*test*
  query_key_allowed: []           # 允许访问的 Query Key，支持的格式如: test、*test*
  query_key_disallowed: []        # 不允许访问的 Query Key, 支持的格式如: test、*test*
  fragment_allowed: []            # 允许访问的 Fragment, 支持的格式如: test、*test*
  fragment_disallowed: []         # 不允许访问的 Fragment, 支持的格式如: test、*test*
  post_key_allowed: []            # 允许访问的 Post Body 中的参数, 支持的格式如: test、*test*
  post_key_disallowed: []         # 不允许访问的 Post Body 中的参数, 支持的格式如: test、*test*
request_output_filter_config:     # 检查某个请求是否应该被输出
  hostname_allowed: []            # 允许访问的 Hostname，支持格式如 t.com、*.t.com、1.1.1.1、1.1.1.1/24、1.1-4.1.1-8
  hostname_disallowed: []         # 不允许访问的 Hostname，支持格式如 t.com、*.t.com、1.1.1.1、1.1.1.1/24、1.1-4.1.1-8
  port_allowed: []                # 允许访问的端口, 支持的格式如: 80、80-85
  port_disallowed: []             # 不允许访问的端口, 支持的格式如: 80、80-85
  path_allowed: []                # 允许访问的路径，支持的格式如: test、*test*
  path_disallowed: []             # 不允许访问的路径, 支持的格式如: test、*test*
  query_key_allowed: []           # 允许访问的 Query Key，支持的格式如: test、*test*
  query_key_disallowed: []        # 不允许访问的 Query Key, 支持的格式如: test、*test*
  fragment_allowed: []            # 允许访问的 Fragment, 支持的格式如: test、*test*
  fragment_disallowed: []         # 不允许访问的 Fragment, 支持的格式如: test、*test*
  post_key_allowed: []            # 允许访问的 Post Body 中的参数, 支持的格式如: test、*test*
  post_key_disallowed: []         # 不允许访问的 Post Body 中的参数, 支持的格式如: test、*test*""",
                'headers': get_default_headers(),
                'cookies': {},
                'timeout': 10,
                'thread_num': os.cpu_count() * 2 + 4,
            }
            return Response(config)
        else:
            config = Config.objects.get(pk=1)
            serializer = ConfigSerializer(config)
            data = serializer.data
            s = open(os.path.join(setting.BASE_DIR, 'core', 'util', 'rad_config.yml'), 'r', encoding='utf-8').read()
            data['rad_config'] = s
            return Response(data)

    def post(self, request):
        '''
        修改扫描配置
        :param request:
        :return:
        '''
        data = request.data
        data['headers'] = json.loads(data['headers'])
        data['cookies'] = json.loads(data['cookies'])
        rad_f = open(os.path.join(setting.BASE_DIR, 'core', 'util', 'rad_config.yml'), 'w', encoding='utf-8')
        rad_f.write(data['rad_config'])
        rad_f.close()
        origin = Config.objects.get(pk=1)
        if origin.thread_num != data['thread_num']:
            recreate_thread_pool()
        del data['rad_config']
        config = Config(id=1, **data)
        config.save(force_update=True)
        return Response("修改成功")


class FingerModifyAdminHandle(UserPassesTestMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def test_func(self):
        return self.request.user.role == 'admin'

    def get(self, request):
        value = request.GET['value']
        fingers = Finger.objects.filter(value=value)
        for fin in fingers:
            fin.delete()
        return Response("操作成功")

    def post(self, request):
        id = request.POST['id']
        app_id = request.POST.get('app_id', None)
        fac_id = request.POST.get('fac_id', None)

        finger = Finger.objects.get(id=id)
        if app_id:
            if int(app_id) != finger.app.id:
                old_app_id = finger.app.id
                finger.app_id = app_id
                finger.save(force_update=True)
                if Finger.objects.filter(app_id=old_app_id).count() == 0:
                    app = App(id=old_app_id)
                    facid = App.objects.get(id=app.id).factory.id
                    app.delete()
                    if App.objects.filter(factory_id=facid).count() == 0:
                        Factory(id=facid).delete()
            return Response("修改成功")
        elif fac_id:
            if int(fac_id) != finger.app.factory.id:
                old_fac_id = finger.app.factory.id
                finger.app.factory_id = fac_id
                finger.app.save(force_update=True)
                if App.objects.filter(factory_id=old_fac_id).count() == 0:
                    Factory(id=old_fac_id).delete()
            return Response("修改成功")
        else:
            return Response("空")
