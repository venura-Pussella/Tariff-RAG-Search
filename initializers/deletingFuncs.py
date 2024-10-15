from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from azure.core.exceptions import ResourceNotFoundError
import config


def __deleteChapterBlob(chapterNumber: int, file_extension: str, container_name: str):
    filename = f"{chapterNumber}.{file_extension}"
    container_client = abo.get_container_client(container_name)
    blob_client = container_client.get_blob_client(filename)
    try: blob_client.delete_blob()
    except ResourceNotFoundError:
        print('Blob to be deleted not found. Perhaps it was already deleted or never existed.')

def deleteChapterJsonBlob(chapterNumber: int):
    __deleteChapterBlob(chapterNumber, 'json', config.json_container_name)

def deleteChapterReviewedExcelBlob(chapterNumber: int):
    __deleteChapterBlob(chapterNumber, 'xlsx', config.reviewedExcel_container_name)

def deleteChapterDictPickleBlob(chapterNumber: int):
    __deleteChapterBlob(chapterNumber, 'pkl', config.generatedDict_container_name)

def deleteChapterGeneratedExcelBlob(chapterNumber: int):
    __deleteChapterBlob(chapterNumber, 'xlsx', config.generatedExcel_container_name)

def deleteChapterPDFBlob(chapterNumber: int):
    __deleteChapterBlob(chapterNumber, 'pdf', config.pdf_container_name)

from initializers.az_cosmos_nosql_vectorstore import deleteChapterFromCosmos as __deleteChapterFromCosmos
def deleteChapterFromCosmos(chapterNumber: int):
    __deleteChapterFromCosmos(chapterNumber)