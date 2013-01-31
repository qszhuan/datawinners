from nose.plugins.attrib import attr
from framework.base_test import BaseTest
from pages.loginpage.login_page import LoginPage
from testdata.test_data import DATA_WINNER_LOGIN_PAGE
from tests.logintests.login_data import TRIAL_CREDENTIALS_VALIDATES, VALID_CREDENTIALS
from tests.remindertests.reminder_data import *
from nose.plugins.skip import SkipTest
from framework.utils.data_fetcher import fetch_, from_

#@attr('suit_3')
class TestReminderSend(BaseTest):
    def login_with(self, account):
        self.driver.go_to(DATA_WINNER_LOGIN_PAGE)
        login_page = LoginPage(self.driver)
        return login_page.do_successful_login_with(account)

    def go_to_reminder_page(self, project, credentials):
        global_navigation = self.login_with(credentials)
        all_project_page = global_navigation.navigate_to_view_all_project_page()
        overview_page = all_project_page.navigate_to_project_overview_page(project)
        return overview_page.navigate_to_reminder_page()

    def set_deadline_by_week(self, reminder_settings, deadline):
        reminder_settings.set_frequency(fetch_(FREQUENCY, from_(deadline)))
        reminder_settings.set_week_day(fetch_(DAY, from_(deadline)))
        reminder_settings.set_deadline_type_for_week(fetch_(TYPE, from_(deadline)))
        return reminder_settings

    def set_deadline_by_month(self, reminder_settings, deadline):
        reminder_settings.set_frequency(fetch_(FREQUENCY, from_(deadline)))
        reminder_settings.set_month_day(fetch_(DAY, from_(deadline)))
        reminder_settings.set_deadline_type_for_month(fetch_(TYPE, from_(deadline)))
        return reminder_settings

    def active_project_and_go_to_all_reminder_page(self, project_overview_page):
        project_overview_page.activate_project()
        return project_overview_page.navigate_to_reminder_page()

    @attr("functional_test")
    def test_trial_account_should_see_reminder_not_work_message_at_reminder_tab_in_active_project(self):
        all_reminder_pages = self.go_to_reminder_page(fetch_(PROJECT_NAME, from_(DISABLED_REMINDER)), TRIAL_CREDENTIALS_VALIDATES)
        self.assertEqual(DISABLED_REMINDER[WARNING_MESSAGE], all_reminder_pages.get_warning_message())
        all_reminder_pages.click_sent_reminder_tab()
        self.assertEqual(fetch_(WARNING_MESSAGE, from_(DISABLED_REMINDER)), all_reminder_pages.get_warning_message())

    #@attr("functional_test")
    @SkipTest
    def test_trial_account_should_see_reminder_not_work_message_at_sent_tab_in_active_project(self):
        all_reminder_pages = self.go_to_reminder_page(fetch_(PROJECT_NAME, from_(DISABLED_REMINDER)), TRIAL_CREDENTIALS_VALIDATES)
        all_reminder_pages.click_sent_reminder_tab()
        self.assertEqual(fetch_(WARNING_MESSAGE, from_(DISABLED_REMINDER)), all_reminder_pages.get_warning_message())

    @attr("functional_test")
    def test_verify_change_in_deadline_example_for_week(self):
        all_reminder_pages = self.go_to_reminder_page(fetch_(PROJECT_NAME, from_(DEADLINE_FIRST_DAY_OF_SAME_WEEK)), VALID_CREDENTIALS)
        reminder_settings = all_reminder_pages.click_reminder_settings_tab()
        reminder_settings = self.set_deadline_by_week(reminder_settings, fetch_(DEADLINE, from_(DEADLINE_FIRST_DAY_OF_SAME_WEEK)))
        self.assertEqual(reminder_settings.get_example_text(), fetch_(DEADLINE, from_(DEADLINE_FIRST_DAY_OF_SAME_WEEK))[EXAMPLE_TEXT])

        reminder_settings = self.set_deadline_by_week(reminder_settings, fetch_(DEADLINE, from_(DEADLINE_LAST_DAY_OF_SAME_WEEK)))
        self.assertEqual(reminder_settings.get_example_text(), fetch_(EXAMPLE_TEXT, from_(DEADLINE_LAST_DAY_OF_SAME_WEEK[DEADLINE])))

        reminder_settings = self.set_deadline_by_week(reminder_settings, fetch_(DEADLINE, from_(DEADLINE_SECOND_DAY_OF_FOLLOWING_WEEK)))
        self.assertEqual(reminder_settings.get_example_text(), fetch_(EXAMPLE_TEXT, from_(DEADLINE_SECOND_DAY_OF_FOLLOWING_WEEK[DEADLINE])))

        reminder_settings = self.set_deadline_by_week(reminder_settings, fetch_(DEADLINE, from_(DEADLINE_FIFTH_DAY_OF_FOLLOWING_WEEK)))
        self.assertEqual(reminder_settings.get_example_text(), fetch_(EXAMPLE_TEXT, from_(DEADLINE_FIFTH_DAY_OF_FOLLOWING_WEEK[DEADLINE])))

    @attr("functional_test")
    def test_verify_change_in_deadline_example_for_month(self):
        all_reminder_pages = self.go_to_reminder_page(fetch_(PROJECT_NAME, from_(DEADLINE_FIRST_DAY_OF_SAME_MONTH)), VALID_CREDENTIALS)
        reminder_settings = all_reminder_pages.click_reminder_settings_tab()

        reminder_settings = self.set_deadline_by_month(reminder_settings, fetch_(DEADLINE, from_(DEADLINE_FIRST_DAY_OF_SAME_MONTH)))
        self.assertEqual(reminder_settings.get_example_text(), fetch_(EXAMPLE_TEXT, from_(DEADLINE_FIRST_DAY_OF_SAME_MONTH[DEADLINE])))

        reminder_settings = self.set_deadline_by_month(reminder_settings, fetch_(DEADLINE, from_(DEADLINE_LAST_DAY_OF_SAME_MONTH)))
        self.assertEqual(reminder_settings.get_example_text(), fetch_(EXAMPLE_TEXT, from_(DEADLINE_LAST_DAY_OF_SAME_MONTH[DEADLINE])))

        reminder_settings = self.set_deadline_by_month(reminder_settings, fetch_(DEADLINE, from_(DEADLINE_TWENTIETH_DAY_OF_FOLLOWING_MONTH)))
        self.assertEqual(reminder_settings.get_example_text(), fetch_(EXAMPLE_TEXT, from_(DEADLINE_TWENTIETH_DAY_OF_FOLLOWING_MONTH[DEADLINE])))

        reminder_settings = self.set_deadline_by_month(reminder_settings, fetch_(DEADLINE, from_(DEADLINE_ELEVENTH_DAY_OF_FOLLOWING_MONTH)))
        self.assertEqual(reminder_settings.get_example_text(), fetch_(EXAMPLE_TEXT, from_(DEADLINE_ELEVENTH_DAY_OF_FOLLOWING_MONTH[DEADLINE])))

    @attr("functional_test")
    def test_verify_set_one_reminder(self):
        all_reminder_pages = self.go_to_reminder_page(fetch_(PROJECT_NAME, from_(REMINDER_DATA_WEEKLY)), VALID_CREDENTIALS)
        reminder_settings = all_reminder_pages.click_reminder_settings_tab()
        reminder_settings = self.set_deadline_by_week(reminder_settings, fetch_(DEADLINE, from_(REMINDER_DATA_WEEKLY)))
        reminder_settings.set_reminder(fetch_(REMINDERS, from_(REMINDER_DATA_WEEKLY)))
        reminder_settings.set_whom_to_send(fetch_(WHOM_TO_SEND, from_(REMINDER_DATA_WEEKLY)))
        reminder_settings.save_reminders()
        self.assertEqual(reminder_settings.get_success_message(), SUCCESS_MESSAGE)
        reminders = reminder_settings.get_reminders_of_project(reminder_settings.get_project_id())
        self.assertEqual(fetch_(REMINDERS, from_(REMINDER_DATA_WEEKLY)), reminders[0])


