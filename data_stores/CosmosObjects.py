from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos import exceptions as AzureCosmosExceptions
from azure.cosmos import database as AzureCosmosDatabase
from azure.cosmos import container as AzureCosmosContainer
import os
import logging
import config

class CosmosObjects:
    """Singleton class to hold cosmos objects. (So that wasteful similar calls to cosmos are not made, each time a reference to an object is required).
    
    Attributes:
        __cosmosClient: CosmosClient = None
        __cosmosDatabase: AzureCosmosDatabase.DatabaseProxy = None
        __cosmosContainer: AzureCosmosContainer.ContainerProxy = None

    Methods:
        3 Methods to get each of the above attributes
    """

    __cosmosClient: CosmosClient = None
    __cosmosDatabase: AzureCosmosDatabase.DatabaseProxy = None
    __cosmosContainer: AzureCosmosContainer.ContainerProxy = None
    
    @classmethod
    def getCosmosClient(cls) -> CosmosClient:
        """Singleton method to return a Cosmos object"""
        if CosmosObjects.__cosmosClient == None:
            ENDPOINT = os.environ["COSMOS_ENDPOINT"]
            KEY = os.environ["COSMOS_KEY"]
            CosmosObjects.__cosmosClient = CosmosClient(url=ENDPOINT, credential=KEY)
            logging.info("Azure Cosmos client created using URL and key given in config.py")

        return CosmosObjects.__cosmosClient


    @classmethod
    def getCosmosDatabase(cls) -> AzureCosmosDatabase.DatabaseProxy:
        """Singleton method to return a Cosmos object"""
        if CosmosObjects.__cosmosDatabase == None:
            try:
                cosmosClient = CosmosObjects.getCosmosClient()
                CosmosObjects.__cosmosDatabase = cosmosClient.create_database_if_not_exists(id=config.cosmosNoSQLDBName)
                logging.info(f"Database created or returned: {CosmosObjects.__cosmosDatabase.id}")

            except AzureCosmosExceptions.CosmosHttpResponseError:
                logging.error("Request to the Azure Cosmos database service failed.")
        
        return CosmosObjects.__cosmosDatabase
    

    @classmethod
    def getCosmosContainer(cls) -> AzureCosmosContainer.ContainerProxy:
        """Singleton method to return a Cosmos object"""
        if CosmosObjects.__cosmosContainer == None:
            try:
                partition_key_path = PartitionKey(path="/categoryId")
                database = CosmosObjects.getCosmosDatabase()
                CosmosObjects.__cosmosContainer = database.create_container_if_not_exists(
                    id=config.cosmosNoSQLContainerName,
                    partition_key=partition_key_path,
                    offer_throughput=400,
                )
                logging.info(f"Container created or returned: {CosmosObjects.__cosmosContainer.id}")

            except AzureCosmosExceptions.CosmosHttpResponseError:
                logging.error("Request to the Azure Cosmos database service failed.")

        return CosmosObjects.__cosmosContainer
    

    