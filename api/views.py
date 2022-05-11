from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .csrf import CsrfExemptSessionAuthentication
from .serializers import *
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import UserPassesTestMixin

from .models import *
from core.util.http_scan import finger_scan
# Create your views here.



class UserRegisterView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    def post(self, request, format=None):
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
        logout(request)
        return Response("退出成功", status=status.HTTP_200_OK)


class FactoryMultiHandle(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    def get(self, request):
        '''
        获取所有的厂商信息
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
        获取所有应用的信息
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
        分页时间降序获取所有指纹的信息
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
        serializer = FingerDetailSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            print(request.GET.get('app_id', None))
            # 已存在的应用
            if request.GET.get('app_id', None) != None:
                app = App.objects.get(id=request.GET['app_id'])
                finger = Finger.objects.create(**data, app=app)
                return Response(FingerDetailSerializer(finger).data)
            # 已存在的厂商，应用不存在
            elif request.GET.get('factory_id', None) != None:
                fac = Factory.objects.get(id=request.GET['factory_id'])
                app = App.objects.create(**data['app'], factory=fac)
                data['app'] = app
                finger = Finger.objects.create(**data)
                return Response(FingerDetailSerializer(finger).data)
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
        fingers_model = Finger.objects.filter(is_right=1)
        fingers = FingerQuerySerializer(fingers_model, many=True)
        res = finger_scan(url, fingers.data)
        return Response(res)


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
        Finger(**data).save(force_update=True)
        return Response("修改成功")
