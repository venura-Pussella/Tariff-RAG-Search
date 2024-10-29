import config
import os
import config
from other_funcs.tokenTracker import TokenTracker as tok
from other_funcs import getEmbeddings as emb
import datetime
import pickle
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from data_stores.AzureTableObjects import AzureTableObjects as ato
from azure.core import exceptions
from initializers.Line_Item import Line_Item
from data_stores.CosmosObjects import CosmosObjects as co
import uuid

def createVectorstoreUsingAzureCosmosNoSQL(documents: list[Line_Item], chapterNumber: int, mutexKey: str): 
    """Feeds to given langchain documents to the Cosmos DB.
    Chapter number and mutex key required to update the record.
    Does not necessarily create the store from scratch despite what the name might suggest
    """
    vectorstore = getLangchainVectorstore() # get vectorstore object

    # get the current cosmos document IDs of the chapter we are attempting to upload
    cosmos_ids_filename = str(chapterNumber) + '.pkl'
    cosmos_ids_container_client = abo.get_container_client(config.cosmos_ids_container_name)
    blob_client = cosmos_ids_container_client.get_blob_client(cosmos_ids_filename)
    try:
        existing_cosmos_ids_pickle_stream = blob_client.download_blob()
        cosmosIDs: list = pickle.loads(existing_cosmos_ids_pickle_stream.readall())
    except exceptions.ResourceNotFoundError:
        cosmosIDs: list = None

    # if required delete existing chapter uploads, to prevent duplicate entries in cosmos db
    try:
        ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.deletingExistingCosmosDocs)
        for cosmosID in cosmosIDs:
            vectorstore.delete_document_by_id(cosmosID)
            print("Deleted cosmos ID: " + str(cosmosID))
        ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.deletingExistingCosmosIDTracker)
        blob_client.delete_blob()
    except TypeError as e:
        print("Retrieved existing cosmosIDs list is not an iterable object. Maybe this is the first time this chapter is been uploaded to cosmos. Chapter number: " + str(chapterNumber)+ 'Error: '+ str(e))

    
    # Add the new documents (line items) to the vector-store
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.addingdNewDocsToCosmos)
    ct = datetime.datetime.now()
    print("Adding chapter " + str(chapterNumber) +" items to cosmos begin: - " + str(ct))
    print("Total number of line items in chapter " + str(chapterNumber) + " to be added: " + str(len(documents)))
    allIDs = []

    container = co.getCosmosContainer()
    for document in documents:
        text_fields:dict = document.fields_to_embed
        vector = document.vector
        metadata = document.metadata_fields

        vector_dict = {"embedding": vector}
        id = str(uuid.uuid4())
        final_dict_for_item = {"id": id}

        final_dict_for_item.update(text_fields); final_dict_for_item.update(metadata); final_dict_for_item.update(vector_dict)

        container.create_item(body=final_dict_for_item)
        allIDs.append(id)


    allIDs_bytes = pickle.dumps(allIDs)
    
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.addingNewCosmosIdTracker)
    blob_client.upload_blob(allIDs_bytes, blob_type="BlockBlob")
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus='', newRecordState=config.RecordState.excelUploaded)
    ato.release_mutex(chapterNumber, mutexKey)
    
    ct = datetime.datetime.now()
    print("Chapter "+ str(chapterNumber) + " |||Adding items to cosmos end: - " + str(ct))

def getLangchainVectorstore():
    """Simply returns a langchain reference object to our Cosmos DB
    """
    embedding = emb.getEmbeddings.getEmbeddings()

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

    

    #create blank vectorstore (or get an already created one)
    print("Getting langchain vectorstore object.")
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
    print("Langchain vector store returned.")
    return vectorstore

def deleteChapterFromCosmos(chapterNumber: int):
    vectorstore = getLangchainVectorstore()

    cosmos_ids_filename = str(chapterNumber) + '.pkl'
    cosmos_ids_container_client = abo.get_container_client(config.cosmos_ids_container_name)
    blob_client = cosmos_ids_container_client.get_blob_client(cosmos_ids_filename)
    try:
        existing_cosmos_ids_pickle_stream = blob_client.download_blob()
        cosmosIDs: list = pickle.loads(existing_cosmos_ids_pickle_stream.readall())
    except exceptions.ResourceNotFoundError:
        cosmosIDs: list = None
        print("Cannot find a cosmos IDs pickle for the provided chapter: " + str(chapterNumber))
        return

    # if required delete existing chapter uploads, to prevent duplicate entries in cosmos db
    try:
        for cosmosID in cosmosIDs:
            vectorstore.delete_document_by_id(cosmosID)
            print("Deleted cosmos ID: " + str(cosmosID))
        blob_client.delete_blob()
    except TypeError as e:
        print("Retrieved existing cosmosIDs list is not an iterable object. Maybe this is the first time this chapter is been uploaded to cosmos. Chapter number: " + str(chapterNumber)+ 'Error: '+ str(e))

