from celery import Celery
import os
import ssl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL") or 'redis://localhost:6379/0'

ssl_config = {
    'ssl_cert_reqs': ssl.CERT_NONE  
}


if REDIS_URL.startswith("rediss://"):
    celery_app = Celery(
        'code_review',
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=['app.tasks']
    )
    celery_app.conf.broker_use_ssl = ssl_config
    celery_app.conf.redis_backend_use_ssl = ssl_config
else:
    # Non-secure Redis connection
    celery_app = Celery(
        'code_review',
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=['app.tasks']
    )
