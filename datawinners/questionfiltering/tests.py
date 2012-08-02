"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from collections import OrderedDict, defaultdict
import random
import unittest
import commands
from mangrove.contrib.registration import GLOBAL_REGISTRATION_FORM_CODE
from mangrove.datastore.database import get_db_manager, _delete_db_and_remove_db_manager
from mangrove.bootstrap.initializer import run
from mangrove.datastore.datadict import create_datadict_type
from mangrove.datastore.entity_type import define_type
from mangrove.errors.MangroveException import EntityTypeAlreadyDefined
from mangrove.form_model.field import TextField, SelectField
from mangrove.form_model.form_model import FormModel, MOBILE_NUMBER_FIELD_CODE, FormSubmissionFactory, MOBILE_NUMBER_FIELD, get_form_model_by_code
from mangrove.form_model.validation import TextLengthConstraint, NumericRangeConstraint
from mangrove.transport.facade import TransportInfo, Request
from mangrove.transport.player.player import SMSPlayer
from mock import Mock

from datawinners.questionfiltering.views import _load_all_data, _format_data_for_filter_presentation, _transform_data_to_list_of_records, _transform_data_to_list_of_records_v2


class QuestionFilteringTest(unittest.TestCase):
    def setUp(self):
        commands.getoutput('curl -X DELETE http://localhost:5984/test_question_filtering')
        self.clinic_form_code = 'clinic_form'
        self.dbm = get_db_manager('http://localhost:5984', 'test_question_filtering')
        run(self.dbm)
        self.register_report(self.get_reporter_questionnaire_form())
        self.form = self.get_clinic_questionnaire_form()
        text = self.form.form_code
        clinic_return_data = self.register_clinic(self.form.id)
        self.clinic_id = clinic_return_data
        text += ' ' + self.clinic_id + ' c'
        self.submit_answer_for_clinic(text)
        self.submit_answer_for_clinic(text)

    def tearDown(self):
        _delete_db_and_remove_db_manager(self.dbm)

    def get_clinic_entity_type(self):
        entity_type_name = ['clinic']
        try:
            define_type(self.dbm, entity_type_name)
        except EntityTypeAlreadyDefined:
            pass

        return entity_type_name

    def get_clinic_questionnaire_form(self):
        question1 = TextField(code="q1", label=u"which clinic are you reporting on?",
            name="which clinic are you reporting on?", ddtype=self.get_ddtype(),
            constraints=[TextLengthConstraint(min=1, max=50)], entity_question_flag=True)
        question2 = SelectField(code="q2", label=u"what is your blood type?", options=['A', 'B', 'AB', 'O', 'others'],
            ddtype=self.get_ddtype(), name="what is your blood type?",
            single_select_flag=True)

        question_set = [question1, question2]
        form_model = FormModel(dbm=self.dbm, name="clinic_questionnaire_form", label="clinic_questionnaire",
            form_code=self.clinic_form_code,
            entity_type=self.get_clinic_entity_type()
            , fields=question_set)
        form_model.save()
        return form_model

    def get_ddtype(self):
        return create_datadict_type(self.dbm, "type", None, "string", None, None, None)

    def get_reporter_questionnaire_form(self):
        question1 = TextField(name="reporter name", code="q1", label=u"what's your name?", ddtype=self.get_ddtype(),
            constraints=[TextLengthConstraint(min=1, max=50)], entity_question_flag=True)
        question2 = TextField(name=MOBILE_NUMBER_FIELD, code=MOBILE_NUMBER_FIELD_CODE,
            label=u"what's your mobile number?", ddtype=self.get_ddtype(),
            constraints=[TextLengthConstraint(min=11, max=11)])
        question3 = TextField(name="reporter age", code="q3", label=u"what's your age?", ddtype=self.get_ddtype(),
            constraints=[NumericRangeConstraint(min=18, max=150)])
        question4 = TextField(name="reporter email", code="q4", label=u"what's your email?", ddtype=self.get_ddtype(),
            constraints=[TextLengthConstraint(min=5, max=100)])

        form_model = FormModel(dbm=self.dbm, name="reporter_questionnaire_form", label="reporter_questionnaire",
            form_code='reporter' + str(random.randint(100, 500)),
            entity_type=['reporter'], is_registration_model=True
            , fields=[question1, question2, question3, question4])
        return form_model.save()

    def register_report(self, form_id):
        '''
        register a report and return the report id
        '''
        form_returned = FormModel.get(self.dbm, form_id)
        id = str(random.randint(0, 1000))
        answers = {
            'q1': 'reporter_' + id,
            MOBILE_NUMBER_FIELD_CODE: '13811816914',
            'q3': '24',
            'q4': 'edfeng@gmail.com'
        }
        form_submission = FormSubmissionFactory().get_form_submission(form_returned, OrderedDict(answers))
        form_returned.bind(form_submission._cleaned_data)
        cleaned_data, errors = form_returned.validate_submission(form_submission._cleaned_data)

        if len(errors) > 0:
            print errors
            raise Exception('From data is invalid')
        else:
            print 'Form data is valid'

        form_returned.save()
        return form_submission.save(self.dbm)


    def register_clinic(self, form_id):
        submission = FormSubmissionFactory().get_form_submission(
            get_form_model_by_code(self.dbm, GLOBAL_REGISTRATION_FORM_CODE),
            OrderedDict({'t': ['clinic'], 's': '1234'}))
        submission.save(self.dbm)
        return '1234'

    def submit_answer_for_clinic(self, text):
        transport_info = TransportInfo(transport="sms", source="13811816914", destination="5678")
        sms_player = SMSPlayer(self.dbm)
        return sms_player.accept(Request(transportInfo=transport_info, message=text)).errors


    def test_should_load_all_data(self):
        form_model = self.form

        dict_data = _load_all_data(self.dbm, form_model)

        self.assertEqual(len(dict_data), 1)
        self.assertEqual(len(dict_data.values()[0]), 2)

    def test_should_load_question_filter_options(self):
        form_model = self.form
        data_dict, data_list = _load_all_data(self.dbm, form_model)
        formated_data = _format_data_for_filter_presentation(data_dict, data_list, form_model)

        self.assertEqual(len(formated_data[2][0]), 5)


    def _build_field_set(self):
        fields = []
        for index in range(1, 3):
            field = Mock()
            field.name = 'q_' + str(index)
            fields.append(field)
        return fields

    def test_should_transform_data_into_list_of_data_record(self):
        fields = self._build_field_set()

        data_dictionary = {('cid1', 'q_1'): ['a', 'b'], ('cid1', 'q_2'): ['c', 'd'], ('cid2', 'q_1'): ['aa'],
                           ('cid2', 'q_2'): ['bb'], ('cid3', 'q_1'): ['aaa'], ('cid3', 'q_2'): ['bbb']}

        result, list_of_result = _transform_data_to_list_of_records(data_dictionary, fields)

        self.assertEqual(len(list_of_result), 4)
        self.assertEqual(list_of_result[0], ['a', 'c'])
        self.assertEqual(list_of_result[1], ['b', 'd'])
        self.assertEqual(list_of_result[2], ['aa', 'bb'])
        self.assertEqual(list_of_result[3], ['aaa', 'bbb'])

    def test_should_transformed_data_into_list_of_data_record_when_subject_have_multi_submission(self):
        fields = self._build_field_set()

        data_dictionary = {('cid1', 'q_1'): ['a', 'b'], ('cid1', 'q_2'): ['c', 'd'], ('cid2', 'q_1'): ['aa'],
                           ('cid2', 'q_2'): ['bb'], ('cid3', 'q_1'): ['aaa'], ('cid3', 'q_2'): ['bbb']}

        result, list_of_result = _transform_data_to_list_of_records_v2(data_dictionary, fields)

        self.assertEqual(len(list_of_result), 4)
        self.assertEqual(list_of_result[0], ['a', 'c'])
        self.assertEqual(list_of_result[1], ['b', 'd'])
        self.assertEqual(list_of_result[2], ['aa', 'bb'])
        self.assertEqual(list_of_result[3], ['aaa', 'bbb'])


    def test_should_transformed_data_into_list_of_data_record_when_subject_have_only_one_submission(self):
            fields = self._build_field_set()

            data_dictionary = {('cid1', 'q_1'): ['a'], ('cid1', 'q_2'): ['c'], ('cid2', 'q_1'): ['aa'],
                               ('cid2', 'q_2'): ['bb'], ('cid3', 'q_1'): ['aaa'], ('cid3', 'q_2'): ['bbb']}

            result, list_of_result = _transform_data_to_list_of_records_v2(data_dictionary, fields)

            self.assertEqual(len(list_of_result), 3)
            self.assertEqual(list_of_result[0], ['a', 'c'])
            self.assertEqual(list_of_result[1], ['aa', 'bb'])
            self.assertEqual(list_of_result[2], ['aaa', 'bbb'])





