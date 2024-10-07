import config
import os
from langchain_core.documents import Document
import config
from other_funcs.tokenTracker import TokenTracker as tok
from other_funcs import getEmbeddings as emb


def createVectorstoreUsingAzureCosmosNoSQL(docs: list): 
    """Creates vectorstore in Azure Cosmos NoSQL using the passed in list of langchain documents
    ### Args:
        docs: list of langchain documents
    """    

    embedding = emb.getEmbeddings.getEmbeddings()
    vectorstore = createBlankCosmosVectorstore(embedding)
    
    # Add text to the vectorstore without hitting the embeddings rate limit
    # 120k for Azure OpenAI Embeddings, 1M for OpenAI Embeddings
    rateLimit = 0
    if config.embeddings == "AzureOpenAI": rateLimit = 120000
    elif config.embeddings == "OpenAI": rateLimit = 1000000

    n = 0
    tokenCount = 0
    texts = []
    metadatas = []
    allMetaDatas = []
    allIDs = []

    print("Total number of line items to be added: " + str(len(docs)))
    print("Takes about 15 mins to add 3300 line items")

    while n < len(docs):
        doc: Document = docs[n]
        text = doc.page_content
        metadata = doc.metadata
        tokenCount += tok.getTokenCount(text)
        if (tokenCount >= rateLimit):
            tokenCount = 0 # reset tokencount
            n -= 1
            ids = vectorstore.add_texts(
                texts = texts,
                embedding=embedding,
                metadatas= metadatas, 
            )
            print("Added "+ str(len(ids)) + " line items.")
            # the above process is so slow, that there is no need to worry about hitting the rate limit, so no need to sleep the script
            texts = []
            metadatas = []
            allIDs = allIDs + ids
        else:
            texts.append(text)
            metadatas.append(metadata)
            allMetaDatas.append(metadata)
        n += 1

    # add the leftovers also to the vectorstore
    ids = vectorstore.add_texts(
        texts = texts,
        embedding=embedding,
        metadatas= metadatas, 
    )
    print("Added "+ str(len(ids)) + " line items.")
    allIDs = allIDs + ids
    
    print("Cosmos vectorstore created or overwritten.")
    #to-do
    #print number of items in container



def createBlankCosmosVectorstore(embedding):
    """Deletes existing container (just in case to stop adding duplicate info). And creates and returns new cosmos vectorstore.
    Langchain used for this process, #todo - can remove it and do it directly.
    ### Args:
        embedding: pass in embedding here
    ### Returns:
        Returns blank vectorstore
    """

    # policy for vectorstore in cosmos
    indexing_policy = config.indexing_policy

    # policy for vectorstore in cosmos
    vector_embedding_policy = config.vector_embedding_policy

    from azure.cosmos import CosmosClient, PartitionKey, exceptions
    from langchain_community.vectorstores.azure_cosmos_db_no_sql import (AzureCosmosDBNoSqlVectorSearch,)

    HOST = os.environ["COSMOS_ENDPOINT"]
    KEY = os.environ["COSMOS_KEY"]
    cosmos_client = CosmosClient(HOST, KEY)
    database_name = config.cosmosNoSQLDBName
    container_name = config.cosmosNoSQLContainerName
    partition_key = PartitionKey(path="/id")
    cosmos_container_properties = {"partition_key": partition_key}
    cosmos_database_properties = {"id": database_name}

    


    #delete existing container to avoid adding duplicates to vectorstore
    print("Deleting existing items in cosmos db to prepare for new items...")
    database = cosmos_client.create_database_if_not_exists(id=database_name)
    try: database.delete_container(container=container_name)
    except exceptions.CosmosHttpResponseError:
        print("Container has already been deleted or does not exist.")

    #create blank vectorstore (or get an already created one)
    print("Creating blank vector store in cosmos or fetching already exsting one.")
    vectorstore = AzureCosmosDBNoSqlVectorSearch(
        cosmos_client=cosmos_client,
        database_name=database_name,
        container_name=container_name,
        vector_embedding_policy=vector_embedding_policy,
        indexing_policy=indexing_policy,
        cosmos_container_properties=cosmos_container_properties,
        cosmos_database_properties=cosmos_database_properties,
        embedding=embedding,
    )
    print("Blank vector store returned.")
    return vectorstore


