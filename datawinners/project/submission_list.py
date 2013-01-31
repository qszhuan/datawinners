from datawinners.project.Header import SubmissionsPageHeader
from submission_data import SubmissionData

class SubmissionList(SubmissionData):
    def __init__(self, form_model, manager, org_id, submission_type, filters,keyword=None):
        super(SubmissionList, self).__init__(form_model, manager, org_id, SubmissionsPageHeader, submission_type, filters,keyword)
        self._init_raw_values()

    def get_leading_part(self):
        leading_part = []
        for submission in self.filtered_submissions:
            data_sender, rp, subject, submission_date = super(SubmissionList, self)._get_submission_details(submission)
            status = self._get_translated_submission_status(submission.status)
            error_message = submission.errors if submission.errors else "-"
            leading_part.append(filter(lambda x: x, [submission.id, data_sender, submission_date, status, error_message, subject, rp]))
        return leading_part

    def _init_raw_values(self):
        leading_part = self.get_leading_part()
        self.populate_submission_data(leading_part)
