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
    indexing_policy = {
        "indexingMode": "consistent",
        "includedPaths": [{"path": "/*"}],
        "excludedPaths": [{"path": '/"_etag"/?'}],
        "vectorIndexes": [{"path": "/embedding", "type": "quantizedFlat"}],
    }
    vector_embedding_policy = {
        "vectorEmbeddings": [
            {
                "path": "/embedding",
                "dataType": "float32",
                "distanceFunction": "cosine",
                "dimensions": 1536,
            }
        ]
    }

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
                database = CosmosObjects.__cosmosClient.create_database_if_not_exists(id=config.cosmosNoSQLDBName)
                print(f"Database created or returned: {database.id}")

            except AzureCosmosExceptions.CosmosHttpResponseError:
                print("Request to the Azure Cosmos database service failed.")
        
        return CosmosObjects.__cosmosDatabase
    

    @classmethod
    def getCosmosContainer(cls) -> AzureCosmosContainer.ContainerProxy:
        if CosmosObjects.__cosmosContainer == None:
            try:
                partition_key_path = PartitionKey(path="/categoryId")
                container = CosmosObjects.__cosmosDatabase.create_container_if_not_exists(
                    id=config.cosmosNoSQLContainerName,
                    partition_key=partition_key_path,
                    offer_throughput=400,
                )
                print(f"Container created or returned: {container.id}")

            except AzureCosmosExceptions.CosmosHttpResponseError:
                print("Request to the Azure Cosmos database service failed.")

        return CosmosObjects.__cosmosContainer
    

    