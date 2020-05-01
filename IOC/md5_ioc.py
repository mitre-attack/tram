import re

class IOC:
    def __init__(self):
        self.name = 'md5'
    
    async def find(self,report,blob):
        re_md5 = r"([A-F]|[0-9]){32}"
        for md5 in re.findall(re_md5, blob):
            if self._is_valid_md5(md5):
                report.indicators.append(Indicator(name=self.name, value=md5))

    @staticmethod
    def _is_valid_md5(md5):
        re_check = r"^([A-F]|[0-9]){32}$"
        try:
            if bool(re.match(re_check, md5)):
                return 1
            else:
                return 0

        except:
            return -1

