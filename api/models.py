from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
class User(AbstractUser):
    email = models.CharField(max_length=50, null=True, blank=True, unique=True)
    finger_num = models.IntegerField(verbose_name="提交的指纹数量", default=0)
    low_num = models.IntegerField(verbose_name="低质量指纹数量", default=0)
    med_num = models.IntegerField(verbose_name="中质量指纹数量", default=0)
    high_num = models.IntegerField(verbose_name="高质量指纹数量", default=0)
    app_num = models.IntegerField(verbose_name="贡献应用数量", default=0)

    def __str__(self):
        return self.username

