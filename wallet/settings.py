"""
Django settings for wallet project.

Generated by 'django-admin startproject' using Django 4.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
from enum import Enum, auto
from pathlib import Path

import dj_database_url


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# DEPLOYED = True if "SECRET_KEY" in os.environ else False
DEPLOYED = True if "DATABASE_URL" in os.environ else False


class PlaidMode(Enum):
    SANDBOX = auto()
    DEV = auto()
    PRODUCTION = auto()


PLAID_MODE = PlaidMode.SANDBOX

if DEPLOYED:
    DEBUG = False
    DEBUG = True # todo temp!!
    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = os.environ["SECRET_KEY"]
    PLAID_CLIENT_ID = os.environ["PLAID_CLIENT_ID"]
    PLAID_SECRET = os.environ["PLAID_SECRET"]
    SENDGRID_API_KEY = os.environ["SENDGRID_KEY"]
    EMAIL_HOST_PASSWORD = os.environ["SENDGRID_KEY"]
else:
    DEBUG = True
    SECRET_KEY = "django-insecure-kt#8(6pid*k1u6b9!yh(70^7s41ydqu=_!#%l79n8nm-os*$b)"

    try:
        from main import private
    # Allow an escape hatch so the problem runs and can be tested with a quick
    # git pull. Email is non-functional here.
    except ImportError:
        SENDGRID_KEY = ""
        PLAID_SECRET = ""
        PLAID_CLIENT_ID = ""
    else:
        PLAID_CLIENT_ID = private.PLAID_CLIENT_ID

        if PLAID_MODE == PlaidMode.SANDBOX:
            PLAID_SECRET = private.PLAID_SECRET_SANDBOX
        elif PLAID_MODE == PlaidMode.DEV:
            PLAID_SECRET = private.PLAID_SECRET_DEV
        else:
            PLAID_SECRET = private.PLAID_SECRET_PRODUCTION

        SENDGRID_API_KEY = private.SENDGRID_KEY
        EMAIL_HOST_PASSWORD = private.SENDGRID_KEY

        # SECURITY WARNING: don't run with debug turned on in production!

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "financial-monitor-783ae5ca6965.herokuapp.com", "financial-monitor.com"]

# Application definition

INSTALLED_APPS = [
    "main.apps.MainConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # "rest_framework",
    # "corsheaders",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wallet.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "wallet.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Todo: Postgres once working.
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }

LOCAL_DB = "postgres://postgres:test@localhost:5432/wallet"

DATABASES = {"default": dj_database_url.config(default=LOCAL_DB)}

# if DEPLOYED:
#     pass
# else:
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.postgresql",
#             "NAME": "wallet",
#             "USER": "postgres",
#             "PASSWORD": "test",
#             "HOST": "localhost",
#             "PORT": "5432",
#         }
#     }


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_ROOT = "staticfiles"
STATIC_URL = "static/"

STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


ADMINS = (("admin", "contact@finance-monitor.com"),)
MANAGERS = ADMINS

if DEPLOYED:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True

EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_HOST_USER = "apikey"

EMAIL_PORT = 587
EMAIL_USE_TLS = True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
        },
        "console_debug_false": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "logging.StreamHandler",
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "mail_admins"],
            "level": "INFO",
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
