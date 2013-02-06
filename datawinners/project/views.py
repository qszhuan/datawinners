# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from collections import namedtuple
import json
import datetime
import logging
from time import mktime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext_lazy as _, get_language, activate
from django.utils.translation import ugettext
from django.conf import settings
from django.utils import translation
from django.core.urlresolvers import reverse
from django.contrib import messages
from datawinners.accountmanagement.views import session_not_expired
from datawinners.project.view_models import ReporterEntity
from mangrove.datastore.entity import get_by_short_code
from datawinners.alldata.helper import get_visibility_settings_for
from datawinners.custom_report_router.report_router import ReportRouter
from datawinners.entity.helper import process_create_data_sender_form, add_imported_data_sender_to_trial_organization, _get_data, update_data_sender_from_trial_organization
from datawinners.entity import import_data as import_module
from datawinners.submission.location import LocationBridge
from datawinners.utils import get_organization
from mangrove.datastore.queries import get_entity_count_for_type, get_non_voided_entity_count_for_type
from mangrove.errors.MangroveException import QuestionCodeAlreadyExistsException, EntityQuestionAlreadyExistsException, DataObjectAlreadyExists, DataObjectNotFound, QuestionAlreadyExistsException, MangroveException
from mangrove.form_model import form_model
from mangrove.form_model.field import field_to_json
from mangrove.form_model.form_model import get_form_model_by_code, FormModel, REGISTRATION_FORM_CODE, get_form_model_by_entity_type, REPORTER
from mangrove.transport.facade import TransportInfo, Request
from mangrove.transport.player.player import WebPlayer
from mangrove.transport.submissions import  get_submissions, submission_count
from mangrove.utils.dates import convert_date_string_in_UTC_to_epoch
from mangrove.utils.json_codecs import encode_json
from mangrove.utils.types import is_empty, is_string
from mangrove.transport import Channel

import datawinners.utils as utils

from datawinners.accountmanagement.views import is_datasender, is_datasender_allowed, is_new_user, project_has_web_device
from datawinners.entity.import_data import load_all_subjects_of_type, get_entity_type_fields, get_entity_type_info
from datawinners.location.LocationTree import get_location_tree
from datawinners.main.utils import get_database_manager
from datawinners.messageprovider.message_handler import get_exception_message_for
from datawinners.messageprovider.messages import exception_messages, WEB
from datawinners.project.forms import BroadcastMessageForm
from datawinners.project.models import Project, Reminder, ReminderMode, get_all_reminder_logs_for_project, get_all_projects
from datawinners.accountmanagement.models import Organization, OrganizationSetting, NGOUserProfile
from datawinners.entity.forms import ReporterRegistrationForm
from datawinners.entity.views import import_subjects_from_project_wizard, save_questionnaire as subject_save_questionnaire, create_single_web_user
from datawinners.project.wizard_view import edit_project, reminders
from datawinners.location.LocationTree import get_location_hierarchy
from datawinners.project import models
from datawinners.project.web_questionnaire_form_creator import WebQuestionnaireFormCreator, SubjectQuestionFieldCreator
from datawinners.accountmanagement.views import is_not_expired
from mangrove.transport.player.parser import XlsDatasenderParser
import helper
from project.utils import make_project_links, make_data_sender_links, make_subject_links
from project.filters import   KeywordFilter
from project.helper import is_project_exist
from project.submission_analyzer import SubmissionAnalyzer
from project.submission_router import SubmissionRouter, successful_submissions
from project.submission_utils.submission_filter import SubmissionFilter
from datawinners.activitylog.models import UserActivityLog
from datawinners.common.constant import DELETED_PROJECT, ACTIVATED_PROJECT, IMPORTED_DATA_SENDERS,\
    REMOVED_DATA_SENDER_TO_PROJECTS, REGISTERED_SUBJECT, REGISTERED_DATA_SENDER, EDITED_DATA_SENDER, EDITED_PROJECT
from datawinners.questionnaire.questionnaire_builder import QuestionnaireBuilder

logger = logging.getLogger("django")
performance_logger = logging.getLogger("performance")
websubmission_logger = logging.getLogger("websubmission")

END_OF_DAY = " 23:59:59"
START_OF_DAY = " 00:00:00"

PAGE_SIZE = 10
NUMBER_TYPE_OPTIONS = ["Latest", "Sum", "Count", "Min", "Max", "Average"]
MULTI_CHOICE_TYPE_OPTIONS = ["Latest", "sum(yes)", "percent(yes)", "sum(no)", "percent(no)"]
DATE_TYPE_OPTIONS = ["Latest"]
GEO_TYPE_OPTIONS = ["Latest"]
TEXT_TYPE_OPTIONS = ["Latest", "Most Frequent"]

XLS_TUPLE_FORMAT = "%s (%s)"

@login_required(login_url='/login')
@is_not_expired
def save_questionnaire(request):
    manager = get_database_manager(request.user)
    if request.method == 'POST':
        questionnaire_code = request.POST['questionnaire-code']
        json_string = request.POST['question-set']
        question_set = json.loads(json_string)
        pid = request.POST['pid']
        project = Project.load(manager.database, pid)
        form_model = FormModel.get(manager, project.qid)
        old_fields = form_model.fields
        try:
            QuestionnaireBuilder(form_model, manager).update_questionnaire_with_questions(question_set)
        except QuestionCodeAlreadyExistsException as e:
            return HttpResponseServerError(e)
        except QuestionAlreadyExistsException as e:
            return HttpResponseServerError(e)
        except EntityQuestionAlreadyExistsException as e:
            return HttpResponseServerError(e.message)
        else:
            try:
                form_model.form_code = questionnaire_code.lower()
            except DataObjectAlreadyExists as e:
                if e.message.find("Form") >= 0:
                    return HttpResponseServerError("Questionnaire with this code already exists")
                return HttpResponseServerError(e.message)
            form_model.name = project.name
            form_model.entity_id = project.entity_type
            detail = utils.get_changed_questions(old_fields, form_model.fields, subject=False)
            form_model.save()
            UserActivityLog().log(request, project=project.name, action=EDITED_PROJECT, detail=json.dumps(detail))
            return HttpResponse(json.dumps({"response": "ok"}))


