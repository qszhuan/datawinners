from framework.base_test import BaseTest
from nose.plugins.attrib import attr
from pages.registrationpage.registration_page import RegistrationPage
from tests.endtoendtest.trial_end_to_end_data import REGISTRATION_DATA_FOR_SUCCESSFUL_TRIAL_REGISTRATION, SUCCESS_MESSAGE
import time

#Tear out the email backend and replace it with the filebased backend
#In the settings, you will need to add settings.EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
#Set the path to save emails to: settings.EMAIL_FILE_PATH = 'path/to/email'
#Do the registration
#Open the email file and find the link to the registration page (some <a> tag in it somewhere probably)
#self.driver.go_to(That activation url)
#Check that activation page has the success message


#@attr('suit_2')
class TestTrialApplicationEndToEnd(BaseTest):
    def tearDown(self):
        pass

    def register_trial_account(self):
        self.driver.go_to("localhost:8000/register/trial")
        registration_page = RegistrationPage(self.driver)
        registration_confirmation_page, email = registration_page.successful_registration_with(REGISTRATION_DATA_FOR_SUCCESSFUL_TRIAL_REGISTRATION)
        time.sleep(2)
        self.assertEquals(registration_confirmation_page.registration_success_message(),
                          SUCCESS_MESSAGE)

    @attr("functional_test")
    def test_trial_end_to_end_test(self):
        self.register_trial_account()