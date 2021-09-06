import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stocktracker.settings')

app = Celery('stocktracker')
app.conf.enable_utc = False
app.conf.update(timezone='Asia/Kolkata')

app.config_from_object(settings, namespace='CELERY')

# app.conf.beat_schedule = {
#     'load-stocks-data': {
#         'task': 'mainapp.tasks.update_stock_data',
#         'schedule': 10,
#         'args': (['RELIANCE.NS', 'BAJAJFINSV.NS'],)
#     }
# }

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
