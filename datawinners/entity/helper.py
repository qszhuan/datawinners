# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from mangrove.contrib.deletion import ENTITY_DELETION_FORM_CODE

from mangrove.datastore.datadict import get_datadict_type_by_slug,\
    create_datadict_type
from mangrove.datastore.entity import get_by_short_code_include_voided
from mangrove.errors import MangroveException
from mangrove.form_model.field import TextField, HierarchyField, GeoCodeField, TelephoneNumberField
from mangrove.form_model.form_model import FormModel, NAME_FIELD,\
    NAME_FIELD_CODE, LOCATION_TYPE_FIELD_NAME, LOCATION_TYPE_FIELD_CODE,\
    GEO_CODE, MOBILE_NUMBER_FIELD, MOBILE_NUMBER_FIELD_CODE,\
    SHORT_CODE_FIELD, REGISTRATION_FORM_CODE,\
    ENTITY_TYPE_FIELD_CODE, GEO_CODE_FIELD_NAME, SHORT_CODE, REPORTER
from mangrove.form_model.validation import TextLengthConstraint,\
    RegexConstraint
from mangrove.transport.player.player import WebPlayer
from mangrove.utils.types import  is_sequence, is_not_empty
import re
from mangrove.errors.MangroveException import NumberNotRegisteredException,\
    DataObjectNotFound
from mangrove.transport.reporter import find_reporter_entity
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _, get_language
from datawinners.accountmanagement.models import Organization,\
    DataSenderOnTrialAccount, NGOUserProfile
from datawinners.location.LocationTree import get_location_tree
from mangrove.transport import Request, TransportInfo
from datawinners.messageprovider.message_handler import\
    get_success_msg_for_registration_using
from datawinners.location.LocationTree import get_location_hierarchy
from datawinners.project.models import get_all_projects, Project
from datawinners.submission.location import LocationBridge
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import  get_current_site
from django.core.mail.message import EmailMessage
from django.template.loader import render_to_string
from django.utils.http import int_to_base36
from datawinners.settings import HNI_SUPPORT_EMAIL_ID, EMAIL_HOST_USER
import logging

websubmission_logger = logging.getLogger("websubmission")
FIRSTNAME_FIELD = "firstname"
FIRSTNAME_FIELD_CODE = "f"

def remove_hyphens(telephone_number):
    return re.sub('[- \(\)+]', '', smart_unicode(telephone_number))


def unique(dbm, telephone_number):
    telephone_number = remove_hyphens(telephone_number)
    try:
        find_reporter_entity(dbm, telephone_number)
    except NumberNotRegisteredException:
        return True
    return False


def _get_or_create_data_dict(dbm, name, slug, primitive_type, description=None):
    try:
        ddtype = get_datadict_type_by_slug(dbm, slug)
    except DataObjectNotFound:
        ddtype = create_datadict_type(dbm=dbm, name=name, slug=slug,
            primitive_type=primitive_type, description=description)
    return ddtype


def _create_constraints_for_mobile_number():
    mobile_number_length = TextLengthConstraint(max=15)
    mobile_number_pattern = RegexConstraint(reg='^[0-9]+$')
    mobile_constraints = [mobile_number_length, mobile_number_pattern]
    return mobile_constraints


def _generate_form_code(manager, prefix, rank=''):
    form_code = "%s%s" % (prefix, rank)
    rows = manager.load_all_rows_in_view("questionnaire", key=form_code)
    if len(rows) > 0:
        rank = 1 if rank is '' else rank + 1
        form_code = _generate_form_code(manager, prefix, rank)
    return form_code


