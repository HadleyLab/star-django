"""
Django settings for stargeo project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

INTERNAL_IPS = ['127.0.0.1']

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', '').lower() == 'true'

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_jinja',
    'django_jinja.contrib._humanize',
    'bootstrapform_jinja',
    'datatableview',
    'rest_framework',
    'rest_framework_swagger',
    'rest_framework.authtoken',
    'cacheops',
    'oauth2access',

    'core',
    'legacy',
    'tags',
    'analysis',
    'api',
)
if DEBUG:
    INSTALLED_APPS += ('debug_toolbar', 'django_extensions')
os.environ['WERKZEUG_DEBUG_PIN'] = 'off'

MIGRATION_MODULES = {
    'auth': 'stargeo.auth_migrations'
}

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)
if DEBUG:
    MIDDLEWARE = ('debug_toolbar.middleware.DebugToolbarMiddleware',) + MIDDLEWARE

ROOT_URLCONF = 'stargeo.urls'
LOGIN_REDIRECT_URL = '/'

WSGI_APPLICATION = 'stargeo.wsgi.application'


AUTH_USER_MODEL = 'core.User'

SILENCED_SYSTEM_CHECKS = ['fields.W342']

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

import dj_database_url
import os

DATABASES = {
    'default': dj_database_url.config(),
}


REDIS = {
    'host': os.environ.get('REDIS_HOST', 'localhost'),
    'port': 6379,
    'db': 3,
    'socket_timeout': 3,
}
BROKER_URL = os.environ.get('BROKER_URL', 'amqp://guest:@127.0.0.1:5672')

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Django registration
ACCOUNT_ACTIVATION_DAYS = 7


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'public')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# For debug toolbar
DEBUG_TOOLBAR_CONFIG = {
    'JQUERY_URL': '/static/jquery.min.js'
}


_TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.template.context_processors.debug",
    "django.template.context_processors.i18n",
    "django.template.context_processors.media",
    "django.template.context_processors.static",
    "django.template.context_processors.tz",
    "django.template.context_processors.request",
    "django.contrib.messages.context_processors.messages"
)

TEMPLATES = [
    {
        "BACKEND": "django_jinja.backend.Jinja2",
        "APP_DIRS": True,
        "DIRS": [BASE_DIR + '/templates'],
        "OPTIONS": {
            "match_extension": None,
            # We use default template names for auth things, so we need to intercept them,
            # we hackily exclude email, subject and logged_out templates
            "match_regex": r'(.*\.(j2|jinja)$|(^registration.*(?<!email|bject|d_out)\.\w+$))',
            "context_processors": _TEMPLATE_CONTEXT_PROCESSORS,
            "constants": {
                "FRONTEND": "http://localhost:8082/" if DEBUG else STATIC_URL
            }
        }
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [BASE_DIR + '/templates'],
        "OPTIONS": {
            "context_processors": _TEMPLATE_CONTEXT_PROCESSORS,
            "debug": DEBUG,
        }
    },
]

TEMPLATE_DEFAULT_EXTENSION = '.j2'


# Cacheops settings
CACHEOPS_REDIS = {
    'host': os.environ.get('REDIS_HOST', 'localhost'),  # redis-server is on same machine
    'port': 6379,         # default redis port
    'db': 2,              # SELECT redis db different from whatever we use for anything else
    'socket_timeout': 3,  # connection timeout in seconds, optional
}

CACHEOPS = {
    'tags.sampleannotation': {'ops': [], 'timeout': 60 * 60},
}


CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
CELERY_TASK_TIME_LIMIT = 60 * 60 * 12
CELERY_SEND_TASK_ERROR_EMAILS = True

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = os.environ.get('FROM_EMAIL', 'no-reply@stargeo.org')
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD= os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_USE_TLS= os.environ.get("EMAIL_USE_TLS") == "True"


# Logging settings
if 'ADMIN' in os.environ:
    ADMINS = (
        tuple(os.environ['ADMIN'].split(':')),
    )

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(name)s %(levelname)s [%(asctime)s] %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, '../logs/debug.log'),
            'formatter': 'verbose'
        },
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
        'boto': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'requests': {
            'handlers': ['file'],
            'levelname': 'ERROR',
            'propagate': True,
        },
        'urllib3': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'parso': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        }
    },
}

# Log to console in DEBUG mode
if DEBUG or os.environ.get('CONSOLE_DEBUG'):
    for logger in LOGGING['loggers'].values():
        logger['handlers'] = ['console']


AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY = os.environ['AWS_CREDENTIALS'].split(':')
S3_BUCKETS = {
    'legacy.analysis.df': os.environ['AWS_BUCKET_TEMPLATE'] % 'analysis-df',
    'legacy.analysis.fold_changes': os.environ['AWS_BUCKET_TEMPLATE'] % 'fold-changes',
    'tags.snapshot.files': os.environ['AWS_BUCKET_TEMPLATE'] % 'snapshots',
}

# Django REST framework settings
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'PAGE_SIZE': 10
}

DJAPI_AUTH = ['djapi.authtoken.use_token', 'djapi.auth.use_contribauth']

BIOPORTAL_API_KEY = os.environ.get('BIOPORTAL_API_KEY')

ZENODO_CLIENT_ID, ZENODO_CLIENT_SECRET = os.environ.get('ZENODO_CREDENTIALS', ':').split(':')
OAUTH2ACCESS = {
    'zenodo': {
        'client_id': ZENODO_CLIENT_ID,
        'client_secret': ZENODO_CLIENT_SECRET,
        'scope': ['deposit:write', 'deposit:actions'],
        'auth_url': 'https://zenodo.org/oauth/authorize',
        'token_url': 'https://zenodo.org/oauth/token',
    }
}
