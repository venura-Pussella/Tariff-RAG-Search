from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, BlobBlock, StandardBlobTier
import os
import config
import io
import uuid
from data_stores.AzureBlobObjects import AzureBlobObjects as ABO

def allowed_file(filename: str, extension: str):
    """Checks if filename has allowed extension.
    ### Example:
    filename = '28.pdf', extension = 'pdf' will return true
    """
    actualExtension = filename.rsplit(".")[-1]
    return actualExtension == extension


def upload_blob_file(filepath: str):
    container_client = ABO.get_container_client(config.pdf_container_name)
    filename = filepath.rsplit("/")[-1]
    print("filename about to be uploaded to blob: " + filename)
    with open(filepath, mode="rb") as data:
        blob_client = container_client.upload_blob(name=filename, data=data, overwrite=True)
    os.remove(filepath)

def getListOfFilenamesInContainer(containerName: str):
    containerClient = ABO.get_container_client(containerName)
    blobName_list = containerClient.list_blob_names()
    return list(blobName_list)

# def getListOfFilesInContainer(containerName: str):
#     containerClient = ABO.get_container_client(containerName)
#     blob_list = containerClient.list_blobs()
#     for blob in blob_list:
#         print(str(type(blob)))
#         print(blob)

def generateArrayForTableRows():
    tableRows = []
    listOfPDFNames = getListOfFilenamesInContainer(config.pdf_container_name)
    for name in listOfPDFNames:
        chapterNumber = name.rsplit('.')[0]
        tableRows.append([chapterNumber,name,'d1','d2','d3','uploafed'])
    return tableRows