def _create_registration_form(manager, entity_name=None, form_code=None, entity_type=None):
    code_generator = question_code_generator()
    location_type = _get_or_create_data_dict(manager, name='Location Type', slug='location', primitive_type='string')
    geo_code_type = _get_or_create_data_dict(manager, name='GeoCode Type', slug='geo_code', primitive_type='geocode')
    name_type = _get_or_create_data_dict(manager, name='Name', slug='name', primitive_type='string')
    mobile_number_type = _get_or_create_data_dict(manager, name='Mobile Number Type', slug='mobile_number',
        primitive_type='string')

    question1 = TextField(name=FIRSTNAME_FIELD, code=code_generator.next(),
        label=_("What is the %(entity_type)s's first name?") % {'entity_type': entity_name},
        defaultValue="some default value",  ddtype=name_type,
        instruction=_("Enter a %(entity_type)s first name") % {'entity_type': entity_name})

    question2 = TextField(name=NAME_FIELD, code=code_generator.next(),
        label=_("What is the %(entity_type)s's last name?") % {'entity_type': entity_name},
        defaultValue="some default value", ddtype=name_type,
        instruction=_("Enter a %(entity_type)s last name") % {'entity_type': entity_name})
    question3 = HierarchyField(name=LOCATION_TYPE_FIELD_NAME, code=code_generator.next(),
        label=_("What is the %(entity_type)s's location?") % {'entity_type': entity_name},
        ddtype=location_type, instruction=unicode(_("Enter a region, district, or commune")))
    question4 = GeoCodeField(name=GEO_CODE_FIELD_NAME, code=code_generator.next(),
        label=_("What is the %(entity_type)s's GPS co-ordinates?") % {'entity_type': entity_name},
        ddtype=geo_code_type,
        instruction=unicode(_("Answer must be GPS co-ordinates in the following format: xx.xxxx,yy.yyyy Example: -18.1324,27.6547 ")))
    question5 = TelephoneNumberField(name=MOBILE_NUMBER_FIELD, code=code_generator.next(),
        label=_("What is the %(entity_type)s's mobile telephone number?") % {'entity_type': entity_name},
        defaultValue="some default value", ddtype=mobile_number_type,
        instruction=_(
            "Enter the (%(entity_type)s)'s number with the country code and telephone number. Example: 261333745269") % {
            'entity_type': entity_name}, constraints=(
            _create_constraints_for_mobile_number()))
    question6 = TextField(name=SHORT_CODE_FIELD, code=code_generator.next(),
        label=_("What is the %(entity_type)s's Unique ID Number?") % {'entity_type': entity_name},
        defaultValue="some default value", ddtype=name_type,
        instruction=unicode(_("Enter an id, or allow us to generate it")),
        entity_question_flag=True,
        constraints=[TextLengthConstraint(max=20)], required=False)
    questions = [question1, question2, question3, question4, question5, question6]

    form_model = FormModel(manager, name=entity_name, form_code=form_code, fields=questions, is_registration_model=True,
        entity_type=entity_type)
    return form_model


def create_registration_form(manager, entity_name):
    if is_sequence(entity_name):
        entity_name = entity_name[0]
    prefix = entity_name.lower()[:3]
    form_code = _generate_form_code(manager, prefix)
    form_model = _create_registration_form(manager, entity_name, form_code, [entity_name])
    form_model.save()
    return form_model

def get_country_appended_location(location_hierarchy, country):
    location_hierarchy_split = location_hierarchy.split(',')
    country_already_appended = (location_hierarchy_split[len(location_hierarchy_split)-1].strip() == country)
    return ','.join([x.strip() for x in location_hierarchy_split])  if location_hierarchy is None or country_already_appended else ','.join(location_hierarchy_split) + ',' + country

def _get_data(form_data, country,reporter_id=None):
    #TODO need to refactor this code. The master dictionary should be maintained by the registration form model
    mapper = {'telephone_number': MOBILE_NUMBER_FIELD_CODE, 'geo_code': GEO_CODE, 'Name': NAME_FIELD_CODE,
              'location': LOCATION_TYPE_FIELD_CODE, 'short_code':SHORT_CODE_FIELD}
    data = dict()
    data[mapper['telephone_number']] = form_data.get('telephone_number')
    data[mapper['location']] = get_country_appended_location(form_data.get('location'), country)
    data[mapper['geo_code']] = form_data.get('geo_code')
    data[mapper['Name']] = form_data.get('name')
    data['form_code'] = REGISTRATION_FORM_CODE
    data[ENTITY_TYPE_FIELD_CODE] = REPORTER
    data['s'] = reporter_id
    return data


def add_data_sender_to_trial_organization(telephone_number, org_id):
    data_sender = DataSenderOnTrialAccount.objects.model(mobile_number=telephone_number,
        organization=Organization.objects.get(org_id=org_id))
    data_sender.save()

def update_data_sender_from_trial_organization(old_telephone_number,new_telephone_number, org_id):
    data_sender = DataSenderOnTrialAccount.objects.model(mobile_number=old_telephone_number,
        organization=Organization.objects.get(org_id=org_id))
    data_sender.delete()
    add_data_sender_to_trial_organization(new_telephone_number,org_id=org_id)

