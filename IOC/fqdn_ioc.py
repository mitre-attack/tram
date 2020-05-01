import re

class IOC:
    def __init__(self):
        self.name = 'fqdn'

    async def find(self,report,blob):
        re_fqdn =r"(?=.{1,253})((((?!-)[a-zA-Z0-9-]{1,63}(?<!-))|((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}))"
        for domain in re.findall(re_fqdn,blob):
            if self._is_valid_domain(domain):
                report.indicators.append(Indicator(name=self.name, value=domain))
    
    @staticmethod
    def _is_valid_domain(domain):
        return True # need to check way to verify