@login_required(login_url='/login')
@session_not_expired
@is_new_user
@is_datasender
@is_not_expired
def index(request):
    project_list = []
    rows = models.get_all_projects(dbm=get_database_manager(request.user))
    for row in rows:
        project_id = row['value']['_id']
        link = reverse('project-overview', args=[project_id])
        if row['value']['state'] == 'Inactive':
            link = reverse('edit_project', args=[project_id])
        activate_link = reverse('activate_project', args=[project_id])
        delete_link = reverse('delete_project', args=[project_id])
        project = dict(delete_link=delete_link, name=row['value']['name'], created=row['value']['created'],
            type=row['value']['project_type'],
            link=link, activate_link=activate_link, state=row['value']['state'])
        project_list.append(project)
    return render_to_response('project/index.html', {'projects': project_list},
        context_instance=RequestContext(request))


@login_required(login_url='/login')
@session_not_expired
@is_new_user
@is_datasender
@is_not_expired
def delete_project(request, project_id):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)
    helper.delete_project(manager, project)
    undelete_link = reverse(undelete_project, args=[project_id])
    if len(get_all_projects(manager)) > 0:
        messages.info(request, undelete_link)
    UserActivityLog().log(request, action=DELETED_PROJECT, project=project.name)
    return HttpResponseRedirect(reverse(index))


def undelete_project(request, project_id):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)
    helper.delete_project(manager, project, False)
    return HttpResponseRedirect(reverse(index))


@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
@is_project_exist
def project_overview(request, project_id=None):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)
    questionnaire = FormModel.get(manager, project.qid)
    number_of_questions = len(questionnaire.fields)
    questionnaire_code = questionnaire.form_code
    project_links = make_project_links(project, questionnaire_code)
    map_api_key = settings.API_KEYS.get(request.META['HTTP_HOST'])
    number_data_sender = len(project.get_data_senders(manager))
    number_records = submission_count(manager, questionnaire_code, None, None)
    number_reminders = Reminder.objects.filter(project_id=project.id).count()
    links = {'registered_data_senders': reverse(registered_datasenders, args=[project_id]),
             'web_questionnaire_list': reverse(web_questionnaire, args=[project_id])}
    add_data_senders_to_see_on_map_msg = _(
        "Register Data Senders to see them on this map") if number_data_sender == 0 else ""
    add_subjects_to_see_on_map_msg = _(
        "Register %s to see them on this map") % project.entity_type if get_entity_count_for_type(manager,
        project.entity_type) == 0 else ""
    in_trial_mode = _in_trial_mode(request)
    return render_to_response('project/overview.html', RequestContext(request, {
        'project': project,
        'entity_type': project['entity_type'],
        'project_links': project_links,
        'number_of_questions': number_of_questions,
        'map_api_key': map_api_key,
        'number_data_sender': number_data_sender,
        'number_records': number_records,
        'number_reminders': number_reminders,
        'links': links,
        'add_data_senders_to_see_on_map_msg': add_data_senders_to_see_on_map_msg,
        'add_subjects_to_see_on_map_msg': add_subjects_to_see_on_map_msg,
        'in_trial_mode': in_trial_mode,
        'questionnaire_code': questionnaire_code,
        }))

def filter_by_keyword(keyword, raw_field_values):
    return KeywordFilter(keyword).filter(raw_field_values)


def _get_submissions_by_type(request, manager, form_model):
    submission_type = request.GET.get('type')
    submissions = SubmissionRouter().route(submission_type)(manager, form_model.form_code)
    if submission_type == SubmissionRouter.ERROR:
        return filter(lambda x: not x.status, submissions)
    return submissions


def _get_submissions(manager, questionnaire_code, request, paginate=True):
    request_bag = request.GET
    start_time = request_bag.get("start_time") or ""
    end_time = request_bag.get("end_time") or ""
    start_time_epoch = convert_date_string_in_UTC_to_epoch(
        helper.get_formatted_time_string(start_time.strip() + START_OF_DAY))
    end_time_epoch = convert_date_string_in_UTC_to_epoch(
        helper.get_formatted_time_string(end_time.strip() + END_OF_DAY))
    current_page = (int(request_bag.get('page_number') or 1) - 1) if paginate else 0
    page_size = PAGE_SIZE if paginate else None
    submissions = get_submissions(manager, questionnaire_code, start_time_epoch, end_time_epoch, current_page,
        page_size)
    count = submission_count(manager, questionnaire_code, start_time_epoch, end_time_epoch)
    error_message = ugettext("No submissions present for this project") if not count else None
    return count, submissions, error_message


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
def submissions(request):
    """
            Called via ajax, returns the partial HTML for the submissions made for the project, paginated.
    """
    manager = get_database_manager(request.user)
    if request.method == 'GET':
        questionnaire_code = request.GET.get('questionnaire_code')
        questionnaire = get_form_model_by_code(manager, questionnaire_code)
        count, submissions, error_message = _get_submissions(manager, questionnaire_code, request)
        submission_display = helper.adapt_submissions_for_template(questionnaire.fields, submissions)
        return render_to_response('project/log_table.html',
                {'questionnaire_code': questionnaire_code, 'questions': questionnaire.fields,
                 'submissions': submission_display, 'pages': count,
                 'error_message': error_message,
                 'success_message': ""}, context_instance=RequestContext(request))

