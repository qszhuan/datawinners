import logging
from mangrove.utils.types import  is_not_empty

logger = logging.getLogger("django")
custom_report_routing_table={}

class ReportRouter(object):

    def route(self, organization_id, form_submission):

        logger.info("*************************entering route()*************************")
        if self.has_error_in_submission(form_submission): return
        custom_report_handler = custom_report_routing_table.get(organization_id, None)
        if custom_report_handler is not None:
            logger.info("*************************type of custom_report_handler: %s*************************" % type(custom_report_handler))
            custom_report_handler.handle(form_submission.form_code,form_submission.processed_data, form_submission.datarecord_id)

    def delete(self,organization_id,form_code,data_record_id):
        custom_report_handler = custom_report_routing_table.get(organization_id, None)
        if custom_report_handler is not None:
            custom_report_handler.delete_handler(form_code,data_record_id)

    def has_error_in_submission(self, form_submission):
        return is_not_empty(form_submission.errors)

