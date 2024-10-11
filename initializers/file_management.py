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
    """Upload file specified in filepath to Azure blob. The filepath is then deleted.
    ### Args:
        filepath: filepath with file to be uploaded
    ### Returns: 
        void
    """
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
        tableRows.append([chapterNumber,name,'d1','d2','d3','uploaded'])
    return tableRows

def download_blob_file(filename: str):
    """Download file specified in filename from Azure blob to an appropriate local directory.
    ### Args:
            filename: filename to be downloaded from Azure blob
    ### Returns: 
            void
    """
    container_client = ABO.get_container_client(config.pdf_container_name)
    print("filename about to be downloaded from blob: " + filename)
    blob_client = container_client.get_blob_client(blob=filename)
    filepath = os.path.join('files/', filename)
    with open(filepath, mode="wb") as data:
        download_stream = blob_client.download_blob()
        data.write(download_stream.readall())