def _to_name_id_string(value, delimiter='</br>'):
    if not isinstance(value, tuple):return value
    assert len(value) >= 2
    if not value[1]: return value[0]

    return "%s%s(%s)" % (value[0], delimiter, value[1])

def formatted_data(field_values, delimiter='</br>'):
    return  [[_to_name_id_string(each, delimiter) for each in row] for row in field_values]

def _build_submission_analyzer(request, manager, form_model, is_for_submission_page):
    submissions = _get_submissions_by_type(request, manager, form_model)
    filtered_submissions = SubmissionFilter(request.POST, form_model).filter(submissions)
    analyzer = SubmissionAnalyzer(form_model, manager, helper.get_org_id_by_user(request.user), filtered_submissions,
        request.POST.get('keyword', ''), is_for_submission_page=is_for_submission_page)

    return analyzer

def _get_imports_subjects_post_url(project_id=None):
    import_url = reverse(import_subjects_from_project_wizard)
    return import_url if project_id is None else ("%s?project_id=%s" % (import_url, project_id))


def _format_string_for_reminder_table(value):
    return (' '.join(value.split('_'))).title()


def _make_reminder_mode(reminder_mode, day):
    if reminder_mode == ReminderMode.ON_DEADLINE:
        return _format_string_for_reminder_table(reminder_mode)
    return str(day) + ' days ' + _format_string_for_reminder_table(reminder_mode)


def _format_reminder(reminder, project_id):
    return dict(message=reminder.message, id=reminder.id,
        to=_format_string_for_reminder_table(reminder.remind_to),
        when=_make_reminder_mode(reminder.reminder_mode, reminder.day),
        delete_link=reverse('delete_reminder', args=[project_id, reminder.id]))

def _format_reminders(reminders, project_id):
    return [_format_reminder(reminder, project_id) for reminder in reminders]


@login_required(login_url='/login')
@session_not_expired
@csrf_exempt
@is_not_expired
def create_reminder(request, project_id):
    if is_empty(request.POST['id']):
        Reminder(project_id=project_id, day=request.POST.get('day', 0), message=request.POST['message'],
            reminder_mode=request.POST['reminder_mode'], remind_to=request.POST['remind_to'],
            organization=utils.get_organization(request)).save()
        messages.success(request, 'Reminder added successfully')
    else:
        reminder = Reminder.objects.filter(project_id=project_id, id=request.POST['id'])[0]
        reminder.day = request.POST.get('day', 0)
        reminder.message = request.POST['message']
        reminder.reminder_mode = request.POST['reminder_mode']
        reminder.remind_to = request.POST['remind_to']
        reminder.save()
        messages.success(request, 'Reminder updated successfully')
    return HttpResponseRedirect(reverse(reminders, args=[project_id]))


@login_required(login_url='/login')
@session_not_expired
@csrf_exempt
@is_not_expired
def get_reminder(request, project_id):
    reminder_id = request.GET['id']
    reminder = Reminder.objects.filter(project_id=project_id, id=reminder_id)[0]
    return HttpResponse(json.dumps(reminder.to_dict()))


@login_required(login_url='/login')
@session_not_expired
@csrf_exempt
@is_not_expired
def delete_reminder(request, project_id, reminder_id):
    Reminder.objects.filter(project_id=project_id, id=reminder_id)[0].delete()
    messages.success(request, 'Reminder deleted')
    return HttpResponseRedirect(reverse(reminders, args=[project_id]))


@login_required(login_url='/login')
@csrf_exempt
@is_not_expired
def manage_reminders(request, project_id):
    if request.method == 'GET':
        reminders = Reminder.objects.filter(project_id=project_id, voided=False)
        return HttpResponse(json.dumps([reminder.to_dict() for reminder in reminders]))

    if request.method == 'POST':
        reminders = json.loads(request.POST['reminders'])
        Reminder.objects.filter(project_id=project_id).delete()
        for reminder in reminders:
            Reminder(project_id=project_id, day=reminder['day'], message=reminder['message'],
                reminder_mode=reminder['reminderMode'], organization=utils.get_organization(request),
                remind_to=reminder['targetDataSenders']).save()
        return HttpResponse("Reminders has been saved")


@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
def sent_reminders(request, project_id):
    dbm = get_database_manager(request.user)
    project = Project.load(dbm.database, project_id)
    questionnaire = FormModel.get(dbm, project.qid)
    organization = Organization.objects.get(org_id=request.user.get_profile().org_id)
    is_trial_account = organization.in_trial_mode
    html = 'project/reminders_trial.html' if organization.in_trial_mode else 'project/sent_reminders.html'
    return render_to_response(html,
            {'project': project, "project_links": make_project_links(project, questionnaire.form_code),
             'reminders': get_all_reminder_logs_for_project(project_id, dbm),
             'in_trial_mode': is_trial_account,
             'create_reminder_link': reverse(create_reminder, args=[project_id])},
        context_instance=RequestContext(request))


