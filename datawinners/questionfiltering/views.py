# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

from collections import defaultdict
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
from mangrove.datastore.aggregrate import Sum
from mangrove.datastore.entity import get_by_short_code

from mangrove.datastore.data import EntityAggregration, QuestionAggregation
from mangrove.datastore.queries import get_entity_count_for_type, get_non_voided_entity_count_for_type
from mangrove.errors.MangroveException import QuestionCodeAlreadyExistsException, EntityQuestionAlreadyExistsException, DataObjectAlreadyExists, DataObjectNotFound, QuestionAlreadyExistsException, MangroveException
from mangrove.form_model import form_model
from mangrove.form_model.field import field_to_json, SelectField
from mangrove.form_model.form_model import get_form_model_by_code, FormModel, REGISTRATION_FORM_CODE, get_form_model_by_entity_type, REPORTER
from mangrove.transport.facade import TransportInfo, Request
from mangrove.transport.player.player import WebPlayer
from mangrove.transport.submissions import Submission, get_submissions, submission_count
from mangrove.utils.dates import convert_date_string_in_UTC_to_epoch
from mangrove.datastore import aggregrate as aggregate_module
from mangrove.utils.json_codecs import encode_json
from mangrove.utils.types import is_empty, is_string
from mangrove.transport import Channel

from datawinners.accountmanagement.views import is_datasender
from datawinners.main.utils import get_database_manager
from datawinners.project.models import Project
from datawinners.accountmanagement.views import is_not_expired
from mangrove.transport.player.parser import XlsDatasenderParser
from activitylog.models import UserActivityLog
from datawinners.project.views import make_project_links, _in_trial_mode, _get_aggregated_data
from project import helper
from project.views import _load_data, _format_data_for_presentation

def _get_field_index(fields, field_name):
    field_name_list = [field.name for field in fields]
    return field_name_list.index(field_name)

def _transform_data_to_list_of_records_v2(data_dictionary, fields):
    result = defaultdict(list)
    clone_of_data_dict = {key : value for key, value in data_dictionary.items()}
    for (entity_id, field_name), value_list in data_dictionary.items():
        for field in fields:
            value = clone_of_data_dict.get((entity_id, field.name), None)
            if value:
                result[entity_id].append(value.pop(0))
            else:
                clone_of_data_dict.pop((entity_id, field.name))
    list_of_result = [value for key, value in result.items()]
    return result, list_of_result



def _transform_data_to_list_of_records(data_dictionary, fields):
    result = defaultdict(dict)
    result_transformed = defaultdict(list)
    grand_total = None
    dict_of_entity_index = dict()
    entity_index = 0
    for (entity_id, field_name), value_list in data_dictionary.items():

        if entity_id == 'GrandTotals':
            result[entity_id][field_name] = [Sum('').reduce(value_list)]
            grand_total = [entity_id, [Sum('').reduce(value_list)]]
        else:
            if not dict_of_entity_index.has_key(entity_id):
                dict_of_entity_index[entity_id] = entity_index
                entity_index += 1
            result_transformed[field_name].extend([(dict_of_entity_index[entity_id], val) for val in value_list])
            result[entity_id][field_name] = value_list

    list_of_result = None
    for field_name, value_list in result_transformed.items():
        if not list_of_result:
            list_of_result = [[None for ele in result_transformed] for val in value_list]
        for (entity_index, each) in value_list:
            field_index = _get_field_index(fields, field_name)
            list_of_result[entity_index][field_name]= each
    if grand_total:
        list_of_result.append(grand_total)
    return result, list_of_result


def _load_all_data(manager, form_model):
    data_dictionary = aggregate_module.get_by_form_code_python(manager, form_model.form_code,  aggregate_on=QuestionAggregation())
    fields = form_model.fields
    return _transform_data_to_list_of_records(data_dictionary, fields)


def get_question_filter_options(fields):
    question_filter_options = []
    for field in fields:
        if isinstance(field, SelectField):
            question_filter_options.append(field.options)
        else:
            question_filter_options.append([])
    return question_filter_options


def _format_data_for_filter_presentation(entity_values_dict, entity_values_list, form_model):
    headers = helper.get_headers(form_model)
    question_filter_options = get_question_filter_options(form_model.fields[1:])
    field_values, grand_totals = helper.get_all_values(entity_values_dict, form_model)
    field_values = entity_values_list
    return field_values, headers, question_filter_options, grand_totals


def _get_field_based_data(form_model, manager):
    entity_values_dict, entity_values_list = _load_all_data(manager, form_model)
    return _format_data_for_filter_presentation(entity_values_dict, entity_values_list, form_model)


@login_required(login_url='/login')
@is_datasender
@is_not_expired
def question_filter(request, project_id=None, questionnaire_code=None):
    manager = get_database_manager(request.user)
    project = Project.load(manager.database, project_id)
    form_model = get_form_model_by_code(manager, questionnaire_code)
    field_values, header_list, question_filter_options, grand_totals = _get_field_based_data(form_model, manager)

    if request.method == "GET":
        in_trial_mode = _in_trial_mode(request)
        return render_to_response('questionfiltering/data_analysis.html',
                {"entity_type": form_model.entity_type[0], "data_list": repr(encode_json(field_values)),
                 "header_list": header_list, "question_filter_options": question_filter_options, 'grand_totals': grand_totals, 'project_links': (
                make_project_links(project, questionnaire_code)), 'project': project, 'in_trial_mode': in_trial_mode}
            ,
            context_instance=RequestContext(request))
    if request.method == "POST":
        return HttpResponse(encode_json({'data': field_values, 'footer': grand_totals}))