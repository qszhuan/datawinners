# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from mangrove.form_model.field import  SelectField
from mangrove.form_model.form_model import get_form_model_by_code
from mangrove.datastore import aggregrate as aggregate_module
from mangrove.utils.json_codecs import encode_json

from datawinners.accountmanagement.views import is_datasender
from datawinners.main.utils import get_database_manager
from datawinners.project.models import Project
from datawinners.accountmanagement.views import is_not_expired
from datawinners.project.views import make_project_links, _in_trial_mode
from project import helper

def _transform_data_to_list_of_records(data_dictionary):
    entity = defaultdict(dict)
    for field_name, values in data_dictionary.items():
        i = 0
        for value in values:
            entity[i][field_name] = value
            i += 1
    return entity

def _load_all_data(manager, form_model):
    data_dictionary = aggregate_module.get_by_form_code_python(manager, form_model.form_code)
    return _transform_data_to_list_of_records(data_dictionary)


def get_question_filter_options(fields):
    question_filter_options = []
    for field in fields:
        if isinstance(field, SelectField):
            question_filter_options.append(field.options)
        else:
            question_filter_options.append([])
    return question_filter_options


def _format_data_for_filter_presentation(entity_values_dict, form_model):
    headers = helper.get_headers(form_model)
    question_filter_options = get_question_filter_options(form_model.fields[1:])
    field_values, grand_totals = helper.get_all_values(entity_values_dict, form_model)
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