# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import date

import unittest
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.forms.forms import Form
from mangrove.datastore.datadict import DataDictType
from mangrove.form_model.field import TextField, DateField
from entity.forms import ReporterRegistrationForm
from mangrove.datastore.database import DatabaseManager
from mangrove.form_model.form_model import FormModel
from mangrove.transport.submissions import Submission
from mock import Mock, patch
from datawinners.project.models import Reminder, RemindTo, ReminderMode, Project
from datawinners.project.views import _format_reminders, make_data_sender_links, add_link
from project.models import ProjectState
from project.preview_views import get_sms_preview_context, get_questions, get_web_preview_context, add_link_context
from project.submission_router import SubmissionRouter
from project.submission_views import delete_submissions_by_ids, _prepare_export_data
from project.utils import make_subject_links
from project.views import get_form_model_and_template, get_preview_and_instruction_links_for_questionnaire, append_success_to_context, formatted_data
from project.wizard_view import get_preview_and_instruction_links, get_reporting_period_field
from questionnaire.questionnaire_builder import get_max_code

class TestProjectViews( unittest.TestCase ):
    def test_should_return_reminders_in_the_required_format(self):
        reminder1 = Mock( spec=Reminder )
        reminder1.message = ''
        reminder1.id = '1'
        reminder1.remind_to = RemindTo.DATASENDERS_WITHOUT_SUBMISSIONS
        reminder1.reminder_mode = ReminderMode.ON_DEADLINE
        reminder1.day = 0

        reminder2 = Mock( spec=Reminder )
        reminder2.message = ''
        reminder2.id = '2'
        reminder2.remind_to = RemindTo.ALL_DATASENDERS
        reminder2.reminder_mode = ReminderMode.BEFORE_DEADLINE
        reminder2.day = 2

        reminders = [reminder1, reminder2]
        formated_reminders = _format_reminders( reminders, 'test_project' )

        self.assertEqual( 2, len( formated_reminders ) )
        self.assertEqual( '/project/delete_reminder/test_project/1/', formated_reminders[0]['delete_link'] )

        self.assertEqual( 'On Deadline', formated_reminders[0]['when'] )
        self.assertEqual( 'Datasenders Without Submissions', formated_reminders[0]['to'] )

        self.assertEqual( '2 days Before Deadline', formated_reminders[1]['when'] )
        self.assertEqual( 'All Datasenders', formated_reminders[1]['to'] )

    def test_should_return_subject_project_links(self):
        project_id = "1"
        subject_links = make_subject_links(project_id)
        self.assertEqual( reverse( 'subjects', args=[project_id] ), subject_links['subjects_link'] )
        self.assertEqual( reverse( 'edit_subject_questionaire', args=[project_id] ), subject_links['subjects_edit_link'] )
        self.assertEqual( reverse( 'subject_registration_form_preview', args=[project_id] ),
                          subject_links['subject_registration_preview_link'] )
        self.assertEqual( reverse( 'registered_subjects', args=[project_id] ), subject_links['registered_subjects_link'] )
        self.assertEqual( reverse( 'subject_questionnaire', args=[project_id] ),
                          subject_links['register_subjects_link'] )

    def test_should_return_datasender_project_links(self):
        project_id = "1"
        datasender_links = make_data_sender_links( project_id )
        self.assertEqual( reverse( 'all_datasenders' ), datasender_links['datasenders_link'] )
        self.assertEqual( reverse( 'create_data_sender_and_web_user', args=[project_id] ),
                          datasender_links['register_datasenders_link'] )
        self.assertEqual( reverse( 'registered_datasenders', args=[project_id] ),
                          datasender_links['registered_datasenders_link'] )


    def test_for_websubmission_on_subjects_should_provide_add_links(self):
        project = Mock( spec=Project )
        project.id = "1"
        project.entity_type = "clinic"
        link = add_link( project )
        self.assertEqual( reverse( 'subject_questionnaire', args=[project.id] ), link.url )
        self.assertEqual( 'Register a clinic', link.text )

    def test_for_websubmission_on_datasenders_should_provide_add_links(self):
        project = Mock( spec=Project )
        project.id = "1"
        project.entity_type = "reporter"
        link = add_link( project )
        self.assertEqual( reverse( 'create_data_sender_and_web_user', args=[project.id] ), link.url )
        self.assertEqual( 'Add a data sender', link.text )

    def test_should_get_correct_template_for_non_data_sender(self):
        request = Mock( )
        request.user = Mock( spec=User )
        manager = Mock( spec=DatabaseManager )
        manager.database = dict( )
        project = Project( project_type="survey", entity_type="clinic", state=ProjectState.ACTIVE )

        with patch.object( FormModel, "get" ) as get_form_model:
            get_form_model.return_value = {}
            is_data_sender = False
            subject = False
            form_model, template = get_form_model_and_template( manager, project, is_data_sender, subject )
            self.assertEquals( template, "project/web_questionnaire.html" )

    def test_should_get_correct_template_for_data_sender(self):
        request = Mock( )
        request.user = Mock( spec=User )
        manager = Mock( spec=DatabaseManager )
        manager.database = dict( )
        project = Project( project_type="survey", entity_type="clinic", state=ProjectState.ACTIVE )

        with patch.object( FormModel, "get" ) as get_form_model:
            get_form_model.return_value = {}
            is_data_sender = True
            subject = False
            form_model, template = get_form_model_and_template( manager, project, is_data_sender, subject )
            self.assertEquals( template, "project/data_submission.html" )

    def test_should_get_correct_template_for_subject_questionnaire(self):
        request = Mock( )
        request.user = Mock( spec=User )
        manager = Mock( spec=DatabaseManager )
        manager.database = dict( )
        project = Project( project_type="survey", entity_type="clinic", state=ProjectState.ACTIVE )

        with patch.object( FormModel, "get" ) as get_form_model:
            get_form_model.return_value = {}
            with patch( "project.views.get_form_model_by_entity_type" ) as get_subject_form:
                get_subject_form.return_value = {}
                is_data_sender = False
                subject = True
                form_model, template = get_form_model_and_template( manager, project, is_data_sender, subject )
                self.assertEquals( template, "project/register_subject.html" )


    def test_should_get_preview_and_instruction_links(self):
        with patch( "project.wizard_view.reverse" ) as reverse:
            reverse.side_effect = lambda *args, **kw: "/project/%s" % args[0]
            links = get_preview_and_instruction_links( )
            self.assertEqual( links["sms_preview"], "/project/sms_preview" )
            self.assertEqual( links["web_preview"], "/project/web_preview" )
            self.assertEqual( links["smart_phone_preview"], "/project/smart_phone_preview" )

    def test_should_get_correct_context_for_sms_preview(self):
        questions = {}
        manager = {}
        project = {"name": "project_name", "entity_type": "clinic", "language": "en"}
        form_model = Mock( )
        form_model.fields = [{}]
        form_model.form_code = "form code"
        project_form = Mock( )
        project_form.cleaned_data = {
            "name": "project_name", "entity_type": "clinic", "language": "en"
        }

        post = {"questionnaire-code": "q01",
                "question-set": "",
                "profile_form": '{"name":"project_name", "entity_type":"clinic", "language":"en"}'}

        project_info = {"name": "project_name", "entity_type": "clinic", "language": "en"}

        with patch( "project.preview_views.create_questionnaire" ) as questionnaire:
            questionnaire.return_value = form_model
            with patch( "project.preview_views.get_questions" ) as get_questions:
                get_questions.return_value = questions
                preview_context = get_sms_preview_context( manager, post, project_info )
                self.assertEquals( preview_context['questionnaire_code'], 'q01' )
                self.assertEquals( preview_context['questions'], questions )
                self.assertEquals( preview_context['project'], project )
                self.assertEquals( preview_context['example_sms'], "form code answer1" )


    def test_should_get_question_list(self):
        form_model = Mock( )
        form_model.fields = [{}]
        form_model.entity_defaults_to_reporter.return_value = False

        with patch( "project.preview_views.get_preview_for_field" ) as preview_of_field:
            preview_of_field.return_value = {"description": "description"}
            questions = get_questions( form_model )
            self.assertEquals( questions[0]["description"], "description" )

    def test_should_get_question_list_when_entity_is_reporter(self):
        form_model = Mock( )
        form_model.fields = [{}]
        form_model.entity_defaults_to_reporter.return_value = True

        with patch( "project.preview_views.get_preview_for_field" ) as preview_of_field:
            preview_of_field.return_value = {"description": "description"}
            with patch( "project.preview_views.hide_entity_question" ) as hide_entity_question:
                hide_entity_question.return_value = {"description": "description"}
                questions = get_questions( form_model )
                self.assertEquals( len( questions ), 1 )

    def test_should_get_correct_add_link_for_project(self):
        project = Mock( spec=Project )
        project.entity_type = "reporter"
        project.id = "pid"
        add_link_dict = add_link_context( project )
        self.assertEquals( add_link_dict['text'], 'Add a datasender' )
        self.assertEquals( add_link_dict['url'], "#" )

    def test_should_get_correct_context_for_web_preview(self):
        manager = {}
        form_model = {}

        project_info = {"name": "project_name", "goals": "des", "entity_type": "clinic", "activity_report": "yes",
                        "language": "en"}
        post = {'project_state': 'Test'}
        QuestionnaireForm = type( 'QuestionnaireForm', (Form, ), {"short_code_question_code": "eid"} )

        with patch( "project.preview_views.get_questionnaire_form_model" ) as questionnaire_form_model:
            questionnaire_form_model.return_value = form_model
            with patch( "project.preview_views.WebQuestionnaireFormCreator" ) as web_questionnaire_form_creator:
                web_questionnaire_form_creator.return_value = web_questionnaire_form_creator
                with patch.object( web_questionnaire_form_creator, "create" ) as create_form:
                    create_form.return_value = QuestionnaireForm
                    with patch( "project.preview_views.add_link_context" ) as add_link:
                        add_link.return_value = {'text': 'Add a datasender'}
                        web_preview_context = get_web_preview_context( manager, post, project_info )
                        project = web_preview_context['project']
                        self.assertEquals( project['activity_report'], "yes" )
                        questionnaire_form = web_preview_context['questionnaire_form']
                        self.assertEquals( questionnaire_form.short_code_question_code, "eid" )
                        self.assertEquals( web_preview_context['add_link']['text'], 'Add a datasender' )

    def test_should_get_correct_instruction_and_preview_links_for_questionnaire(self):
        with patch( "project.views.reverse" ) as reverse:
            reverse.side_effect = lambda *args, **kw: "/project/%s" % args[0]
            links = get_preview_and_instruction_links_for_questionnaire( )
            self.assertEqual( links["sms_preview"], "/project/questionnaire_sms_preview" )
            self.assertEqual( links["web_preview"], "/project/questionnaire_web_preview" )
            self.assertEqual( links["smart_phone_preview"], "/project/smart_phone_preview" )


    def test_should_delete_submission_with_error_status(self):
        dbm = Mock( )
        request = Mock( )
        submission = Mock( spec=Submission )
        submission.created = date( 2012, 8, 20 )
        submission.data_record = None
        with patch( "project.submission_views.Submission.get" ) as get_submission:
            get_submission.return_value = submission
            with patch( "project.submission_views.get_organization" ) as get_organization:
                get_organization.return_value = Mock( )
                received_times = delete_submissions_by_ids( dbm, request, ['1'] )
                self.assertEqual( ['20/08/2012 00:00:00'], received_times )

    def test_should_append_success_status_to_context_when_no_error(self):
        context = {}
        form = Mock( spec=ReporterRegistrationForm )
        form.errors = [];
        new_context = append_success_to_context( context, form )
        self.assertTrue( new_context['success'] )

    def test_should_append_failed_status_to_context_when_has_error(self):
        context = {}
        form = Mock( spec=ReporterRegistrationForm )
        form.errors = [''];
        new_context = append_success_to_context( context, form )
        self.assertFalse( new_context['success'] )

    def test_should_return_max_code_in_questionnaire(self):
        ddtype = Mock( spec=DataDictType )
        fields = [TextField( name="f1", code="q1", label="f1", ddtype=ddtype ),
                         TextField( name="f2", code="q2", label="f2", ddtype=ddtype ),
                         TextField( name="f3", code="q3", label="f3", ddtype=ddtype ),
                         TextField( name="f3", code="q4", label="f4", ddtype=ddtype ),
                         TextField( name="f5", code="q5", label="f5", ddtype=ddtype )]
        self.assertEqual( 5, get_max_code( fields ) )

    def test_should_return_one_in_questionnaire_without_start_with_q(self):
        ddtype = Mock( spec=DataDictType )
        fields = [TextField( name="f1", code="c1", label="f1", ddtype=ddtype ),
                         TextField( name="f2", code="c2", label="f2", ddtype=ddtype ),
                         TextField( name="f3", code="c3", label="f3", ddtype=ddtype ),
                         TextField( name="f3", code="c4", label="f4", ddtype=ddtype ),
                         TextField( name="f5", code="c5", label="f5", ddtype=ddtype )]
        self.assertEqual( 1, get_max_code( fields ) )

    def test_should_return_reporting_period_field_if_questionnaire_contains(self):
        ddtype = Mock( spec=DataDictType )
        dateField = DateField( name="f2", code="c2", label="f2",date_format="dd.mm.yyyy", ddtype=ddtype, event_time_field_flag=True)
        fields = [
            TextField( name="f1", code="c1", label="f1", ddtype=ddtype ),
            dateField]
        self.assertEqual(fields[1], get_reporting_period_field(fields))

    def test_should_return_none_if_questionnaire_dose_not_contains(self):
        ddtype = Mock( spec=DataDictType )
        dateField = DateField( name="f2", code="c2", label="f2",date_format="dd.mm.yyyy", ddtype=ddtype, event_time_field_flag=False)
        fields = [
            TextField( name="f1", code="c1", label="f1", ddtype=ddtype ),
            dateField]
        self.assertEqual(None, get_reporting_period_field(fields))

    def test_should_return_origin_value_for_item_is_non_tuple_data(self):
        field_values = [['string']]
        data = formatted_data(field_values)
        self.assertEqual(data, [['string']])
        self.assertEqual(field_values, [['string']])

    def test_should_return_formatted_value_for_item_is_tuple_data_and_origin_not_changed(self):
        field_values = [[('key', 'value'), 'string']]
        data = formatted_data(field_values)
        self.assertEqual(data, [['key</br>(value)', 'string']])
        self.assertEqual(field_values, [[('key', 'value'), 'string']])

    def test_should_prepare_export_data_for_success_submission_log_tab(self):
        request = Mock()
        request.GET.get.return_value = SubmissionRouter.SUCCESS
        request.POST.get.return_value = 'proj_name'
        data, file_name = _prepare_export_data(request, ["Submission ID", "Q1", "Q2", "Status", "Reply SMS", "Q4", "Q5"], [[0, 1, 2, 3, '-', 4, 5]])
        expected = [['Q1', 'Q2', 'Q4', 'Q5'], [1, 2, 4, 5]]
        self.assertEqual(expected, data)
        self.assertEqual('proj_name_success_log', file_name)

    def test_should_prepare_export_data_for_all_submission_log_tab(self):
        request = Mock()
        request.GET.get.return_value = SubmissionRouter.ALL
        request.POST.get.return_value = 'proj_name'
        data, file_name = _prepare_export_data(request, ["Submission ID", "Q1", "Q2", "Status", "Reply SMS", "Q4", "Q5"], [[0, 1, 2, 3, '-', 4, 5]])
        expected = [['Q1', 'Q2', 'Status', 'Q4', 'Q5'], [1, 2, 3, 4, 5]]
        self.assertEqual(expected, data)
        self.assertEqual('proj_name_all_log', file_name)

    def test_should_prepare_export_data_for_deleted_submission_log_tab(self):
        request = Mock()
        request.GET.get.return_value = SubmissionRouter.DELETED
        request.POST.get.return_value = 'proj_name'
        data, file_name = _prepare_export_data(request, ["Submission ID", "Q1", "Q2", "Status", "Reply SMS", "Q4", "Q5"], [[0, 1, 2, 3, '-', 4, 5]])
        expected = [['Q1', 'Q2', 'Status', 'Q4', 'Q5'], [1, 2, 3, 4, 5]]
        self.assertEqual(expected, data)
        self.assertEqual('proj_name_deleted_log', file_name)

    def test_should_prepare_export_data_for_error_submission_log_tab(self):
        request = Mock()
        request.GET.get.return_value = SubmissionRouter.ERROR
        request.POST.get.return_value = 'proj_name'
        data, file_name = _prepare_export_data(request, ["Submission ID", "Q1", "Q2", "Status", "Reply SMS", "Q4", "Q5"], [[0, 1, 2, 3, '-', 4, 5]])
        expected = [['Q1', 'Q2', 'Reply SMS', 'Q4', 'Q5'], [1, 2, '-', 4, 5]]
        self.assertEqual(expected, data)
        self.assertEqual('proj_name_error_log', file_name)

    def test_should_prepare_export_data_for_analysis_page(self):
        request = Mock()
        request.GET.get.return_value = None
        request.POST.get.return_value = 'proj_name'
        data, file_name = _prepare_export_data(request, ["Submission ID", "Q1", "Q2", "Status", "Q4", "Q5"], [[0, 1, 2, 3, 4, 5]])
        expected = [['Q1', 'Q2', 'Status', 'Q4', 'Q5'], [1, 2, 3, 4, 5]]
        self.assertEqual(expected, data)
        self.assertEqual('proj_name_analysis', file_name)