def _get_data_senders(dbm, form, project):
    data_senders = []
    if form.cleaned_data['to'] == "All":
        data_senders = _get_all_data_senders(dbm)
    elif form.cleaned_data['to'] == "Associated":
        data_senders = project.get_data_senders(dbm)
    return data_senders


@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
def broadcast_message(request, project_id):
    dbm = get_database_manager(request.user)
    project = Project.load(dbm.database, project_id)
    questionnaire = FormModel.get(dbm, project.qid)
    organization = utils.get_organization(request)
    if request.method == 'GET':
        form = BroadcastMessageForm()
        html = 'project/broadcast_message_trial.html' if organization.in_trial_mode else 'project/broadcast_message.html'
        return render_to_response(html, {'project': project,
                                         "project_links": make_project_links(project, questionnaire.form_code),
                                         "form": form,
                                         "success": None},
            context_instance=RequestContext(request))
    if request.method == 'POST':
        form = BroadcastMessageForm(request.POST)
        if form.is_valid():
            data_senders = _get_data_senders(dbm, form, project)
            organization_setting = OrganizationSetting.objects.get(organization=organization)
            current_month = datetime.date(datetime.datetime.now().year, datetime.datetime.now().month, 1)
            message_tracker = organization._get_message_tracker(current_month)
            other_numbers = form.cleaned_data['others']
            sms_sent = helper.broadcast_message(data_senders, form.cleaned_data['text'],
                organization_setting.get_organisation_sms_number()[0], other_numbers, message_tracker,
                country_code=organization.get_phone_country_code())
            form = BroadcastMessageForm()
            return render_to_response('project/broadcast_message.html',
                    {'project': project,
                     "project_links": make_project_links(project, questionnaire.form_code), "form": form,
                     'success': sms_sent},
                context_instance=RequestContext(request))

        return render_to_response('project/broadcast_message.html',
                {'project': project,
                 "project_links": make_project_links(project, questionnaire.form_code), "form": form,
                 'success': None},
            context_instance=RequestContext(request))


def _get_all_data_senders(dbm):
    data_senders, fields, labels = load_all_subjects_of_type(dbm)
    return [dict(zip(fields, data["cols"])) for data in data_senders]


@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
def activate_project(request, project_id=None):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)
    project.activate(manager)
    form_model = FormModel.get(manager, project.qid)
    oneDay = datetime.timedelta(days=1)
    tomorrow = datetime.datetime.now() + oneDay
    submissions = get_submissions(manager, form_model.form_code, from_time=0,
        to_time=int(mktime(tomorrow.timetuple())) * 1000, page_size=None)
    for submission in submissions:
        submission.void()
    UserActivityLog().log(request, action=ACTIVATED_PROJECT, project=project.name)
    return HttpResponseRedirect(reverse('project-overview', args=[project_id]))


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
def review_and_test(request, project_id=None):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)
    form_model = FormModel.get(manager, project.qid)
    if request.method == 'GET':
        number_of_registered_subjects = get_non_voided_entity_count_for_type(manager, project.entity_type)
        number_of_registered_data_senders = len(project.data_senders)
        fields = form_model.fields
        if form_model.entity_defaults_to_reporter():
            fields = helper.hide_entity_question(form_model.fields)
        is_reminder = "enabled" if project['reminder_and_deadline']['has_deadline'] else "disabled"

        project_devices = project.devices
        devices = ", ".join(project_devices).replace('sms', 'SMS').replace('web', 'Web').replace('smartPhone',
            'Smartphone')

        in_trial_mode = _in_trial_mode(request)
        return render_to_response('project/review_and_test.html', {'project': project, 'fields': fields,
                                                                   'project_links': make_project_links(project,
                                                                       form_model.form_code),
                                                                   'number_of_datasenders': number_of_registered_data_senders
            ,
                                                                   'number_of_subjects': number_of_registered_subjects,
                                                                   "is_reminder": is_reminder,
                                                                   "in_trial_mode": in_trial_mode,
                                                                   "devices": devices},
            context_instance=RequestContext(request))


def _get_project_and_project_link(manager, project_id, reporter_id=None):
    project = Project.load(manager.database, project_id)
    questionnaire = FormModel.get(manager, project.qid)
    project_links = make_project_links(project, questionnaire.form_code, reporter_id)
    return project, project_links

@login_required(login_url='/login')
@session_not_expired
@is_not_expired
def subjects(request, project_id=None):
    manager = get_database_manager(request.user)
    project, project_links = _get_project_and_project_link(manager, project_id)
    fields, project_links_with_subject_questionnaire, questions, reg_form = _get_registration_form(manager, project,
        type_of_subject='subject')
    example_sms = get_example_sms_message(fields, reg_form)
    subject = get_entity_type_info(project.entity_type, manager=manager)
    return render_to_response('project/subjects.html',
            {'project': project,
             'project_links': project_links,
             'questions': questions,
             'questionnaire_code': reg_form.form_code,
             'example_sms': example_sms,
             'org_number': get_organization_telephone_number(request),
             'current_language': translation.get_language(),
             'subject': subject},
        context_instance=RequestContext(request))


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
def registered_subjects(request, project_id=None):
    manager = get_database_manager(request.user)
    project, project_links = _get_project_and_project_link(manager, project_id)
    all_data, fields, labels = load_all_subjects_of_type(manager, type=project.entity_type)
    subject = get_entity_type_info(project.entity_type, manager=manager)
    in_trial_mode = _in_trial_mode(request)
    return render_to_response('project/registered_subjects.html',
            {'project': project, 'project_links': project_links, 'all_data': all_data, "labels": labels,
             "subject": subject, 'in_trial_mode': in_trial_mode, 'edit_url': '/project/subject/edit/%s/' % project_id},
        context_instance=RequestContext(request))


