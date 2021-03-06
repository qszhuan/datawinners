SITE_ID = 1
DEBUG=False


ADMINS = (
    ('TW', 'sairama@thoughtworks.com,ramyar@thoughtworks.com'),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'mangrove',                      # Or path to database file if using sqlite3.
        'USER': 'mangrover',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

API_KEYS = {
    '172.18.9.6': 'AIzaSyDE7V6tcY34e5uAB7eYS7AcSStty87vulQ'
}

TRIAL_REGISTRATION_ENABLED = True

HNI_SUPPORT_EMAIL_ID = 'dummy@dummy.com'

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'test.datawinners@gmail.com'
EMAIL_HOST_PASSWORD = 'd@t@winners'
EMAIL_PORT = 587

COUCHDBMAIN_USERNAME = 'admin'
COUCHDBMAIN_PASSWORD = 'admin'
COUCHDBMAIN_CREDENTIALS = (COUCHDBMAIN_USERNAME, COUCHDBMAIN_PASSWORD)
COUCHDBFEED_USERNAME = 'admin'
COUCHDBFEED_PASSWORD = 'admin'
COUCHDBFEED_CREDENTIALS = (COUCHDBFEED_USERNAME, COUCHDBFEED_PASSWORD)

HNI_BLOG_FEED = 'http://datawinners.wordpress.com/feed/'

CRS_ORG_ID = 'TVZ184210'

FEEDS_ENABLED = True
MAX_FEED_ENTRIES=100