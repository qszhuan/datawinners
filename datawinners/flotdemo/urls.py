from django.conf.urls.defaults import patterns
from datawinners.flotdemo.views import *

urlpatterns = patterns('',
    (r'^flotdemo/$', chart_demo),
)