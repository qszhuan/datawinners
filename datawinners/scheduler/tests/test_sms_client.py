import unittest
from accountmanagement.models import OrganizationSetting
from scheduler.smsclient import SMSClient

class TestSMSClient(unittest.TestCase):
    def test_should_return_true_and_log_error_when_to_number_is_a_datawinner_organization(self):
        organization_numbers = [];
        for each in OrganizationSetting.objects.all():
            organization_numbers.extend(each.get_organisation_sms_number())
        for number in organization_numbers:
            self.assertTrue(SMSClient().check_and_log_destination_organization(number))

    def test_should_return_false_when_to_number_is_a_not_datawinner_organization(self):
        self.assertFalse(SMSClient().check_and_log_destination_organization(0))
