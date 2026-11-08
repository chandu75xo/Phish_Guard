import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'detection_of_phishing_websites.settings')

application = get_wsgi_application()

# Load the pre-trained artifact into this worker's RAM. Never train at startup.
# A missing/incompatible artifact fails startup with an actionable error.
from ml_engine import load_models
load_models()
