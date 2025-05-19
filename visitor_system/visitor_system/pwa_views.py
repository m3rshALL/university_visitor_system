"""
Custom views for PWA service worker to handle encoding issues on Windows.
"""
import os
from django.http import HttpResponse
from django.conf import settings

def service_worker_view(request):
    """
    Serve the service worker file with UTF-8 encoding to avoid encoding issues on Windows.
    """
    # Path to the service worker file
    service_worker_path = settings.PWA_SERVICE_WORKER_PATH
    
    if os.path.exists(service_worker_path):
        with open(service_worker_path, 'r', encoding='utf-8') as serviceworker_file:
            return HttpResponse(
                serviceworker_file.read(),
                content_type="application/javascript",
            )
    else:
        # Return an empty service worker if the file doesn't exist
        return HttpResponse("// Service worker not found", content_type="application/javascript")
