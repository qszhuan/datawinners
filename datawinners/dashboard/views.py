# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import json
from django.http import HttpResponse

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from mangrove.datastore.entity import get_by_short_code
from mangrove.datastore.queries import get_entities_by_type
from datawinners.accountmanagement.views import session_not_expired
from datawinners import settings
from datawinners.accountmanagement.models import NGOUserProfile, Organization
from datawinners.accountmanagement.views import is_datasender, is_not_expired
from datawinners.dashboard import helper

from datawinners.main.utils import get_database_manager
from datawinners.project.models import ProjectState, Project
from datawinners.project.wizard_view import edit_project
from mangrove.form_model.form_model import FormModel
from mangrove.transport import Channel
from project.views import project_overview

def _find_reporter_name(dbm, row):
    channel = row.value.get("channel")
    if channel == Channel.SMS:
        reporters = dbm.load_all_rows_in_view('reporters_by_number_and_name',key=(row.value["source"]))
        reporter = reporters[0].value
    else:
        reporter = ""
    return reporter


def _make_message(row):
    if row.value["status"]:
        message = " ".join(["%s: %s" % (k, v) for k, v in row.value["values"].items()])
    else:
        message = row.value["error_message"]
    return message

@login_required(login_url='/login')
@session_not_expired
@csrf_exempt
@is_not_expired
def get_submission_breakup(request, project_id):
    dbm = get_database_manager(request.user)
    project = Project.load(dbm.database, project_id)
    form_model = FormModel.get(dbm, project.qid)
    rows = dbm.load_all_rows_in_view('undeleted_submission_log', startkey=[form_model.form_code], endkey=[form_model.form_code, {}],
                                     group=True, group_level=1, reduce=True)
    submission_success,submission_errors = 0, 0
    for row in rows:
        submission_success = row["value"]["success"]
        submission_errors = row["value"]["count"] - row["value"]["success"]
    response = json.dumps([submission_success, submission_errors])
    return HttpResponse(response)

def get_submissions_about_project(request, project_id):
    dbm = get_database_manager(request.user)
    project = Project.load(dbm.database, project_id)
    form_model = FormModel.get(dbm, project.qid)
    rows = dbm.load_all_rows_in_view('undeleted_submission_log', reduce=False, descending=True, startkey=[form_model.form_code, {}],
                                     endkey=[form_model.form_code], limit=7)
    submission_list = []
    for row in rows:
        reporter = _find_reporter_name(dbm, row)
        message = _make_message(row)
        submission = dict(message=message, created=row.value["submitted_on"].strftime("%B %d %y %H:%M"), reporter=reporter,
                          status=row.value["status"])
        submission_list.append(submission)

    submission_response = json.dumps(submission_list)
    return HttpResponse(submission_response)

def is_project_inactive(row):
    return row['value']['state'] == ProjectState.INACTIVE

@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
def dashboard(request):
    manager = get_database_manager(request.user)
    user_profile = NGOUserProfile.objects.get(user=request.user)
    organization = Organization.objects.get(org_id=user_profile.org_id)
    project_list = []
    rows = manager.load_all_rows_in_view('all_projects', descending=True, limit=4)
    for row in rows:
        link = reverse("project-overview", args=(row['value']['_id'],))
        if row['value']['state'] == ProjectState.INACTIVE:
            link = reverse(edit_project,args=(row['value']['_id'],))
        project = dict(name=row['value']['name'], link=link, inactive=is_project_inactive(row), id=row['value']['_id'])
        project_list.append(project)
#    language = request.session.get("django_language", "en")
#    return render_to_response('dashboard/home.html',{"projects": project_list, 'trial_account': organization.in_trial_mode, 'language':language}, context_instance=RequestContext(request))
    return render_to_response('dashboard/home.html',{"projects": project_list, 'trial_account': organization.in_trial_mode}, context_instance=RequestContext(request))


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
def start(request):
    text_dict = {'project': _('Projects'), 'datasenders': _('Data Senders'),
                 'subjects': _('Subjects'), 'alldata': _('Data Records')}

    tabs_dict = {'project': 'projects', 'datasenders': 'data_senders',
                 'subjects': 'subjects', 'alldata': 'all_data'}
    page = request.GET['page']
    page = page.split('/')
    url_tokens = [each for each in page if each != '']
    text = text_dict[url_tokens[-1]]
    return render_to_response('dashboard/start.html',
            {'text': text, 'title': text, 'active_tab': tabs_dict[url_tokens[-1]]},
                              context_instance=RequestContext(request))


def map_entities(request):
    dbm = get_database_manager(request.user)
    project = Project.load(dbm.database, request.GET['project_id'])
    if project.is_activity_report():
        entity_list = [get_by_short_code(dbm, short_code, ["reporter"]) for short_code in project.data_senders]
    else:
        entity_list = get_entities_by_type(dbm, request.GET['id'])
    location_geojson = helper.create_location_geojson(entity_list)
    return HttpResponse(location_geojson)

def render_map(request):
    map_api_key = settings.API_KEYS[request.META['HTTP_HOST']]
    return render_to_response('maps/entity_map.html', {'map_api_key': map_api_key},context_instance=RequestContext(request))
