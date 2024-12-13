#### KEYS REQUIRED:

COSMOS_ENDPOINT
COSMOS_KEY
AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS
AZURE_OPENAI_ENDPOINT_FOR_CHATCOMPLETION
AZURE_OPENAI_API_KEY
SCM_DO_BUILD_DURING_DEPLOYMENT=true
AZURE_STORAGE_CONNECTION_STRING
FLASK_SECRET_KEY (can use any key - see https://flask.palletsprojects.com/en/stable/config/)
AZURE_TABLE_CONNECTION_STRING

#### Python version
python 3.11

#### Command for Azure deployment thru zip file push
Curl command to push zip file to deployment:
curl.exe -X POST -H 'Content-Type: application/zip' -u '$tariff-search-browns' -T pdfplumber.zip https://tariff-search-browns.scm.azurewebsites.net/api/zipdeploy

#### How to run app
Local: run app.py with python3
Azure web app using code: startup.txt provided - mention this in startup option
Azure web app refering docker image in Azure container registry - dockerfile provided