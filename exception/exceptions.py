class ImportReportError(Exception):
    """ exception when a report cannot be imported """
    def __init__(self, message):
        self.message = message