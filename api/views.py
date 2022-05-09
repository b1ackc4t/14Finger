from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from .csrf import CsrfExemptSessionAuthentication
from .serializers import UserRegisterSerializer, UserSimpleSerializer
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password

from .models import User
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
            'id': request.user.id
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
