# SCRIPT

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # read local .env file
import sys
sys.path.append('../tariff-search') # IMPORTANT: required since we manually run this script from this location itself
import os
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from data_stores.AzureTableObjects import AzureTableObjects as ato
import config

commandLineArguments = sys.argv
pdfFilepath = None
reviewFilepaths = None
if len(commandLineArguments) == 6:
    excelPath = commandLineArguments[1]
    dictPath = commandLineArguments[2]
    pdfFilepath = commandLineArguments[3]
    mutexKey = commandLineArguments[4]
    chapterNumber = int(commandLineArguments[5])

os.remove(pdfFilepath)
ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.uploadingGeneratedDocuments)
abo.upload_blob_file(excelPath,config.generatedExcel_container_name) # upload generated excel to azure blob
abo.upload_blob_file(dictPath,config.generatedDict_container_name) # upload dictionary pickle to azure blob
ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.uploadedGeneratedDocuments, newRecordState=config.RecordState.pdfUploaded)
ato.release_mutex(chapterNumber, mutexKey)
os.remove(excelPath)
os.remove(dictPath)           

print("Data extracted from tariff pdfs and saved as excel (and text data dictionary pickle) for review.")