import datetime
import os
from django.db import models
from django.contrib.auth.models import AbstractUser

from django.utils import timezone
# Create your models here.
class User(AbstractUser):
    email = models.CharField(max_length=50, null=True, blank=True, unique=True)
    role = models.CharField(max_length=50, default="user")


    def __str__(self):
        return self.username

class Finger(models.Model):
    '''
    基础指纹信息
    '''
    is_right = models.BooleanField(default=False)    # 是否通过审核
    value = models.CharField(max_length=200, null=True)
    method = models.CharField(max_length=30, null=False)
    location = models.CharField(max_length=30, null=True)
    path = models.CharField(max_length=200, null=True)
    add_time = models.DateTimeField(null=False, default=timezone.now)
    app = models.ForeignKey('App', on_delete=models.CASCADE)
    user = models.ForeignKey('User', on_delete=models.CASCADE, null=True)


class App(models.Model):
    name = models.CharField(max_length=200, null=False, unique=True)
    is_right = models.BooleanField(default=False)    # 是否通过审核
    app_layer = models.CharField(max_length=20, null=True)
    is_open = models.BooleanField(null=True, default=False)
    app_type = models.CharField(max_length=50, null=True)
    app_industry = models.CharField(max_length=100, null=True)
    app_lang = models.CharField(max_length=20, null=True)
    app_desc = models.CharField(max_length=300, null=True, default='')
    factory = models.ForeignKey('Factory', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name

class Factory(models.Model):
    name = models.CharField(max_length=200, null=False, unique=True)
    is_right = models.BooleanField(default=False)    # 是否通过审核
    official_site = models.CharField(max_length=200, null=True, default=None)
    rel_par_company = models.CharField(max_length=200, null=True, default=None)
    rel_son_company = models.CharField(max_length=200, null=True)
    country = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.name


class BatchQuery(models.Model):
    status = models.CharField(max_length=20, null=False, default='scanning')
    add_time = models.DateTimeField(null=False, default=timezone.now)
    name = models.CharField(max_length=200, null=False, unique=True)
    user = models.ForeignKey('User', on_delete=models.CASCADE, null=False)
    res_json = models.JSONField(null=True)
    all_time = models.IntegerField(null=True)
    url_num = models.IntegerField(null=True)

    def __str__(self):
        return self.name

def get_default_headers():
    return {'Accept': 'text/html,application/xhtml+xml,'
                      'application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',}


class Config(models.Model):
    headers = models.JSONField(default=get_default_headers)
    cookies = models.JSONField(default=dict)
    timeout = models.IntegerField(default=10)
    thread_num = models.IntegerField(default=os.cpu_count() * 2 + 4)
