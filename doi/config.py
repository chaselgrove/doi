"""DOI configuration"""

import configparser

cp = configparser.ConfigParser()
cp.read('/etc/doi.config')

test_auth = (cp.get('test', 'username'), cp.get('test', 'password'))

umms_auth = (cp.get('umms', 'username'), cp.get('umms', 'password'))

umms_doi_prefix = cp.get('umms', 'prefix')

db_host = cp.get('db', 'host')
db_database = cp.get('db', 'database')
db_user = cp.get('db', 'user')
db_password = cp.get('db', 'password')

# eof
