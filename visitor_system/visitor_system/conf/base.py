import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parents[2]


SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-placeholder')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = [h for h in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h]

INTERNAL_IPS = ['127.0.0.1']

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'django.contrib.sites',

	'allauth',
	'allauth.account',
	'allauth.socialaccount',
	'allauth.socialaccount.providers.microsoft',

	'django_extensions',
	'django_select2',
	'django_filters',
	'pwa',
	'widget_tweaks',

	'authentication',
	'visitors',
	'departments',
	'notifications',
	'classroom_book',
]


MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'whitenoise.middleware.WhiteNoiseMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'allauth.account.middleware.AccountMiddleware',
	'visitors.middleware.ProfileSetupMiddleware',
]


STORAGES = {
	'default': {
		'BACKEND': 'django.core.files.storage.FileSystemStorage',
	},
	'staticfiles': {
		'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
	},
}


ROOT_URLCONF = 'visitor_system.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [BASE_DIR.parent / 'templates'],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
		},
	},
]

WSGI_APPLICATION = 'visitor_system.wsgi.application'


DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.postgresql',
		'NAME': os.environ.get('POSTGRES_DB', 'visitor_system_db'),
		'USER': os.environ.get('POSTGRES_USER', 'visitor_system_user'),
		'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
		'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
		'PORT': os.environ.get('POSTGRES_PORT', '5432'),
	}
}


AUTH_PASSWORD_VALIDATORS = [
	{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
	{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
	{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
	{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Asia/Almaty'
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = os.path.join(BASE_DIR / 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = (
	'django.contrib.auth.backends.ModelBackend',
	'allauth.account.auth_backends.AuthenticationBackend',
)

SITE_ID = int(os.getenv('DJANGO_SITE_ID', '1'))

LOGIN_URL = '/accounts/login'
LOGIN_REDIRECT_URL = 'employee_dashboard'
LOGOUT_REDIRECT_URL = '/'

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True

client_id = os.getenv('MICROSOFT_CLIENT_ID')
client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
tenant_id = os.getenv('MS_TENANT_ID')

SOCIALACCOUNT_PROVIDERS = {
	'microsoft': {
		'APP': {
			'client_id': client_id,
			'secret': client_secret,
			'key': '',
		},
		'TENANT': tenant_id,
		'AUTH_PARAMS': {'prompt': 'select_account'},
		'SCOPE': ['User.Read'],
	}
}


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() == 'true'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

CSRF_TRUSTED_ORIGINS = [
	*[
		origin for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if origin
	]
]


EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)


CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:{os.environ.get('REDIS_PORT', '6379')}/0")
CELERY_BROKER_TRANSPORT_OPTIONS = {
	'retry_policy': {
		'max_retries': 10,
		'interval_start': 0,
		'interval_step': 0.2,
		'interval_max': 1,
	},
}
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:{os.environ.get('REDIS_PORT', '6379')}/0")
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE


LOGS_DIR = Path(os.getenv('DJANGO_LOGS_DIR', BASE_DIR / 'logs'))
LOGS_DIR.mkdir(parents=True, exist_ok=True)

DJANGO_LOG_TO_STDOUT = os.getenv('DJANGO_LOG_TO_STDOUT', 'False').lower() == 'true'

LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'formatters': {
		'verbose': {
			'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
			'style': '{',
		},
		'simple': {
			'format': '{levelname} {asctime} {module}: {message}',
			'style': '{',
		},
	},
	'handlers': {
		'console': {
			'level': 'DEBUG',
			'class': 'logging.StreamHandler',
			'formatter': 'simple',
		},
		'file': {
			'level': 'INFO',
			'class': 'logging.handlers.RotatingFileHandler',
			'filename': str(LOGS_DIR / 'visitor_system.log'),
			'maxBytes': 1024 * 1024 * 5,
			'backupCount': 5,
			'formatter': 'verbose',
			'encoding': 'utf-8',
		},
	},
	'loggers': {
		'': {
			'handlers': ['console'] if DJANGO_LOG_TO_STDOUT else ['console', 'file'],
			'level': 'INFO',
			'propagate': True,
		},
		'django': {
			'handlers': ['console'] if DJANGO_LOG_TO_STDOUT else ['console', 'file'],
			'level': 'INFO',
			'propagate': False,
		},
		'visitors': {
			'handlers': ['console'] if DJANGO_LOG_TO_STDOUT else ['console', 'file'],
			'level': 'DEBUG',
			'propagate': False,
		},
		'notifications': {
			'handlers': ['console'] if DJANGO_LOG_TO_STDOUT else ['console', 'file'],
			'level': 'DEBUG',
			'propagate': False,
		},
		'celery': {
			'handlers': ['console'] if DJANGO_LOG_TO_STDOUT else ['console', 'file'],
			'level': 'INFO',
			'propagate': True,
		},
		'redis': {
			'handlers': ['console'] if DJANGO_LOG_TO_STDOUT else ['console', 'file'],
			'level': 'WARNING',
			'propagate': False,
		},
		'django_redis': {
			'handlers': ['console'] if DJANGO_LOG_TO_STDOUT else ['console', 'file'],
			'level': 'WARNING',
			'propagate': False,
		},
	},
}


CACHES = {
	'default': {
		'BACKEND': 'django_redis.cache.RedisCache',
		'LOCATION': os.getenv('REDIS_CACHE_URL', 'redis://127.0.0.1:6379/1'),
		'OPTIONS': {
			'CLIENT_CLASS': 'django_redis.client.DefaultClient',
			'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
			'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
			'MAX_ENTRIES': int(os.getenv('DJANGO_CACHE_MAX_ENTRIES', '50000')),
			'TIMEOUT': int(os.getenv('DJANGO_CACHE_TIMEOUT', str(60 * 15))),
		},
		'KEY_PREFIX': os.getenv('DJANGO_CACHE_KEY_PREFIX', 'visitor_system_cache'),
	}
}


# PWA
PWA_APP_NAME = 'AITU Visitor Pass'
PWA_APP_DESCRIPTION = 'Система управления пропусками для Astana IT University'
PWA_APP_THEME_COLOR = '#206bc4'
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_ORIENTATION = 'any'
PWA_APP_START_URL = '/'
PWA_APP_SCOPE = '/'
PWA_APP_ICONS = [
	{'src': '/static/img/icons/icon-72x72.png', 'sizes': '72x72'},
	{'src': '/static/img/icons/icon-96x96.png', 'sizes': '96x96'},
	{'src': '/static/img/icons/icon-128x128.png', 'sizes': '128x128'},
	{'src': '/static/img/icons/icon-144x144.png', 'sizes': '144x144'},
	{'src': '/static/img/icons/icon-152x152.png', 'sizes': '152x152'},
	{'src': '/static/img/icons/icon-192x192.png', 'sizes': '192x192'},
	{'src': '/static/img/icons/icon-384x384.png', 'sizes': '384x384'},
	{'src': '/static/img/icons/icon-512x512.png', 'sizes': '512x512'},
]
PWA_APP_APPLE_TOUCH_ICON = '/static/img/icons/apple-touch-icon.png'
PWA_APP_SPLASH_SCREEN = [
	{
		'src': '/static/img/icons/splash-640x1136.png',
		'media': '(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)'
	}
]
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static/js', 'serviceworker.js')
PWA_APP_FETCH_URL_PATTERNS = []
PWA_SERVICE_WORKER_EXCLUDE_URLS = []
PWA_DEBUG = DEBUG
PWA_MANIFEST_FILENAME = 'manifest.json'


