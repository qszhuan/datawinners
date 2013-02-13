from datawinners.project import Header
from datawinners.project.submission_data import SubmissionData
from project.analysis_result import AnalysisResult
from project.data_sender import DataSender
from project.submission_utils.submission_formatter import SubmissionFormatter

class Analysis(SubmissionData):
    def __init__(self, form_model, manager, org_id, filters):
        super(Analysis, self).__init__(form_model, manager, org_id, Header, None, filters)
        self._init_raw_values()

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

    def analyse(self):
        field_values = SubmissionFormatter().get_formatted_values_for_list(self.get_raw_values())
        analysis_statistics = self.get_analysis_statistics()
        data_sender_list = self.get_data_senders()
        subject_lists = self.get_subjects()
        default_sort_order = self.get_default_sort_order()

        return AnalysisResult(field_values, analysis_statistics, data_sender_list, subject_lists, default_sort_order)

    def _init_excel_values(self):
        leading_part = []
        for submission in self.submissions:
            data_sender_tuple, rp, subject, submission_date = super(Analysis, self)._get_submission_details(submission)
            data_sender = DataSender.from_tuple(data_sender_tuple)
            leading_part.append(
                filter(lambda x: x, [data_sender.name, data_sender.reporter_id, submission_date, subject, rp]))
        return leading_part
