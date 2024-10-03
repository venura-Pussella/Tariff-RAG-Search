from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos import exceptions as AzureCosmosExceptions
from azure.cosmos import database as AzureCosmosDatabase
from azure.cosmos import container as AzureCosmosContainer
import os
import config

class CosmosObjects:

    __cosmosClient: CosmosClient = None
    __cosmosDatabase: AzureCosmosDatabase.DatabaseProxy = None
    __cosmosContainer: AzureCosmosContainer.ContainerProxy = None
    
    @classmethod
    def getCosmosClient(cls) -> CosmosClient:
        if CosmosObjects.__cosmosClient == None:
            ENDPOINT = os.environ["COSMOS_ENDPOINT"]
            KEY = os.environ["COSMOS_KEY"]
            CosmosObjects.__cosmosClient = CosmosClient(url=ENDPOINT, credential=KEY)
            print("Azure Cosmos client created using URL and key given in config.py")

        return CosmosObjects.__cosmosClient


    @classmethod
    def getCosmosDatabase(cls) -> AzureCosmosDatabase.DatabaseProxy:
        if CosmosObjects.__cosmosDatabase == None:
            try:
                cosmosClient = CosmosObjects.getCosmosClient()
                CosmosObjects.__cosmosDatabase = cosmosClient.create_database_if_not_exists(id=config.cosmosNoSQLDBName)
                print(f"Database created or returned: {CosmosObjects.__cosmosDatabase.id}")

            except AzureCosmosExceptions.CosmosHttpResponseError:
                print("Request to the Azure Cosmos database service failed.")
        
        return CosmosObjects.__cosmosDatabase
    

    @classmethod
    def getCosmosContainer(cls) -> AzureCosmosContainer.ContainerProxy:
        if CosmosObjects.__cosmosContainer == None:
            try:
                partition_key_path = PartitionKey(path="/categoryId")
                database = CosmosObjects.getCosmosDatabase()
                CosmosObjects.__cosmosContainer = database.create_container_if_not_exists(
                    id=config.cosmosNoSQLContainerName,
                    partition_key=partition_key_path,
                    offer_throughput=400,
                )
                print(f"Container created or returned: {CosmosObjects.__cosmosContainer.id}")

            except AzureCosmosExceptions.CosmosHttpResponseError:
                print("Request to the Azure Cosmos database service failed.")

        return CosmosObjects.__cosmosContainer
    

    