@login_required(login_url='/login')
@csrf_exempt
@is_not_expired
def registered_datasenders(request, project_id=None):
    manager = get_database_manager(request.user)
    project, project_links = _get_project_and_project_link(manager, project_id)
    grant_web_access = False
    if request.method == 'GET' and int(request.GET.get('web', '0')):
        grant_web_access = True
    if request.method == 'GET':
        fields, old_labels, codes = get_entity_type_fields(manager)
        labels = []
        for label in old_labels:
            if label != "What is the mobile number associated with the subject?":
                labels.append(_(label.replace('subject', 'Data Sender')))
            else:
                labels.append(_("What is the Data Sender's mobile number?"))
        in_trial_mode = _in_trial_mode(request)
        senders = project.get_data_senders(manager)
        for sender in senders:
            if sender["short_code"] == "test":
                index = senders.index(sender)
                del senders[index]
                continue
            org_id = NGOUserProfile.objects.get(user=request.user).org_id
            user_profile = NGOUserProfile.objects.filter(reporter_id=sender['short_code'], org_id=org_id)

            sender["is_user"] = False
            if len(user_profile) > 0:
                data_sender_user_groups = list(user_profile[0].user.groups.values_list('name', flat=True))
                if "NGO Admins" in data_sender_user_groups or "Project Managers" in data_sender_user_groups\
                or "Read Only Users" in data_sender_user_groups:
                    sender["is_user"] = True
                sender['email'] = user_profile[0].user.email
                sender['devices'] = "SMS,Web,Smartphone"
            else:
                sender['email'] = "--"
                sender['devices'] = "SMS"

            sender['project'] = project.name

        return render_to_response('project/registered_datasenders.html',
                {'project': project, 'project_links': project_links, 'all_data': (
                senders), 'grant_web_access': grant_web_access, "labels": labels,
                 'current_language': translation.get_language(), 'in_trial_mode': in_trial_mode},
            context_instance=RequestContext(request))
    if request.method == 'POST':
        error_message, failure_imports, success_message, imported_entities = import_module.import_data(request, manager,
            default_parser=XlsDatasenderParser)
        all_data_senders, fields, labels = import_module.load_all_subjects_of_type(manager)
        project.data_senders.extend([id for id in imported_entities.keys()])
        project.save(manager)

        if len(imported_entities.keys()):
            UserActivityLog().log(request, action=IMPORTED_DATA_SENDERS,
                detail=json.dumps(dict({"Unique ID": "[%s]" % ", ".join(imported_entities.keys())})),
                project=project.name)
        mobile_number_index = fields.index('mobile_number')
        add_imported_data_sender_to_trial_organization(request, imported_entities,
            all_data_senders=all_data_senders, index=mobile_number_index)
        return HttpResponse(json.dumps(
                {'success': error_message is None and is_empty(failure_imports), 'message': success_message,
                 'error_message': error_message,
                 'failure_imports': failure_imports, 'all_data_senders': all_data_senders,
                 'imported_entities': imported_entities,
                 'associated_datasenders': project.data_senders}))


@login_required(login_url='/login')
@csrf_exempt
@is_not_expired
def disassociate_datasenders(request):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, request.POST['project_id'])
    [project.data_senders.remove(id) for id in request.POST['ids'].split(';') if id in project.data_senders]
    project.save(manager)
    ids = request.POST["ids"].split(";")
    if len(ids):
        UserActivityLog().log(request, action=REMOVED_DATA_SENDER_TO_PROJECTS, project=project.name,
            detail=json.dumps(dict({"Unique ID": "[%s]" % ", ".join(ids)})))
    return HttpResponse(reverse(registered_datasenders, args=(project.id,)))


def _get_questions_for_datasenders_registration_for_print_preview(questions):
    cleaned_qestions = _get_questions_for_datasenders_registration_for_wizard(questions)
    cleaned_qestions.insert(0, questions[0])
    return cleaned_qestions


def _get_questions_for_datasenders_registration_for_wizard(questions):
    return [questions[1], questions[2], questions[3], questions[4], questions[5]]


@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
def datasenders(request, project_id=None):
    manager = get_database_manager(request.user)
    project, project_links = _get_project_and_project_link(manager, project_id)
    fields, project_links, questions, reg_form = _get_registration_form(manager, project)
    questions = _get_questions_for_datasenders_registration_for_print_preview(questions)
    example_sms = get_example_sms_message(questions, reg_form)
    return render_to_response('project/datasenders.html',
            {'project': project,
             'project_links': project_links,
             'questions': questions,
             'questionnaire_code': reg_form.form_code,
             'example_sms': example_sms,
             'org_number': get_organization_telephone_number(request),
             'current_language': translation.get_language()},
        context_instance=RequestContext(request))


def get_preview_and_instruction_links_for_questionnaire():
    return {'sms_preview': reverse("questionnaire_sms_preview"),
            'web_preview': reverse("questionnaire_web_preview"),
            'smart_phone_preview': reverse("smart_phone_preview"), }


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
@is_project_exist
def questionnaire(request, project_id=None):
    manager = get_database_manager(request.user)
    if request.method == 'GET':
        project = Project.load(manager.database, project_id)
        form_model = FormModel.get(manager, project.qid)
        fields = form_model.fields
        if form_model.entity_defaults_to_reporter():
            fields = helper.hide_entity_question(form_model.fields)
        existing_questions = json.dumps(fields, default=field_to_json)
        project_links = make_project_links(project, form_model.form_code)
        in_trial_mode = _in_trial_mode(request)
        return render_to_response('project/questionnaire.html',
                {"existing_questions": repr(existing_questions),
                 'questionnaire_code': form_model.form_code,
                 'project': project,
                 'project_links': project_links,
                 'in_trial_mode': in_trial_mode,
                 'preview_links': get_preview_and_instruction_links_for_questionnaire()},
            context_instance=RequestContext(request))


