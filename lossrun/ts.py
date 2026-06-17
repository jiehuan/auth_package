python3 -c "
import os
from urllib.parse import quote_plus
server = os.getenv('SPRING_DATASOURCE_HOST')
database = os.getenv('SPRING_DATASOURCE_DATABASE')
username = os.getenv('SPRING_DATASOURCE_USERNAME')
password = os.getenv('SPRING_DATASOURCE_PASSWORD')
print('all set:', all([server, database, username, password]))
url = f'mssql+pyodbc://{quote_plus(username)}:{quote_plus(password)}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&Authentication=ActiveDirectoryServicePrincipal&Encrypt=Yes&TrustServerCertificate=Yes'
print('URL:', url)
"



python3 -c "
import sqlalchemy
engine = sqlalchemy.create_engine(
    'mssql+pyodbc://f5f4beaa-7200-4a89-ae9b-fa8915679bd6:ud18Q~.7.DLz8YIJ05fEE5x9~MY5ImOnxYDIpbEs@z-xlc-0122-axio-pp-ue2-sql03-axiomaisubmissionprioriti.database.windows.net:1433/z-xlc-0122-axio-pp-ue2-sdb04-axiomaisubmissionprioriti?driver=ODBC+Driver+17+for+SQL+Server&Authentication=ActiveDirectoryServicePrincipal&Encrypt=Yes&TrustServerCertificate=Yes',
    connect_args={'timeout': 10}
)
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text('SELECT 1'))
    print('连接成功:', result.fetchone())
"
