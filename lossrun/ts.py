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
