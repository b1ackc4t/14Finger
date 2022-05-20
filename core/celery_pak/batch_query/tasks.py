from django.db.models import Q
from django.utils import timezone

from api.serializers import FingerQuerySerializer
from core.celery_pak.main import app
import time
from api.models import Finger, BatchQuery
from core.util.http_scan import finger_batch_scan
from django.db import connection

@app.task
def batch_query_bak(urls, setting, id):
    fingers_model = Finger.objects.filter(is_right=1)
    if setting.get('only_home', True):
        fingers_model = fingers_model.filter(Q(path=None)|Q(path=''))
    fingers = FingerQuerySerializer(fingers_model, many=True)
    connection.close()
    start = timezone.now()
    res = finger_batch_scan(urls, fingers.data, setting)
    end = timezone.now()
    consume = (end - start).seconds
    bq = BatchQuery(id=id, status="success", res_json=res, all_time=consume)
    bq.save(update_fields=['status', 'res_json', 'all_time'])
    connection.close()


