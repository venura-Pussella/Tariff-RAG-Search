import config
import os
import app_functions.findByHSCode as fhsc
from langchain_community.vectorstores.azure_cosmos_db_no_sql import AzureCosmosDBNoSqlVectorSearch

def vectorStoreSearch(question, data_dict, vectorstore: AzureCosmosDBNoSqlVectorSearch, ids_hscodes_dict=None):
    """Searches the dictionary containing all tariff pdf information for line items by comparing vectorstore embeddings against 
    the embedding of the user query, and returns a list of line items.
    Args:
        question: question/text to embed and compare with the vectorstore
        data_dict: dictionary containing all tariff pdf information
        vectostore: vectorstore reference to be used
        ids_hscodes_dict: contains azure comsos db IDs to HScodes mapping, needed in case azure cosmos db is used (as a workaround due to 
            the langchain similarity search to azure cosmos not returning hs code metadata)
    Returns:
        List of line items
    """
    # ct = datetime.datetime.now()
    # print("|||VectorStoreSearch Called - " + str(ct))


    print("Vector store search called")
    results = []
    search_results_and_scores = vectorstore.similarity_search_with_score(query=question, k=100)
    search_results = []
    scores = []
    for search_result_and_score in search_results_and_scores:
        search_results.append(search_result_and_score[0])
        scores.append(search_result_and_score[1])
    results = convertSearchResults(search_results, data_dict, ids_hscodes_dict)

    return (results, scores)




def convertSearchResults(search_results, data_dict, ids_hscodes_dict=None) -> list[dict]:
    """ Returns a list of line items that correspond to the search results obtained from a vectorstore
    Args:
        search_results: langchain documents returned by a vectorstore
        data_dict: the dictionary containing the .jsons representing tariff pdfs and their line items
        ids_hscodes_dict: dictionary containing mapping of azure cosmos DB ids to HS codes (required in case search results
            are from azure cosmos db, as it does not return our custom metadata (inlcuding hs code) due to a bug/limitation in
            the langchain similarity search function (as seen in its source code))
    Returns:
        List of line items
    """
    results = []
    for search_result in search_results:
        if config.vectorstore == "azure_cosmos_nosql": # as mentioned above, need to use workaround to get hscode from cosmos search result
            id = search_result.metadata["id"]
            hscode = ids_hscodes_dict[id]
        else:
            hscode = search_result.metadata["HS Code"]
        item = fhsc.findByHSCode(hscode, data_dict)
        try: results.append(item[0]) # came across one case where a line item had been created without an hs code because there was a row without a line item but with a unit
        except Exception as e: print(e); continue

    return results
    

def getVectorStore():
    """Connects to and tries to return vectorstore object.
    """
    if config.vectorstore == "azure_cosmos_nosql":
        return getAzureCosmosVectorstore()
    elif config.vectorstore == "chroma":
        print("Code for getting chroma vectorstore not yet implemented")
        return None
    else:
        print("Valid vectorstore not configured in config.py")
        return None


def getAzureCosmosVectorstore():
    """Connects to and tries to return Azure Cosmos vectorstore object.
    Returns:
        vectorstore: OPTIONAL (AzureCosmosDBNoSqlVectorSearch)
    """
    try:
        print("Creating Azure Cosmos NoSQL vectorstore reference...")

        from azure.cosmos import CosmosClient, PartitionKey
        from langchain_community.vectorstores.azure_cosmos_db_no_sql import (
            AzureCosmosDBNoSqlVectorSearch,
        )

        HOST = os.environ["COSMOS_ENDPOINT"]
        KEY = os.environ["COSMOS_KEY"]

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

        cosmos_client = CosmosClient(HOST, KEY)
        database_name = config.cosmosNoSQLDBName
        container_name = config.cosmosNoSQLContainerName
        partition_key = PartitionKey(path="/id")
        cosmos_container_properties = {"partition_key": partition_key}
        cosmos_database_properties = {"id": database_name}

        from initializers import getEmbeddings as emb
        embedding = emb.getEmbeddings()

        vectorstore = AzureCosmosDBNoSqlVectorSearch(
            cosmos_client=cosmos_client,
            embedding=embedding,
            database_name=database_name,
            container_name=container_name,
            vector_embedding_policy=vector_embedding_policy,
            indexing_policy=indexing_policy,
            cosmos_container_properties=cosmos_container_properties,
            cosmos_database_properties=cosmos_database_properties
        )

        return vectorstore
    except Exception as e: 
        print("Exception @ getAzureCosmosVectorstore() ")
        print(e)
        return None