import json
import datetime
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext
from datawinners.accountmanagement.views import session_not_expired
from datawinners.custom_report_router.report_router import ReportRouter
from datawinners.utils import get_organization
from mangrove.form_model.form_model import get_form_model_by_code
from mangrove.transport.submissions import Submission
from mangrove.utils.json_codecs import encode_json

import datawinners.utils as utils

from datawinners.accountmanagement.views import is_datasender
from datawinners.main.utils import get_database_manager, timebox
from datawinners.project.models import Project
from datawinners.accountmanagement.views import is_not_expired
import helper
from project import submission_analyser_helper, header_helper
from project.analysis import Analysis
from project.submission_router import successful_submissions, SubmissionRouter
from project.submission_utils.submission_filter import SubmissionFilter
from project.utils import   make_project_links
from project.Header import SubmissionsPageHeader, Header
from project.analysis_result import AnalysisResult
from datawinners.activitylog.models import UserActivityLog
from project.views import XLS_TUPLE_FORMAT
from submission_list import SubmissionList
from datawinners.common.constant import   DELETED_DATA_SUBMISSION
from datawinners.project.submission_utils.submission_formatter import SubmissionFormatter

performance_logger = logging.getLogger("performance")

@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
# TODO : TW_BLR : delete_submissions should be a separate view with a redirect to this page
# TODO : TW_BLR : view should be renamed to submission logs
# TODO : TW_BLR : should have separate view for ui and data
def project_results(request, project_id=None, questionnaire_code=None):
    manager = get_database_manager(request.user)
    form_model = get_form_model_by_code(manager, questionnaire_code)
    analyzer = _build_submission_list_for_submission_log_page(request, manager, form_model)

    if request.method == 'GET':
        header = SubmissionsPageHeader(form_model)
        result_dict = {"header_list": header.header_list,
                       "header_name_list": repr(encode_json(header.header_list)),
                       "datasender_list": analyzer.get_data_senders(),
                       "subject_list": analyzer.get_subjects()
                       #                       "datasender_list": analysis_result.get_data_senders)
                       #                       "subject_id": analysis_result.get_subjects)
        }
        result_dict.update(project_info(request, manager, form_model, project_id, questionnaire_code))

        return render_to_response('project/results.html', result_dict, context_instance=RequestContext(request))
    if request.method == 'POST':
        field_values = SubmissionFormatter().get_formatted_values_for_list(analyzer.get_raw_values())
        analysis_result = AnalysisResult(field_values, analyzer.get_analysis_statistics(), analyzer.get_data_senders(), analyzer.get_subjects(), analyzer.get_default_sort_order())
        performance_logger.info("Fetch %d submissions from couchdb." % len(analysis_result.field_values))

        if "id_list" in request.POST:
            project_infos = project_info(request, manager, form_model, project_id, questionnaire_code)
            return HttpResponse(_handle_delete_submissions(manager, request, project_infos.get("project").name))
        return HttpResponse(encode_json({'data_list': analysis_result.field_values,
                                         "statistics_result": analysis_result.statistics_result}))

def _build_submission_list_for_submission_log_page(request, manager, form_model):
    submission_type = request.GET.get('type')
    filters = request.POST
    keyword = request.POST.get('keyword', '')
    submission_list = SubmissionList(form_model, manager, helper.get_org_id_by_user(request.user), submission_type, filters,
        keyword)
    return submission_list

def project_info(request, manager, form_model, project_id, questionnaire_code):
    project = Project.load(manager.database, project_id)
    is_summary_report = form_model.entity_defaults_to_reporter()
    rp_field = form_model.event_time_question
    in_trial_mode = _in_trial_mode(request)
    has_rp = rp_field is not None
    is_monthly_reporting = rp_field.date_format.find('dd') < 0 if has_rp else False

    return {"date_format": rp_field.date_format if has_rp else "dd.mm.yyyy",
            "is_monthly_reporting": is_monthly_reporting, "entity_type": form_model.entity_type[0].capitalize(),
            'project_links': (make_project_links(project, questionnaire_code)), 'project': project,
            'questionnaire_code': questionnaire_code, 'in_trial_mode': in_trial_mode,
            'reporting_period_question_text': rp_field.label if has_rp else None,
            'has_reporting_period': has_rp,
            'is_summary_report': is_summary_report}

def _in_trial_mode(request):
    return utils.get_organization(request).in_trial_mode

def _handle_delete_submissions(manager, request, project_name):
    submission_ids = json.loads(request.POST.get('id_list'))
    received_times = delete_submissions_by_ids(manager, request, submission_ids)
    if len(received_times):
        UserActivityLog().log(request, action=DELETED_DATA_SUBMISSION, project=project_name,
            detail=json.dumps({"Date Received": "[%s]" % ", ".join(received_times)}))
        return encode_json({'success_message': ugettext("The selected records have been deleted"), 'success': True})
    return encode_json({'error_message': ugettext("No records deleted"), 'success': False})

def delete_submissions_by_ids(manager, request, submission_ids):
    received_times = []
    for submission_id in submission_ids:
        submission = Submission.get(manager, submission_id)
        received_times.append(datetime.datetime.strftime(submission.created, "%d/%m/%Y %X"))
        submission.void()
        if submission.data_record:
            ReportRouter().delete(get_organization(request).org_id, submission.form_code, submission.data_record.id)
    return received_times


