import logging

from azure.core.exceptions import ResourceNotFoundError

from data_stores.AzureBlobObjects import AzureBlobObjects as abo
import config
from data_stores.DataStores import DataStores as ds

def __deleteChapterBlob(chapterNumber: int, file_extension: str, container_name: str, release_date: str):
    """From the given args, we can construct the filename and know from what container it should be deleted."""
    filename = f"{release_date}/{chapterNumber}.{file_extension}"
    container_client = abo.get_container_client(container_name)
    blob_client = container_client.get_blob_client(filename)
    try: blob_client.delete_blob()
    except ResourceNotFoundError:
        logging.error(f'Blob to be deleted not found. Perhaps it was already deleted or never existed. chapterNumber: {chapterNumber}, release: {release_date}, file_extension:{file_extension}, container_name:{container_name}')

def deleteChapterJsonBlob(chapterNumber: int, release_date: str):
    __deleteChapterBlob(chapterNumber, 'json', config.json_container_name, release_date)
    ds.updateJSONdictsFromAzureBlob([(chapterNumber,release_date)])

def deleteChapterReviewedExcelBlob(chapterNumber: int, release_date: str):
    __deleteChapterBlob(chapterNumber, 'xlsx', config.reviewedExcel_container_name, release_date)

def deleteChapterDictPickleBlob(chapterNumber: int, release_date: str):
    __deleteChapterBlob(chapterNumber, 'pkl', config.generatedDict_container_name, release_date)

def deleteChapterGeneratedExcelBlob(chapterNumber: int, release_date: str):
    __deleteChapterBlob(chapterNumber, 'xlsx', config.generatedExcel_container_name, release_date)

def deleteChapterPDFBlob(chapterNumber: int, release_date: str):
    __deleteChapterBlob(chapterNumber, 'pdf', config.pdf_container_name, release_date)

from initializers.az_cosmos_nosql_vectorstore import deleteChapterFromCosmos as __deleteChapterFromCosmos
def deleteChapterFromCosmos(chapterNumber: int, release_date: str):
    __deleteChapterFromCosmos(chapterNumber, release_date)