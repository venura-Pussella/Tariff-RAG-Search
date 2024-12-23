import os
import logging
from azure.storage.blob import BlobServiceClient, ContainerClient
import config
from azure.core.exceptions import ServiceRequestError, ResourceNotFoundError
from io import BytesIO

class AzureBlobObjects:
    """Singleton class to hold blob-service-client and container clients. Contains methods to use them.
    https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python?tabs=managed-identity%2Croles-azure-portal%2Csign-in-azure-cli&pivots=blob-storage-quickstart-scratch
    https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-python-get-started?tabs=azure-ad
    """

    __blob_service_client = None
    __container_clients: dict[str,ContainerClient] = {}

    @classmethod
    def get_blob_service_client(cls):
        if cls.__blob_service_client == None:
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            cls.__blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        return cls.__blob_service_client
    
    @classmethod
    def get_container_client(cls, containerName: str):
        try:
            if containerName not in cls.__container_clients.keys():
                blob_service_client = cls.get_blob_service_client()
                containerClient = blob_service_client.get_container_client(container=containerName)
                if not containerClient.exists():
                    containerClient = blob_service_client.create_container(name=containerName)
                cls.__container_clients[containerName] = containerClient
        except ServiceRequestError:
            logging.error('Service Request Error. Also check if the server is connected to the internet.')
            return None

        return cls.__container_clients[containerName]
    
    @classmethod
    def getListOfFilenamesInContainer(cls, containerName: str) -> list[str]:
        containerClient = cls.get_container_client(containerName)
        blobName_list = containerClient.list_blob_names()
        return list(blobName_list)
    
    @classmethod
    def upload_blob_file(cls, filepath: str, containerName: str, file_rename: str = None):
        """Upload file specified in filepath to the specified container in Azure storage.
        Can specifiy file_rename if the file should be with a different name in Azure storage.
        """
        filename = os.path.basename(filepath)
        container_client = cls.get_container_client(containerName)
        logging.info("filename about to be uploaded to blob: " + filename)
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
        logging.info("file about to be uploaded to blob from stream with given filename: " + file_name)
        blob_client.upload_blob(filestream, blob_type="BlockBlob", overwrite=True)

    @classmethod
    def download_blob_file(cls, filename: str, containerName: str, savepath: str):
        """Download file specified in filename from Azure blob to the specified file path.
        """
        container_client = cls.get_container_client(containerName)
        logging.info("filename about to be downloaded from blob: " + filename)
        blob_client = container_client.get_blob_client(blob=filename)
        with open(savepath, mode="wb") as data:
            try: 
                download_stream = blob_client.download_blob()
                data.write(download_stream.readall())
            except ResourceNotFoundError:
                logging.error(f"The file was not found. Filename received:{filename}")

    @classmethod
    def download_blob_file_to_stream(cls, filename: str, containerName: str) -> BytesIO:
        """Download file specified in filename from Azure blob to the specified file path.
        """
        container_client = cls.get_container_client(containerName)
        logging.info("filename about to be downloaded from blob: " + filename)
        blob_client = container_client.get_blob_client(blob=filename)
        stream = BytesIO()
        try: 
            blob_client.download_blob().readinto(stream)
            stream.seek(0)
        except ResourceNotFoundError:
            logging.error(f"The file was not found. Filename received:{filename}")
        return stream