# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from django.conf.urls.defaults import patterns, url
from datawinners.questionfiltering.views import question_filter


urlpatterns = patterns('',
    url(r'^questionfilter/(?P<project_id>.+?)/data/(?P<questionnaire_code>.+?)/$', question_filter),
)