def _make_project_context(form_model, project):
    return {'form_model': form_model, 'project': project,
            'project_links': make_project_links(project,
                form_model.form_code)}


def _create_submission_request(form_model, request):
    submission_request = dict(request.POST)
    submission_request["form_code"] = form_model.form_code
    return submission_request


def _make_form_context(questionnaire_form, project, form_code, hide_link_class, disable_link_class):
    return {'questionnaire_form': questionnaire_form,
            'project': project,
            'project_links': make_project_links(project, form_code),
            'hide_link_class': hide_link_class,
            'disable_link_class': disable_link_class,
            'back_to_project_link': reverse("alldata_index"),
            'smart_phone_instruction_link': reverse("smart_phone_instruction"),
            }


def _get_subject_info(manager, project):
    subject = get_entity_type_info(project.entity_type, manager=manager)
    subject_info = {'subject': subject,
                    'add_link': add_link(project),
                    "entity_type": project.entity_type}
    return subject_info


def _get_form_context(form_code, project, questionnaire_form, manager, hide_link_class, disable_link_class):
    form_context = _make_form_context(questionnaire_form, project, form_code, hide_link_class, disable_link_class)
    form_context.update(_get_subject_info(manager, project))

    return form_context


def get_form_model_and_template(manager, project, is_data_sender, subject):
    form_model = FormModel.get(manager, project.qid)
    template = 'project/data_submission.html' if is_data_sender else "project/web_questionnaire.html"

    if subject:
        template = 'project/register_subject.html'
        form_model = _get_subject_form_model(manager, project.entity_type)

    return form_model, template


def _get_form_code(manager, project):
    return FormModel.get(manager, project.qid).form_code


@login_required(login_url='/login')
@session_not_expired
@is_datasender_allowed
@project_has_web_device
@is_not_expired
@is_project_exist
def web_questionnaire(request, project_id=None, subject=False):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)

    is_data_sender = request.user.get_profile().reporter

    form_model, template = get_form_model_and_template(manager, project, is_data_sender, subject)

    QuestionnaireForm = WebQuestionnaireFormCreator(SubjectQuestionFieldCreator(manager, project),
        form_model=form_model).create()

    form_code_for_project_links = _get_form_code(manager, project) if subject else form_model.form_code

    disable_link_class, hide_link_class = get_visibility_settings_for(request.user)

    if request.method == 'GET':
        questionnaire_form = QuestionnaireForm()
        form_context = _get_form_context(form_code_for_project_links, project, questionnaire_form,
            manager, hide_link_class, disable_link_class)

        return render_to_response(template, form_context,
            context_instance=RequestContext(request))

    if request.method == 'POST':
        questionnaire_form = QuestionnaireForm(country=utils.get_organization_country(request), data=request.POST)
        if not questionnaire_form.is_valid():
            form_context = _get_form_context(form_code_for_project_links, project, questionnaire_form,
                manager, hide_link_class, disable_link_class)

            return render_to_response(template, form_context,
                context_instance=RequestContext(request))

        success_message = None
        error_message = None
        try:
            created_request = helper.create_request(questionnaire_form, request.user.username)
            response = WebPlayer(manager,
                LocationBridge(location_tree=get_location_tree(), get_loc_hierarchy=get_location_hierarchy)).accept(
                created_request, logger=websubmission_logger)
            if response.success:
                ReportRouter().route(get_organization(request).org_id, response)
                if subject:
                    success_message = (_("Successfully submitted. Unique identification number(ID) is:") + " %s") % (
                        response.short_code,)
                    detail_dict = dict(
                            {"Subject Type": project.entity_type.capitalize(), "Unique ID": response.short_code})
                    UserActivityLog().log(request, action=REGISTERED_SUBJECT, project=project.name,
                        detail=json.dumps(detail_dict))
                else:
                    success_message = _("Successfully submitted")
                questionnaire_form = QuestionnaireForm()
            else:
                questionnaire_form._errors = helper.errors_to_list(response.errors, form_model.fields)

                form_context = _get_form_context(form_code_for_project_links, project, questionnaire_form,
                    manager, hide_link_class, disable_link_class)
                return render_to_response(template, form_context,
                    context_instance=RequestContext(request))

        except DataObjectNotFound as exception:
            logger.exception(exception)
            message = exception_messages.get(DataObjectNotFound).get(WEB)
            error_message = _(message) % (form_model.entity_type[0], form_model.entity_type[0])
        except Exception as exception:
            logger.exception('Web Submission failure:-')
            error_message = _(get_exception_message_for(exception=exception, channel=Channel.WEB))

        _project_context = _get_form_context(form_code_for_project_links, project, questionnaire_form,
            manager, hide_link_class, disable_link_class)

        _project_context.update({'success_message': success_message, 'error_message': error_message})

        return render_to_response(template, _project_context,
            context_instance=RequestContext(request))


