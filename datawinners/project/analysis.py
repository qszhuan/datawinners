from datawinners.project import Header
from datawinners.project.submission_data import SubmissionData

class Analysis(SubmissionData):

    def __init__(self, submissions, form_model, manager, org_id, submission_type, filters):
        super(Analysis, self).__init__(submissions, form_model, manager, org_id, Header, submission_type, filters)

    def get_leading_part(self):
        leading_part = []
        for submission in self.filtered_submissions:
            data_sender, rp, subject, submission_date = super(Analysis, self)._get_submission_details(submission)
            leading_part.append(
                filter(lambda x: x, [submission.id, data_sender, submission_date, subject, rp]))
        return leading_part

    def _init_raw_values(self):
        leading_part = self.get_leading_part()
        self.populate_submission_data(leading_part)
