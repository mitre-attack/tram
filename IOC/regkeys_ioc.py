import re

class IOC:
    def __init__(self):
        self.name = 'registry keys'

    async def find(self,report,blob):
        re_regkeys = r"\b(HKEY_CURRENT_USER\\|SOFTWARE\\|HKEY_LOCAL_MACHINE\\|HKLM\\HKCR\\|HKCU)([a-zA-Z0-9\s_@\-\^!#.\:\/\$%&+={}\[\]\\*])*\b"
        for key in re.findall(re_regkeys,blob):
            if self._is_valid_key(key):
                report.indicators.append(Indicator(name=self.name, value=key))

    @staticmethod
    def _is_valid_key(key):
        return True