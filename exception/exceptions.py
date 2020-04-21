class ImportReportError(Exception):
    """ exception when a report cannot be imported """
    def __init__(self, msg, report_id):
        self.msg = msg
        self.report_id = report_id