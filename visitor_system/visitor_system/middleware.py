from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response.setdefault('Permissions-Policy',
                            "geolocation=(), microphone=(), camera=(), "
                            "interest-cohort=()")
        if getattr(settings, 'SECURE_REFERRER_POLICY', None):
            response.setdefault('Referrer-Policy', settings.SECURE_REFERRER_POLICY)
        return response