@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
@timebox
def project_data(request, project_id=None, questionnaire_code=None):
    analysis_result = get_analysis_response(request, project_id, questionnaire_code)

    if request.method == "GET":
        return render_to_response('project/data_analysis.html',
            analysis_result,
            context_instance=RequestContext(request))

    elif request.method == "POST":
        return HttpResponse(analysis_result)

@timebox
def get_analysis_response(request, project_id, questionnaire_code):
    manager = get_database_manager(request.user)
    form_model = get_form_model_by_question_code(manager, questionnaire_code)
    filtered_submissions = filter_submissions(form_model, manager, request)
    analysis_result = submission_analyser_helper.get_analysis_result(filtered_submissions, form_model, manager, request)

    performance_logger.info("Fetch %d submissions from couchdb." % len(analysis_result.field_values))
    if request.method == 'GET':
        project_infos = project_info(request, manager, form_model, project_id, questionnaire_code)
        header_info = header_helper.header_info(form_model)

        analysis_result_dict = analysis_result.analysis_result_dict
        analysis_result_dict.update(project_infos)
        analysis_result_dict.update(header_info)

        return analysis_result_dict

    elif request.method == 'POST':
        return encode_json(
            {'data_list': analysis_result.field_values, "statistics_result": analysis_result.statistics_result})


# TODO : Figure out how to mock mangrove methods
def get_form_model_by_question_code(manager, questionnaire_code):
    return get_form_model_by_code(manager, questionnaire_code)

def filter_submissions(form_model, manager, request):
    return SubmissionFilter(request.POST, form_model).filter(successful_submissions(manager, form_model.form_code))

#export_submissions_in_xls_for_submission_log
def _export_submissions_in_xls(request, is_for_submission_log_page):
    questionnaire_code = request.POST.get('questionnaire_code')
    manager = get_database_manager(request.user)
    form_model = get_form_model_by_code(manager, questionnaire_code)

    analyzer = _build_submission_list_for_submission_log_page(request, manager, form_model)
    formatted_values = SubmissionFormatter().get_formatted_values_for_list(analyzer.get_raw_values(), tuple_format=XLS_TUPLE_FORMAT)

    header_list = SubmissionsPageHeader(form_model).header_list if is_for_submission_log_page else Header(form_model).header_list

    exported_data, file_name = _prepare_export_data(request, header_list, formatted_values)

    return _create_excel_response(exported_data, file_name)

#No need of this func
def _export_submissions_in_xls_for_submission_log_page(request):
    return _export_submissions_in_xls(request, True)

@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
@timebox
#export_submissions_for_analysis
def export_data(request):
    return _export_submissions_in_xls_for_analysis_page(request)

def _export_submissions_in_xls_for_analysis_page(request):
    questionnaire_code = request.POST.get('questionnaire_code')
    manager = get_database_manager(request.user)
    form_model = get_form_model_by_code(manager, questionnaire_code)
    analyzer = _build_submission_analyzer_for_analysis(request, manager, form_model)

    #this will have all answers
    formatted_values = SubmissionFormatter().get_formatted_values_for_list(analyzer.get_raw_values(),tuple_format=XLS_TUPLE_FORMAT)

    header_list = Header(form_model).header_list

    exported_data, file_name = _prepare_export_data(request, header_list, formatted_values)

    return _create_excel_response(exported_data, file_name)

def _build_submission_analyzer_for_analysis(request, manager, form_model):
    #Analysis page wont hv any type since it has oly success submission data.
    submission_type = request.GET.get('type',None)
    filters = request.POST
    return Analysis(form_model,manager,helper.get_org_id_by_user(request.user), submission_type, filters)

@login_required(login_url='/login')
@session_not_expired
@is_datasender
@is_not_expired
def export_log(request):
    return _export_submissions_in_xls_for_submission_log_page(request)


def _create_excel_response(raw_data_list, file_name):
    response = HttpResponse(mimetype="application/vnd.ms-excel")
    from django.template.defaultfilters import slugify

    response['Content-Disposition'] = 'attachment; filename="%s.xls"' % (slugify(file_name),)
    wb = utils.get_excel_sheet(raw_data_list, 'data_log')
    wb.save(response)
    return response

def _prepare_export_data(request, header_list, formatted_values):
    submission_log_type = request.GET.get('type', None)
    exported_data = _get_exported_data(header_list, formatted_values, submission_log_type)

    suffix = submission_log_type + '_log' if submission_log_type else 'analysis'
    project_name = request.POST.get(u"project_name")
    file_name = "%s_%s" % (project_name, suffix)
    return exported_data, file_name

def _get_exported_data(header, formatted_values, submission_log_type):
    data = [header] + formatted_values
    submission_id_col = 0
    status_col = 3
    reply_sms_col = 4
    if submission_log_type in [SubmissionRouter.ALL, SubmissionRouter.DELETED]:
        return [each[submission_id_col+1:reply_sms_col]+each[reply_sms_col+1:] for each in data]
    elif submission_log_type in [SubmissionRouter.ERROR]:
        return [each[submission_id_col+1:status_col]+each[status_col+1:] for each in data]
    elif submission_log_type in [SubmissionRouter.SUCCESS]:
        return [each[submission_id_col+1:status_col]+each[reply_sms_col+1:] for each in data]
    else:
        return [each[1:] for each in data]

