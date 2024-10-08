import os
from azure.storage.blob import BlobServiceClient
import config
# from azure.core.exceptions import ResourceExistsError

class AzureBlobObjects:

    __blob_service_client = None
    __pdf_container_client = None
    __generatedExcel_container_client = None
    __reviewedExcel_container_client = None
    __json_container_client = None

    containerClientToNameMapping = {
        config.pdf_container_name: __pdf_container_client,
        config.generatedExcel_container_name: __generatedExcel_container_client,
        config.reviewedExcel_container_name: __reviewedExcel_container_client,
        config.json_container_name: __json_container_client
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

        if relevantPrivateContainerClient == None:
            blob_service_client = cls.get_blob_service_client()
            relevantPrivateContainerClient = blob_service_client.get_container_client(container=containerName)
            if not relevantPrivateContainerClient.exists():
                relevantPrivateContainerClient = blob_service_client.create_container(name=containerName)

        return relevantPrivateContainerClient