from django.utils.translation import ugettext
from project.Header import Header

class ExcelFileAnalysisHeader(Header):
    def _prefix(self):
        return [self._subject_header(),self._reporting_period_header(),self._submission_date_header(),self._data_sender_name_header,self._data_sender_id_header]

    def _data_sender_name_header(self):
        return ugettext("Data Sender Name"), ''

    def _data_sender_id_header(self):
        return ugettext("Data Sender Id"), ''


class ExcelFileSubmissionHeader(ExcelFileAnalysisHeader):
    def _prefix(self):
        return [self._data_sender_name_header(), self._data_sender_id_header(), self._submission_date_header(), self._status(), self._error_message(),self._subject_header()]

    def _status(self):
        return ugettext('Status'), ''

    def _error_message(self):
        return ugettext("Error Messages"), ''

