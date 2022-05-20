import os
from celery import Celery

# 加载Django的配置文件
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '_14Finger.settings')

app = Celery('14Finger')  #这个可以随便取，一般为项目名

# 加载celery的配置
app.config_from_object('_14Finger.settings', namespace='CELERY')

app.autodiscover_tasks(['core.celery_pak.batch_query'])

# 启动celery
# celery -A core.celery_pak.main worker --loglevel=info