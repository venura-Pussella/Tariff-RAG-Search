import config
import os
import openai
from dotenv import load_dotenv, find_dotenv
import app_functions.findByHSCode as fhsc

def vectorStoreSearch(question, data_dict, ids_hscodes_dict=None):
    """Searches the dictionary containing all tariff pdf information for line items by comparing vectorstore embeddings against 
    the embedding of the user query, and returns a list of line items.
    Args:
        question: question/text to embed and compare with the vectorstore
        data_dict: dictionary containing all tariff pdf information
        hscodes_dict: contains azure comsos db IDs to HScodes mapping, needed in case azure cosmos db is used (as a workaround due to 
            the langchain similarity search to azure cosmos not returning hs code metadata)
    Returns:
        List of line items
    """
    _ = load_dotenv(find_dotenv()) # read local .env file
    openai.api_key = os.environ['OPENAI_API_KEY']

    print("Vector store search called")
    results = []

    if config.vectorstore == "chroma": vectorStoreFunction = vectorStoreSearchChroma
    elif config.vectorstore == "azure_cosmos_nosql": vectorStoreFunction = vectorStoreSearchAzureCosmosNoSQL
    else:
        print("Vector store to be used not specified in config.py")
        return []
    
    search_results = vectorStoreFunction(question)

    results = convertSearchResults(search_results, data_dict, ids_hscodes_dict)
    return results



def vectorStoreSearchChroma(question) -> list:
    """Embeds question and passes it to the chroma vectorstore and returns search results as list of langchain documents
    Args:
        question: question to be embedded and compared in the vectorstore
    Returns:
        Search results from the vectorstore, as a list of langchain documents
    """
    try:
        print("Using chroma vector store...")

        from langchain_community.vectorstores import Chroma
        persist_directory = 'initializers/create_vectorstores/vectorstores/chroma'

        from initializers import getEmbeddings as emb
        embedding = emb.getEmbeddings()

        vectordb = Chroma(
            embedding_function=embedding,
            persist_directory=persist_directory
        )
        print("vector db collection count:")
        print(vectordb._collection.count())

        # search_results = vectordb.max_marginal_relevance_search(question,k=20,lambda_mult=0.25)
        search_results = vectordb.similarity_search(question,k=5)

        return search_results
    except:
        print(Exception)
        return []
    


def vectorStoreSearchAzureCosmosNoSQL(question):
    """Embeds question and passes it to the Azure Cosmos NoSQL vectorstore and returns search results as list of langchain documents
    Args:
        question: question to be embedded and compared in the vectorstore
    Returns:
        Search results from the vectorstore, as a list of langchain documents
    """
    try:
        print("Using Azure Cosmos NoSQL vector store...")

        from azure.cosmos import CosmosClient, PartitionKey
        from langchain_community.vectorstores.azure_cosmos_db_no_sql import (
            AzureCosmosDBNoSqlVectorSearch,
        )
        # from langchain_openai import AzureOpenAIEmbeddings
        import openai
        openai.api_key = os.environ['OPENAI_API_KEY']

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
        database_name = "langchain_python_db"
        container_name = "langchain_python_container"
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


        #search_results = vectorstore.max_marginal_relevance_search(question,k=20,lambda_mult=0.25)
        search_results = vectorstore.similarity_search(question,k=5) # what if search_results is empty
        return search_results
    except Exception as e: 
        print(e)
        return []





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
    