import config
import os
import openai
from dotenv import load_dotenv, find_dotenv
import app_functions.findByHSCode as fhsc

def vectorStoreSearch(question, data_dict, ids_hscodes_dict):
    _ = load_dotenv(find_dotenv()) # read local .env file
    openai.api_key = os.environ['OPENAI_API_KEY']

    from app_functions.findByHSCode import findByHSCode
    print("vector store search called")

    if config.vectorstore == "chroma":
        vectorStoreFunction = vectorStoreSearchChroma
    elif config.vectorstore == "azure_cosmos_nosql":
        vectorStoreFunction = vectorStoreSearchAzureCosmosNoSQL
    else:
        print("Vector store to be used not specified in config.py")
        return []
    
    search_results = vectorStoreFunction(question)
    print(search_results[0])

    results = convertSearchResults(search_results, data_dict, ids_hscodes_dict)
    return results



def vectorStoreSearchChroma(question):
    try:
        print("Using chroma vector store...")

        from langchain_community.vectorstores import Chroma
        persist_directory = 'initializers/create_vectorstores/vectorstores/chroma'

        from langchain_community.embeddings import OpenAIEmbeddings
        embedding = OpenAIEmbeddings()

        vectordb = Chroma(
            embedding_function=embedding,
            persist_directory=persist_directory
        )
        print("vector db collection count:")
        print(vectordb._collection.count())

        search_results = vectordb.max_marginal_relevance_search(question,k=20,lambda_mult=0.25)
        return search_results
    except:
        print(Exception)
        return []
    


def vectorStoreSearchAzureCosmosNoSQL(question):
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

        from langchain.embeddings.openai import OpenAIEmbeddings
        embedding = OpenAIEmbeddings()

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







        






def convertSearchResults(search_results, data_dict, ids_hscodes_dict):
    results = []
    for search_result in search_results:
        if config.vectorstore == "azure_cosmos_nosql":
            id = search_result.metadata["id"]
            hscode = ids_hscodes_dict[id]
        else:
            hscode = search_result.metadata["HS Code"]
        item = fhsc.findByHSCode(hscode, data_dict)
        results.append(item[0])

    return results
    