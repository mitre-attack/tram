import re

class IOC:
    def __init__(self):
        self.name = 'domain'

    async def find(self,report,blob):
        re_domain =r"\b([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}\b"
        for domain in re.findall(re_domain,blob):
            if self._is_valid_domain(domain):
                report.indicators.append(Indicator(name=self.name, value=domain))
    
    @staticmethod
    def _is_valid_domain(domain):
        return True # need to check way to verify