def get_example_sms(fields):
    example_sms = ""
    for field in fields:
        example_sms = example_sms + " " + unicode(_('answer')) + str(fields.index(field) + 1)
    return example_sms


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
@is_project_exist
# TODO : TW_BLR : what happens in case of POST?
def questionnaire_preview(request, project_id=None, sms_preview=False):
    manager = get_database_manager(request.user)
    if request.method == 'GET':
        project = Project.load(manager.database, project_id)
        form_model = FormModel.get(manager, project.qid)
        fields = form_model.fields
        if form_model.entity_defaults_to_reporter():
            fields = helper.hide_entity_question(form_model.fields)
        project_links = make_project_links(project, form_model.form_code)
        questions = []
        for field in fields:
            question = helper.get_preview_for_field(field)
            questions.append(question)
        example_sms = "%s" % (
            form_model.form_code)
        example_sms += get_example_sms(fields)

    template = 'project/questionnaire_preview.html' if sms_preview else 'project/questionnaire_preview_list.html'
    return render_to_response(template,
            {"questions": questions, 'questionnaire_code': form_model.form_code,
             'project': project, 'project_links': project_links,
             'example_sms': example_sms, 'org_number': get_organization_telephone_number(request)},
        context_instance=RequestContext(request))


def _get_preview_for_field_in_registration_questionnaire(field, language):
    preview = {"description": field.label, "code": field.code, "type": field.type,
               "instruction": field.instruction}
    constraints = field.get_constraint_text() if field.type not in ["select", "select1"] else\
    [(option["text"], option["val"]) for option in field.options]
    preview.update({"constraints": constraints})
    return preview



def _get_registration_form(manager, project, type_of_subject='reporter'):
    if type_of_subject == 'reporter':
        registration_questionnaire = form_model.get_form_model_by_code(manager, REGISTRATION_FORM_CODE)
    else:
        entity_type = [project.entity_type]
        registration_questionnaire = get_form_model_by_entity_type(manager, entity_type)
        if registration_questionnaire is None:
            registration_questionnaire = form_model.get_form_model_by_code(manager, REGISTRATION_FORM_CODE)
    fields = registration_questionnaire.fields
    project_links = make_project_links(project, registration_questionnaire.form_code)
    questions = []
    for field in fields:
        question = _get_preview_for_field_in_registration_questionnaire(field,
            registration_questionnaire.activeLanguages[0])
        questions.append(question)
    return fields, project_links, questions, registration_questionnaire


def get_example_sms_message(fields, registration_questionnaire):
    example_sms = "%s %s" % (registration_questionnaire.form_code, get_example_sms(fields))
    return example_sms


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
def subject_registration_form_preview(request, project_id=None):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)
    if request.method == "GET":
        fields, project_links, questions, registration_questionnaire = _get_registration_form(manager,
            project, project.entity_type)
        example_sms = get_example_sms_message(fields, registration_questionnaire)
        return render_to_response('project/questionnaire_preview_list.html',
                {"questions": questions, 'questionnaire_code': registration_questionnaire.form_code,
                 'project': project, 'project_links': project_links,
                 'example_sms': example_sms, 'org_number': get_organization_telephone_number(request)},
            context_instance=RequestContext(request))


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
def sender_registration_form_preview(request, project_id=None):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)
    if request.method == "GET":
        fields, project_links, questions, registration_questionnaire = _get_registration_form(manager,
            project,
            type_of_subject='reporter')
        datasender_questions = _get_questions_for_datasenders_registration_for_print_preview(questions)
        example_sms = get_example_sms_message(datasender_questions, registration_questionnaire)
        return render_to_response('project/questionnaire_preview_list.html',
                {"questions": datasender_questions, 'questionnaire_code': registration_questionnaire.form_code,
                 'project': project, 'project_links': project_links,
                 'example_sms': example_sms, 'org_number': get_organization_telephone_number(request)},
            context_instance=RequestContext(request))


def get_organization_telephone_number(request):
    organization_settings = utils.get_organization_settings_from_request(request)
    organisation_sms_numbers = organization_settings.get_organisation_sms_number()
    return organisation_sms_numbers if organization_settings.organization.in_trial_mode else organisation_sms_numbers[0]


def _get_subject_form_model(manager, entity_type):
    if is_string(entity_type):
        entity_type = [entity_type]
    return get_form_model_by_entity_type(manager, entity_type)


@login_required(login_url='/login')
@session_not_expired
@is_not_expired
def edit_subject_questionaire(request, project_id=None):
    manager = get_database_manager(request.user)
    project, project_links = _get_project_and_project_link(manager, project_id)

    reg_form = _get_subject_form_model(manager, project.entity_type)
    if reg_form is None:
        reg_form = form_model.get_form_model_by_code(manager, REGISTRATION_FORM_CODE)
    fields = reg_form.fields
    existing_questions = json.dumps(fields, default=field_to_json)
    subject = get_entity_type_info(project.entity_type, manager=manager)
    return render_to_response('project/subject_questionnaire.html',
            {'project': project,
             'project_links': project_links,
             'existing_questions': repr(existing_questions),
             'questionnaire_code': reg_form.form_code,
             'language': reg_form.activeLanguages[0],
             'entity_type': project.entity_type,
             'subject': subject,
             'post_url': reverse(subject_save_questionnaire)},
        context_instance=RequestContext(request))


def append_success_to_context(context, form):
    success = False
    if not len(form.errors):
        success = True
    context.update({'success': success})
    return context


