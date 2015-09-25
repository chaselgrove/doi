"""DOI configuration"""

import ConfigParser

cp = ConfigParser.ConfigParser()
cp.read('/etc/doi.config')

test_auth = (cp.get('test', 'username'), cp.get('test', 'password'))

umms_auth = (cp.get('umms', 'username'), cp.get('umms', 'password'))

umms_doi_prefix = cp.get('umms', 'prefix')

# eof
