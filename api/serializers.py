from rest_framework import serializers
from .models import *
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

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ('password',)

class FactorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factory
        fields = ('id', 'name')


class FactoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factory
        fields = ('id', 'name', 'official_site', 'rel_par_company', 'rel_son_company', 'country')
        extra_kwargs = {
            'name': {'required': False}
        }
        # read_only_fields = ('name',)



class AppSimpleSerializer(serializers.ModelSerializer):
    factory = FactorySimpleSerializer()
    class Meta:
        model = App
        fields = ('id', 'name', 'app_type', 'app_desc', 'factory')
        depth = 1

class AppEasySerializer(serializers.ModelSerializer):
    class Meta:
        model = App
        fields = ('id', 'name')

class AppDetailSerializer(serializers.ModelSerializer):
    factory = FactoryDetailSerializer(required=False)
    class Meta:
        model = App
        fields = ('id', 'name', 'app_layer', 'is_open', 'app_type', 'app_industry', 'app_lang', 'app_desc', 'factory')
        depth = 1
        extra_kwargs = {
            'app_type': {'required': True}
        }
        # read_only_fields = ('name',)



class FingerSimpleSerializer(serializers.ModelSerializer):
    app = AppSimpleSerializer()
    class Meta:
        model = Finger
        fields = ('id', 'app', 'add_time')
        depth = 1


class FingerDetailSerializer(serializers.ModelSerializer):
    app = AppDetailSerializer(required=False)
    class Meta:
        model = Finger
        fields = ('id', 'app', 'add_time', 'path', 'value', 'method', 'location')
        depth = 1
        extra_kwargs = {
            'value': {'required': True},
        }

class AppQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = App
        fields = ('id', 'name', 'app_layer', 'is_open', 'app_type', 'app_industry', 'app_lang', 'app_desc')
        depth = 1
        extra_kwargs = {
            'app_type': {'required': True}
        }

class FingerQuerySerializer(serializers.ModelSerializer):
    app = AppQuerySerializer()
    class Meta:
        model = Finger
        fields = ('id', 'app', 'path', 'value', 'method', 'location')
        depth = 1
        extra_kwargs = {
            'value': {'required': True}
        }


class FingerSimpleAdminSerializer(serializers.ModelSerializer):
    app = AppSimpleSerializer()
    class Meta:
        model = Finger
        fields = ('id', 'app', 'add_time', 'is_right', 'user')
        depth = 1


class FingerDetailAdminSerializer(serializers.ModelSerializer):
    app = AppDetailSerializer()
    class Meta:
        model = Finger
        fields = '__all__'
        depth = 1
        extra_kwargs = {'id': {'read_only': False}}
        read_only_fields = ('add_time', 'user')


class BatchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = BatchQuery
        exclude = ('res_json',)
        depth = 1


class ConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Config
        fields = '__all__'