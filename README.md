KEYS:

COSMOS_ENDPOINT
COSMOS_KEY
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
SCM_DO_BUILD_DURING_DEPLOYMENT=true
AZURE_STORAGE_CONNECTION_STRING
FLASK_SECRET_KEY
AZURE_TABLE_CONNECTION_STRING


python 3.11
pywin32 - remove from requirements.txt

Curl command to push zip file to deployment:
curl.exe -X POST -H 'Content-Type: application/zip' -u '$tariff-search-browns' -T pdfplumber.zip https://tariff-search-browns.scm.azurewebsites.net/api/zipdeploy