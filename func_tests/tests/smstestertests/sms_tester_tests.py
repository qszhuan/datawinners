# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from nose.plugins.attrib import attr
from framework.base_test import BaseTest
from framework.utils.data_fetcher import fetch_, from_
from pages.smstesterpage.sms_tester_page import SMSTesterPage
from testdata.test_data import DATA_WINNER_SMS_TESTER_PAGE
from tests.smstestertests.sms_tester_data import *

#@attr('suit_3')
class TestSMSTester(BaseTest):

    @attr('functional_test', 'smoke')
    def test_successful_sms_submission(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(VALID_DATA)
        self.assertEqual(sms_tester_page.get_response_message(), fetch_(SUCCESS_MESSAGE, from_(VALID_DATA)))

    @attr('functional_test')
    def test_sms_player_without_entering_data(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(BLANK_FIELDS)
        self.assertEqual(sms_tester_page.get_error_message(), fetch_(ERROR_MSG, from_(BLANK_FIELDS)))

    @attr('functional_test')
    def test_sms_player_for_exceeding_word_length(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(EXCEED_NAME_LENGTH)
        self.assertEqual(sms_tester_page.get_response_message(), fetch_(ERROR_MSG, from_(EXCEED_NAME_LENGTH)))

    @attr('functional_test')
    def test_sms_player_for_plus_in_the_beginning(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(PLUS_IN_THE_BEGINNING)
        self.assertEqual(sms_tester_page.get_response_message(), fetch_(ERROR_MSG, from_(PLUS_IN_THE_BEGINNING)))

    @attr('functional_test')
    def test_sms_player_for_unregistered_from_number(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(UNREGISTERED_FROM_NUMBER)
        self.assertEqual(sms_tester_page.get_response_message(), fetch_(ERROR_MSG, from_(UNREGISTERED_FROM_NUMBER)))

    @attr('functional_test')
    def test_sms_player_for_addition_of_data_sender(self):
        """
        Function to test the registration of the reporter using sms submission with registered number
        """
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(REGISTER_DATA_SENDER)
        self.assertRegexpMatches(sms_tester_page.get_response_message(),
                                 fetch_(SUCCESS_MESSAGE, from_(REGISTER_DATA_SENDER)))

    @attr('functional_test')
    def test_sms_player_for_addition_of_data_sender_from_unknown_number(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(REGISTER_DATA_SENDER_FROM_UNKNOWN_NUMBER)
        self.assertEqual(sms_tester_page.get_response_message(),
                         fetch_(ERROR_MSG, from_(REGISTER_DATA_SENDER_FROM_UNKNOWN_NUMBER)))

    @attr('functional_test')
    def test_sms_player_for_registration_of_new_subject(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(REGISTER_NEW_SUBJECT)
        self.assertEqual(sms_tester_page.get_response_message(), fetch_(SUCCESS_MESSAGE, from_(REGISTER_NEW_SUBJECT)))

    @attr('functional_test')
    def test_sms_player_for_registration_of_existing_subject_short_code(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(REGISTER_EXISTING_SUBJECT_SHORT_CODE)
        self.assertEqual(sms_tester_page.get_response_message(),
                         fetch_(ERROR_MSG, from_(REGISTER_EXISTING_SUBJECT_SHORT_CODE)))

    @attr('functional_test')
    def test_sms_player_for_registration_with_invalid_geo_code(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(REGISTER_INVALID_GEO_CODE)
        self.assertEqual(sms_tester_page.get_response_message(), fetch_(ERROR_MSG, from_(REGISTER_INVALID_GEO_CODE)))

    @attr('functional_test')
    def test_sms_player_for_only_questionnaire_code(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(ONLY_QUESTIONNAIRE_CODE)
        self.assertEqual(sms_tester_page.get_response_message(), fetch_(ERROR_MSG, from_(ONLY_QUESTIONNAIRE_CODE)))

    @attr('functional_test')
    def test_sms_player_for_wrong_number_of_arg(self):
        self.driver.go_to(DATA_WINNER_SMS_TESTER_PAGE)
        sms_tester_page = SMSTesterPage(self.driver)
        sms_tester_page.send_sms_with(WRONG_NUMBER_OF_ARGS)
        self.assertEqual(sms_tester_page.get_response_message(), fetch_(ERROR_MSG, from_(WRONG_NUMBER_OF_ARGS)))
   