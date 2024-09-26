def createVectorstoreUsingAzureCosmosNoSQL(docs: list): 
    """Creates & returns vectorstore in Azure Cosmos NoSQL using the passed in list of langchain documents
    Args:
        docs: list of langchain documents
    Returns:
        vectorstore (Azure cosmos nosql)
    """
    import os
    import openai
    import config
    import json

    from dotenv import load_dotenv, find_dotenv
    _ = load_dotenv(find_dotenv()) # read local .env file
    openai.api_key = os.environ['OPENAI_API_KEY']

    from initializers import getEmbeddings as emb
    embedding = emb.getEmbeddings()

    # policy for vectorstore in cosmos
    indexing_policy = {
        "indexingMode": "consistent",
        "includedPaths": [{"path": "/*"}],
        "excludedPaths": [{"path": '/"_etag"/?'}],
        "vectorIndexes": [{"path": "/embedding", "type": "quantizedFlat"}],
    }

    # policy for vectorstore in cosmos
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

    from azure.cosmos import CosmosClient, PartitionKey
    from langchain_community.vectorstores.azure_cosmos_db_no_sql import (AzureCosmosDBNoSqlVectorSearch,)

    HOST = os.environ["COSMOS_ENDPOINT"]
    KEY = os.environ["COSMOS_KEY"]
    cosmos_client = CosmosClient(HOST, KEY)
    database_name = config.cosmosNoSQLDBName
    container_name = config.cosmosNoSQLContainerName
    partition_key = PartitionKey(path="/id")
    cosmos_container_properties = {"partition_key": partition_key}
    cosmos_database_properties = {"id": database_name}

    #extract text part and metadata from the langchain documents into python lists
    texts = []
    metadatas = []
    for doc in docs:
        texts.append(doc.page_content)
        metadatas.append(doc.metadata)


    #delete existing container to avoid adding duplicates to vectorstore
    print("Deleting existing items in cosmos db to prepare for new items...")
    database = cosmos_client.create_database_if_not_exists(id=database_name)
    database.delete_container(container=container_name)

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

    
    #add new data into the vectorstore
    print("adding items to vectorstore... ~40s per tarrif pdf")
    ids = vectorstore.add_texts(
        texts = texts,
        embedding=embedding,
        metadatas= metadatas, 
    )
    hscodes = []
    for md in metadatas:
        hscodes.append(md["HS Code"])
    ids_hscode_dict = dict(zip(ids, hscodes))
    json_string = json.dumps(ids_hscode_dict)
    with open('initializers/create_vectorstores/ids_hscode_dict.json','w') as file:
        file.write(json_string)

    print("Cosmos vectorstore created or overwritten.")
    #to-do
    #print number of items in container

    return vectorstore


