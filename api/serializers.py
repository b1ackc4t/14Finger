from rest_framework import serializers
from .models import User
import re

class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email')

    def validate_username(self, value):
        """
        检查用户名是否合格
        :param value:
        :return:
        """
        if len(value) < 2 or len(value) > 30:
            raise serializers.ValidationError("用户名不合格")
        return value

    def validate_email(self, value):
        """
        检查用户名是否合格
        :param value:
        :return:
        """
        if not re.match(r'^(.+)\@(.+)\.(.+)$', value):
            raise serializers.ValidationError("邮箱不合格")
        return value

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')