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

from .models import *
from core.util.http_scan import finger_scan, finger_batch_scan

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
        fingers = Finger.objects.filter(is_right=True).order_by('-add_time')
        page = PageNumberPagination()
        page_data = page.paginate_queryset(queryset=fingers, request=request, view=self)
        serializers = FingerSimpleSerializer(page_data, many=True)
        return page.get_paginated_response(serializers.data)


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
        serializer = FingerDetailSerializer(data=request.data)
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
        fingers = Finger.objects.filter().order_by('-add_time')
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
            print()
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
        serializer = FingerDetailAdminSerializer(data=request.data)
        serializer.is_valid()
        data = serializer.data
        fac = Factory(**data['app']['factory'])
        fac.save(force_update=True)
        data['app']['factory'] = fac
        app = App(**data['app'])
        app.save(force_update=True)
        data['app'] = app
        Finger(**data).save(force_update=True, update_fields=['value', 'method', 'location', 'app', 'path'])
        return Response("修改成功")


def background_scan(urls, fingers, setting, id):
    print("process started")
    res = finger_batch_scan(urls, fingers, setting)
    bq = BatchQuery(id=id, status="success", res_json=res)
    bq.save(update_fields=['status', 'res_json'])
    print("process finished")


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
        fingers_model = Finger.objects.filter(is_right=1)
        fingers = FingerQuerySerializer(fingers_model, many=True)

        date = timezone.now()
        batch_query_info = BatchQuery(name=f"scan-{date.year}-{date.month}-{date.day}-{date.hour}-{date.minute}-{date.second}",
                                      user=request.user)
        batch_query_info.save()

        # t = threading.Thread(target=background_scan, args=(urls_l, fingers.data, setting, batch_query_info.id), kwargs={})
        # t.setDaemon(True)
        # t.start()

        pool = ThreadPoolExecutor(1)
        pool.submit(background_scan, urls_l, fingers.data, setting, batch_query_info.id)


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
