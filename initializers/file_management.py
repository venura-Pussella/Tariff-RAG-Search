from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, BlobBlock, StandardBlobTier
from azure.core.exceptions import ResourceNotFoundError
import os
import config
import io
import uuid
from data_stores.AzureBlobObjects import AzureBlobObjects as ABO
from initializers import extract_data_for_review as edr

def allowed_file(filename: str, extension: str):
    """Checks if filename has allowed extension.
    ### Example:
    filename = '28.pdf', extension = 'pdf' will return true
    """
    actualExtension = filename.rsplit(".")[-1]
    return actualExtension == extension


def upload_blob_file(filepath: str, containerName: str):
    """Upload file specified in filepath to Azure blob.
    ### Args:
        filepath: filepath with file to be uploaded
    ### Returns: 
        void
    """
    container_client = ABO.get_container_client(containerName)
    filename = filepath.rsplit("/")[-1]
    print("filename about to be uploaded to blob: " + filename)
    with open(filepath, mode="rb") as data:
        blob_client = container_client.upload_blob(name=filename, data=data, overwrite=True)

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
    listOfGeneratedExcelNames = getListOfFilenamesInContainer(config.generatedExcel_container_name)
    for name in listOfPDFNames:
        chapterNumber = name.rsplit('.')[0]
        excelName = chapterNumber + '.xlsx'
        tableRow = [chapterNumber,name]
        if excelName in listOfGeneratedExcelNames: tableRow.append(excelName)
        else: tableRow.append('Nil')
        tableRow += ['d2','d3','status']
        # tableRows.append([chapterNumber,name,'d1','d2','d3','uploaded'])
        tableRows.append(tableRow)
    return tableRows

def download_blob_file(filename: str, containerName: str):
    """Download file specified in filename from Azure blob to an appropriate local directory.
    ### Args:
            filename: filename to be downloaded from Azure blob
    ### Returns: 
            void
    """
    container_client = ABO.get_container_client(containerName)
    print("filename about to be downloaded from blob: " + filename)
    blob_client = container_client.get_blob_client(blob=filename)
    filepath = os.path.join('files/', filename)
    with open(filepath, mode="wb") as data:
        try: 
            download_stream = blob_client.download_blob()
            data.write(download_stream.readall())
        except ResourceNotFoundError:
            print("The file was not found, maybe user clicked on a Nil cell")

def convertPDFToExcelForReview(pdfFilepath) -> tuple[str, str] | None:
    """Converts the pdf in the given filepath to excel
    ### Returns:
        filepath of the saved excel (position 0), and filepath of the saved dict (position 1) as a tuple
    """
    reviewFilepaths = None
    try: reviewFilepaths = edr.savePdfToExcelAndStringsForReview(pdfFilepath)
    except Exception as e:
        print("Error processing file @ " + pdfFilepath + " Error: " + str(type(e)) + ": " + str(e))
        print("Using non-strict extraction")
        try: reviewFilepaths = edr.savePdfToExcelAndStringsForReview(pdfFilepath,strict=False)
        except Exception as e:
            print("Error processing file non-strictly @ " + pdfFilepath + " Error: " + str(type(e)) + ": " + str(e))
    return reviewFilepaths