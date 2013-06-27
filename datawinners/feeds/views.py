from datetime import datetime
import urllib2
from django.conf import settings
from django.http import HttpResponse
import jsonpickle
from datawinners.feeds.database import get_feeds_database
from datawinners.feeds.authorization import httpbasic, is_not_datasender

DATE_FORMAT = '%d-%m-%Y %H:%M:%S'


def stream_feeds(feed_dbm, startkey, endkey):
    rows = feed_dbm.database.iterview("questionnaire_feed/questionnaire_feed", 1000, startkey=startkey, endkey=endkey)
    yield "["
    for row in rows:
        yield jsonpickle.encode(row['value'], unpicklable=False)
    yield "]"

@httpbasic
@is_not_datasender
def feed_entries(request, form_code):
    if not settings.FEEDS_ENABLED:
        return HttpResponse(404)
    if _invalid_form_code(form_code):
        return HttpResponse(content='Invalid form code provided', status=400)
    if invalid_date(request.GET.get('start_date')):
        return HttpResponse(content='Invalid Start Date provided expected ' + DATE_FORMAT, status=400)
    if invalid_date(request.GET.get('end_date')):
        return HttpResponse(content='Invalid End Date provided expected ' + DATE_FORMAT, status=400)
    if lesser_end_date(request.GET.get('end_date'), request.GET.get('start_date')):
        return HttpResponse(content='End Date provided is less than Start Date', status=400)

    feed_dbm = get_feeds_database(request.user)
    start_date = _parse_date(request.GET['start_date'])
    end_date = _parse_date(request.GET['end_date'])
    return HttpResponse(stream_feeds(feed_dbm, startkey=[form_code, start_date], endkey=[form_code, end_date]), content_type='application/json; charset=utf-8')


def _is_empty_string(value):
    return value is None or value.strip() == ''


def _invalid_form_code(form_code):
    if _is_empty_string(form_code):
        return True
    return False


def _parse_date(date):
    date_string = urllib2.unquote(date.strip())
    return datetime.strptime(date_string, DATE_FORMAT)


def invalid_date(date_string):
    if _is_empty_string(date_string):
        return True
    try:
        _parse_date(date_string)
    except ValueError:
        return True
    return False


def lesser_end_date(end_date, start_date):
    end_date = _parse_date(end_date)
    start_date = _parse_date(start_date)
    return end_date < start_date
