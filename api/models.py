import datetime

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
    app_desc = models.CharField(max_length=300, null=True, default=None)
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

    def __str__(self):
        return self.name