@login_required(login_url='/login')
@session_not_expired
@is_datasender_allowed
@project_has_web_device
@is_not_expired
def create_data_sender_and_web_user(request, project_id=None):
    manager = get_database_manager(request.user)
    project, project_links = _get_project_and_project_link(manager, project_id)
    in_trial_mode = _in_trial_mode(request)

    if request.method == 'GET':
        form = ReporterRegistrationForm(initial={'project_id': project_id})
        return render_to_response('project/register_datasender.html', {
            'project': project, 'project_links': project_links, 'form': form,
            'in_trial_mode': in_trial_mode,'current_language': translation.get_language()},
            context_instance=RequestContext(request))

    if request.method == 'POST':
        org_id = request.user.get_profile().org_id
        form = ReporterRegistrationForm(org_id=org_id, data=request.POST)
        success = False
        try:
            reporter_id, message = process_create_data_sender_form(manager, form, org_id)
            success = True
        except DataObjectAlreadyExists as e:
            message = _("Data Sender with Unique Identification Number (ID) = %s already exists.") % e.data[1]

        if not len(form.errors) and success:
            project.associate_data_sender_to_project(manager, reporter_id)
            if form.requires_web_access():
                email_id = request.POST['email']
                create_single_web_user(org_id=org_id, email_address=email_id, reporter_id=reporter_id,
                    language_code=request.LANGUAGE_CODE)
            UserActivityLog().log(request, action=REGISTERED_DATA_SENDER,
                detail=json.dumps(dict({"Unique ID": reporter_id})), project=project.name)
        if message is not None and success:
            form = ReporterRegistrationForm(initial={'project_id': form.cleaned_data['project_id']})
        context = {'form': form, 'message': message, 'in_trial_mode': in_trial_mode, 'success': success}
        return render_to_response('datasender_form.html',
            context,
            context_instance=RequestContext(request))


def edit_data_sender(request, project_id, reporter_id):
    manager = get_database_manager(request.user)
    reporter_entity = ReporterEntity(get_by_short_code(manager, reporter_id, [REPORTER]))
    project, links = _get_project_and_project_link(manager, project_id, reporter_id)

    if request.method == 'GET':
        location = reporter_entity.location
        geo_code = reporter_entity.geo_code
        form = ReporterRegistrationForm(initial={'project_id': project_id, 'name': reporter_entity.name,
                                                 'telephone_number': reporter_entity.mobile_number, 'location': location
            , 'geo_code': geo_code})
        return render_to_response('project/edit_datasender.html',
                {'project': project, 'reporter_id': reporter_id, 'form': form, 'project_links': links,
                 'in_trial_mode': _in_trial_mode(request)}, context_instance=RequestContext(request))

    if request.method == 'POST':
        org_id = request.user.get_profile().org_id
        form = ReporterRegistrationForm(org_id=org_id, data=request.POST)

        message = None
        if form.is_valid():
            try:
                organization = Organization.objects.get(org_id=org_id)
                current_telephone_number = reporter_entity.mobile_number
                web_player = WebPlayer(manager,
                    LocationBridge(location_tree=get_location_tree(), get_loc_hierarchy=get_location_hierarchy))
                response = web_player.accept(
                    Request(message=_get_data(form.cleaned_data, organization.country_name(), reporter_id),
                        transportInfo=TransportInfo(transport='web', source='web', destination='mangrove'),
                        is_update=True))
                if response.success:
                    if organization.in_trial_mode:
                        update_data_sender_from_trial_organization(current_telephone_number,
                            form.cleaned_data["telephone_number"], org_id)
                    message = _("Your changes have been saved.")

                    detail_dict = {"Unique ID": reporter_id}
                    current_lang = get_language()
                    activate("en")
                    field_mapping = dict(mobile_number="telephone_number")
                    for field in ["geo_code", "location", "mobile_number", "name"]:
                        if getattr(reporter_entity, field) != form.cleaned_data.get(field_mapping.get(field, field)):
                            label = u"%s" % form.fields[field_mapping.get(field, field)].label
                            detail_dict.update({label: form.cleaned_data.get(field_mapping.get(field, field))})
                    activate(current_lang)
                    if len(detail_dict) > 1:
                        detail_as_string = json.dumps(detail_dict)
                        UserActivityLog().log(request, action=EDITED_DATA_SENDER, detail=detail_as_string,
                            project=project.name)
                else:
                    form.update_errors(response.errors)
            except MangroveException as exception:
                message = exception.message

        return render_to_response('edit_datasender_form.html',
                {'project': project, 'form': form, 'reporter_id': reporter_id, 'message': message,
                 'project_links': links, 'in_trial_mode': _in_trial_mode(request)},
            context_instance=RequestContext(request))

def _in_trial_mode(request):
    return utils.get_organization(request).in_trial_mode

def add_link(project):
    add_link_named_tuple = namedtuple("Add_Link", ['url', 'text'])
    if project.entity_type == REPORTER:
        text = _("Add a data sender")
        url = make_data_sender_links(project.id)['register_datasenders_link']
        return add_link_named_tuple(url=url, text=text)
    else:
        text = _("Register a %(subject)s") % {'subject': project.entity_type}
        url = make_subject_links(project.id)['register_subjects_link']
        return add_link_named_tuple(url=url, text=text)

@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
def project_has_data(request, questionnaire_code=None):
    manager = get_database_manager(request.user)
    form_model = get_form_model_by_code(manager, questionnaire_code)
    submissions = successful_submissions(manager, form_model.form_code)
    analyzer = SubmissionAnalyzer(form_model, manager, helper.get_org_id_by_user(request.user), submissions)
    raw_field_values = analyzer.get_raw_values()

    return HttpResponse(encode_json({'has_data': len(raw_field_values) != 0}))