def process_create_data_sender_form(dbm, form, org_id):
    message = None
    data_sender_id = None

    if form.is_valid():
        try:
            organization = Organization.objects.get(org_id=org_id)
            if organization.in_trial_mode:
                add_data_sender_to_trial_organization(form.cleaned_data["telephone_number"], org_id)
            web_player = WebPlayer(dbm, LocationBridge(location_tree=get_location_tree(), get_loc_hierarchy=get_location_hierarchy))
            reporter_id = form.cleaned_data["short_code"] if form.cleaned_data != "" else None
            request = Request(message=_get_data(form.cleaned_data, organization.country_name(), reporter_id),
                transportInfo=TransportInfo(transport='web', source='web', destination='mangrove'))

            response = web_player.accept(request, logger=websubmission_logger)
            if response.success:
                data_sender_id = response.short_code
                message = get_success_msg_for_registration_using(response, "web")
            else:
                form.update_errors(response.errors)

        except MangroveException as exception:
            message = exception.message

    return data_sender_id,message


def question_code_generator():
    i = 1
    while 1:
        code = 'q' + str(i)
        yield code
        i += 1


def delete_entity_instance(manager, all_ids, entity_type, transport_info):
    web_player = WebPlayer(manager)
    for entity_id in all_ids:
        message = {ENTITY_TYPE_FIELD_CODE: entity_type,
                   SHORT_CODE: entity_id,
                   'form_code': ENTITY_DELETION_FORM_CODE}
        mangrove_request = Request(message, transport_info)
        web_player.accept(mangrove_request)

def delete_datasender_users_if_any(all_ids, organization):
    for id in all_ids:
        profiles = NGOUserProfile.objects.filter(org_id=organization.org_id,reporter_id=id)
        if is_not_empty(profiles):
            profiles[0].user.delete()

def delete_datasender_for_trial_mode(manager, all_ids, entity_type):
    for entity_id in all_ids:
        entity_to_be_deleted = get_by_short_code_include_voided(manager, entity_id, [entity_type])
        DataSenderOnTrialAccount.objects.get(mobile_number=entity_to_be_deleted.value(MOBILE_NUMBER_FIELD)).delete()

def delete_datasender_from_project(manager, all_ids):
    for entity_id in all_ids:
        associated_projects = get_all_projects(manager, data_sender_id=entity_id)
        for associated_project in associated_projects:
            project = Project.load(manager.database, associated_project['value']['_id'])
            project.delete_datasender(manager, entity_id)

def add_imported_data_sender_to_trial_organization(request, imported_datasenders, all_data_senders, index=0):
    org_id = request.user.get_profile().org_id
    organization = Organization.objects.get(org_id=org_id)
    if organization.in_trial_mode:
        mobile_number_index = index
        for ds in all_data_senders:
            if ds['short_code'] in imported_datasenders:
                add_data_sender_to_trial_organization(ds['cols'][mobile_number_index], org_id)

def send_email_to_data_sender(user, language_code, request=None, type="activation"):
    site = get_current_site(request)
    ctx_dict = {
        'domain': site.domain,
        'uid': int_to_base36(user.id),
        'user': user,
        'token': default_token_generator.make_token(user),
        'protocol': 'http',
        'site': site,
        }
    types = dict({"activation":
                dict({"subject":'activatedatasenderemail/activation_email_subject_for_data_sender_account_',
                      "subject_param":False,
                      "template": 'activatedatasenderemail/activation_email_for_data_sender_account_'}),
                   "created_user":
                dict({"subject": 'registration/created_user_email_subject_',
                      "subject_param":site.domain,
                      "template": 'registration/created_user_email_'})})
    if type not in types:
        return
    action = types.get(type)
    subject = render_to_string(action.get("subject") + language_code + '.txt')
    subject = ''.join(subject.splitlines())
    if action.get("subject_param"):
        subject = subject % action.get("subject_param")

    if request is not None:
        ctx_dict.update({"creator_user": request.user.first_name})

    message = render_to_string(action.get("template") + language_code + '.html', ctx_dict)
    email = EmailMessage(subject, message, EMAIL_HOST_USER, [user.email], [HNI_SUPPORT_EMAIL_ID])
    email.content_subtype = "html"
    email.send()