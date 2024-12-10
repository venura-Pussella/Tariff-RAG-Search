import os
from azure.storage.blob import BlobServiceClient
import config
from azure.core.exceptions import ServiceRequestError, ResourceNotFoundError
from io import BytesIO

class AzureBlobObjects:
    """Singleton class to hold blob-service-client and container clients. Contains methods to retrieve them, and the getListOfFilenamesInContainer(cls, containerName: str) -> list[str]:
    """

    __blob_service_client = None
    __pdf_container_client = None
    __generatedExcel_container_client = None
    __generatedDict_container_client = None
    __reviewedExcel_container_client = None
    __json_container_client = None
    __cosmos_ids_container_client = None

    containerClientToNameMapping = {
        config.pdf_container_name: __pdf_container_client,
        config.generatedExcel_container_name: __generatedExcel_container_client,
        config.generatedDict_container_name: __generatedDict_container_client,
        config.reviewedExcel_container_name: __reviewedExcel_container_client,
        config.json_container_name: __json_container_client,
        config.cosmos_ids_container_name: __cosmos_ids_container_client
    }

    @classmethod
    def get_blob_service_client(cls):
        if cls.__blob_service_client == None:
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            cls.__blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        return cls.__blob_service_client
    
    @classmethod
    def get_container_client(cls, containerName: str):
        relevantPrivateContainerClient = cls.containerClientToNameMapping[containerName]

        try:
            if relevantPrivateContainerClient == None:
                blob_service_client = cls.get_blob_service_client()
                relevantPrivateContainerClient = blob_service_client.get_container_client(container=containerName)
                if not relevantPrivateContainerClient.exists():
                    relevantPrivateContainerClient = blob_service_client.create_container(name=containerName)
        except ServiceRequestError:
            print('Service Request Error. Also check if the server is connected to the internet.')

        return relevantPrivateContainerClient
    
    @classmethod
    def getListOfFilenamesInContainer(cls, containerName: str) -> list[str]:
        containerClient = cls.get_container_client(containerName)
        blobName_list = containerClient.list_blob_names()
        return list(blobName_list)
    
    @classmethod
    def upload_blob_file(cls, filepath: str, containerName: str, file_rename: str = None):
        """Upload file specified in filepath to the specified container in Azure storage.
        """
        filename = os.path.basename(filepath)
        container_client = cls.get_container_client(containerName)
        print("filename about to be uploaded to blob: " + filename)
        with open(filepath, mode="rb") as data:
            if file_rename: container_client.upload_blob(name=file_rename, data=data, overwrite=True)
            else: container_client.upload_blob(name=filename, data=data, overwrite=True)

    @classmethod
    def upload_to_blob_from_stream(cls, filestream: BytesIO, containerName: str, file_name: str):
        """Upload file specified in filepath to the specified container in Azure storage.
        """
        cls.get_container_client(containerName) # this will creates container if it doesn't exist already
        blob_service_client = cls.get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(container=containerName, blob=file_name)
        print("file about to be uploaded to blob from stream with given filename: " + file_name)
        blob_client.upload_blob(filestream, blob_type="BlockBlob")

    @classmethod
    def download_blob_file(cls, filename: str, containerName: str, savepath: str):
        """Download file specified in filename from Azure blob to the specified file path.
        """
        container_client = cls.get_container_client(containerName)
        print("filename about to be downloaded from blob: " + filename)
        blob_client = container_client.get_blob_client(blob=filename)
        with open(savepath, mode="wb") as data:
            try: 
                download_stream = blob_client.download_blob()
                data.write(download_stream.readall())
            except ResourceNotFoundError:
                print("The file was not found, maybe user clicked on a Nil cell")

    @classmethod
    def download_blob_file_to_stream(cls, filename: str, containerName: str) -> BytesIO:
        """Download file specified in filename from Azure blob to the specified file path.
        """
        container_client = cls.get_container_client(containerName)
        print("filename about to be downloaded from blob: " + filename)
        blob_client = container_client.get_blob_client(blob=filename)
        stream = BytesIO()
        try: 
            blob_client.download_blob().readinto(stream)
            stream.seek(0)
        except ResourceNotFoundError:
            print("The file was not found, maybe user clicked on a Nil cell")
        return stream