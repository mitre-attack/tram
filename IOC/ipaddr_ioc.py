import re
from ipaddress import ip_address

class IOC:
    def __init__(self):
        self.name = 'ipv4'
    
    async def find(self, report, blob):
        re_ipv4 = r'(?:(?:1\d\d|2[0-5][0-5]|2[0-4]\d|0?[1-9]\d|0?0?\d)\.){3}(?:1\d\d|2[0-5][0-5]|2[0-4]\d|0?[1-9]\d|0?0?\d)'
        for ip in re.findall(re_ipv4, blob):
            if self._is_valid_ip(ip):
                report.indicators.append(Indicator(name=self.name, value=ip))
    
    @staticmethod
    def _is_valid_ip(raw_ip):
        try:
            if raw_ip in ['0.0.0.0', '127.0.0.1']:
                return False
            ip_address(raw_ip)
        except BaseException:
            return False
        return True