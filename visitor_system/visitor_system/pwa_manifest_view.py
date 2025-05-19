"""
Custom views for PWA manifest to handle syntax issues.
"""
import os
import json
from django.http import HttpResponse, JsonResponse
from django.conf import settings

def manifest_json_view(request):
    """
    Serve the manifest.json file with proper content type and encoding
    """
    # Path to our custom manifest.json file
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as manifest_file:
            manifest_data = json.load(manifest_file)
            return JsonResponse(manifest_data)
    else:
        # Fallback: generate a simple valid manifest
        manifest_data = {
            "name": "AITU Visitor Pass",
            "short_name": "Visitor Pass",
            "description": "Система управления пропусками для Astana IT University",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#206bc4",
            "orientation": "any",
            "scope": "/",
            "icons": [
                {
                    "src": "/static/img/icons/icon-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/img/icons/icon-512x512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable"
                }
            ]
        }
        return JsonResponse(manifest_data)
