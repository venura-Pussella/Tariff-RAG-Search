from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # read local .env file
import sys
import os
# sys.path.append('../tariff-search') # IMPORTANT: required since we manually run this script from this location itself
sys.path.append(os.getcwd()) # IMPORTANT: required since we manually run this script from this location itself

from werkzeug.datastructures import FileStorage
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import secrets
import platform

from app_functions import file_management as fm
from initializers.extract_data_for_review import convertPDFToExcelForReview
from data_stores.AzureTableObjects import AzureTableObjects as ato
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from data_stores.AzureTableObjects import MutexError
import config

commandLineArguments = sys.argv
filepath: str = commandLineArguments[1]
chapterNumberString: str = None
if len(commandLineArguments) > 2:
    chapterNumberString: str = commandLineArguments[2]

chapterNumber: int = None
if chapterNumberString:
    try: chapterNumber = int(chapterNumberString)
    except ValueError: 
        print("User entered chapter number could not be converted to an integer")
        quit()

wFile: FileStorage = None
with open(filepath, 'rb') as file:
    wFile = FileStorage(file)

errors = fm.validateUpload('pdf', wFile)
if errors != '':
    print(f'Uploaded file error. {errors}')
    quit()

reviewFilepaths = convertPDFToExcelForReview(filepath, chapterNumber)
if not reviewFilepaths: # i.e. an exception was raised when trying to extract data from the pdf
    print('Error with pdf or entered chapter number')
    quit()

if chapterNumber == None:
    chapterNumber = reviewFilepaths[2]

try: ato.create_new_blank_entity(chapterNumber)
except ResourceExistsError: 
    print(f'A record for chapter {chapterNumber} already exists. Delete it if you want to upload a new PDF.')
    quit()

mutexKey = secrets.token_hex()
try: ato.claim_mutex(chapterNumber, mutexKey)
except MutexError as e:
    if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
        os.remove(filepath)
    print(e.__str__())
    quit()
ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.uploadingPDF)
abo.upload_blob_file(filepath, config.pdf_container_name, f'{chapterNumber}.pdf') # PDF uploaded to azure blob
print('PDF @ ' + filepath + ' successfully uploaded')
if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
    os.remove(filepath)

ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.uploadingGeneratedDocuments)
abo.upload_blob_file(reviewFilepaths[0],config.generatedExcel_container_name) # upload generated excel to azure blob
abo.upload_blob_file(reviewFilepaths[1],config.generatedDict_container_name) # upload dictionary pickle to azure blob
ato.edit_entity(chapterNumber, mutexKey, newRecordStatus='', newRecordState=config.RecordState.pdfUploaded)
ato.release_mutex(chapterNumber, mutexKey)
if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
    os.remove(reviewFilepaths[0])
    os.remove(reviewFilepaths[1])           

print("Data extracted from tariff pdfs and saved as excel (and text data dictionary pickle) for review.")
