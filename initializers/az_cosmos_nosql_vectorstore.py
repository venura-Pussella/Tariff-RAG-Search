# Contains functions used to interact with the Azure Cosmos Vectorstore.

import concurrent.futures
import uuid
import os
import datetime
import logging
import pickle

from azure.core import exceptions

import config
from other_funcs import getEmbeddings as emb
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from data_stores.AzureTableObjects import AzureTableObjects as ato
from initializers.Line_Item import Line_Item
from data_stores.CosmosObjects import CosmosObjects as co


def createVectorstoreUsingAzureCosmosNoSQL(documents: list[Line_Item], chapterNumber: int, mutexKey: str, release_date: str): 
    """Feeds to given Line_Item objects to the Cosmos DB.
    Does not necessarily create the store from scratch despite what the name might suggest (alltho it can if it's the first time of a new release).
    chapterNumber and release_date used for tracking record and files.
    Args:
        documents (list[Line_Item]): _description_
        chapterNumber (int): _description_
        mutexKey (str): _description_
        release_date (str): _description_
    """
    vectorstore = getLangchainVectorstore(release_date) # get vectorstore object

    # get the current cosmos document IDs of the chapter we are attempting to upload
    cosmos_ids_filename = release_date + '/' + str(chapterNumber) + '.pkl'
    cosmos_ids_container_client = abo.get_container_client(config.cosmos_ids_container_name)
    blob_client = cosmos_ids_container_client.get_blob_client(cosmos_ids_filename)
    try:
        existing_cosmos_ids_pickle_stream = blob_client.download_blob()
        cosmosIDs: list = pickle.loads(existing_cosmos_ids_pickle_stream.readall())
    except exceptions.ResourceNotFoundError:
        cosmosIDs: list = None

    # if required delete existing chapter uploads, to prevent duplicate entries in cosmos db
    try:
        ato.edit_chapter_record(chapterNumber, mutexKey, release_date, newRecordStatus=config.RecordStatus.deletingExistingCosmosDocs)
        for cosmosID in cosmosIDs:
            vectorstore.delete_document_by_id(cosmosID)
            logging.info("Deleted cosmos ID: " + str(cosmosID))
        ato.edit_chapter_record(chapterNumber, mutexKey, release_date, newRecordStatus=config.RecordStatus.deletingExistingCosmosIDTracker)
        blob_client.delete_blob()
    except TypeError as e:
        pass
        # this try catch block is redundant now as we don't allow any stage of a record to be overwritten now (instead we must delete that stage explicitly)
        # therefore disabled the below logging.error
        # logging.error("Retrieved existing cosmosIDs list is not an iterable object. Maybe this is the first time this chapter is been uploaded to cosmos. Chapter number: " + str(chapterNumber)+ 'Error: '+ str(e))

    
    # Add the new documents (line items) to the vector-store
    ato.edit_chapter_record(chapterNumber, mutexKey, release_date, newRecordStatus=config.RecordStatus.addingdNewDocsToCosmos)
    ct = datetime.datetime.now()
    logging.log(25,f"Adding chapter {str(chapterNumber)} of release {release_date} to vectorstore. Begin time: {str(ct)}")
    logging.log(25,"Total number of line items to be added: " + str(len(documents)))
    allIDs = []

    container = co.getCosmosContainer(release_date)
    futures = []

    

    def create_cosmos_item(final_dict_for_item):
        """Helper function for createVectorstoreUsingAzureCosmosNoSQL parent function.
        """
        container.create_item(body=final_dict_for_item)
        allIDs.append(final_dict_for_item['id'])

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for document in documents:
            text_fields:dict = document.fields_to_embed
            vector = document.vector
            metadata = document.metadata_fields

            vector_dict = {"embedding": vector}
            id = str(uuid.uuid4())
            final_dict_for_item = {"id": id}

            final_dict_for_item.update(text_fields); final_dict_for_item.update(metadata); final_dict_for_item.update(vector_dict)

            futures.append(executor.submit(create_cosmos_item, final_dict_for_item))

        concurrent.futures.wait(futures)

    # need to store the cosmos document IDs so we can delete them easily later when needed
    allIDs_bytes = pickle.dumps(allIDs)
    
    ato.edit_chapter_record(chapterNumber, mutexKey,release_date, newRecordStatus=config.RecordStatus.addingNewCosmosIdTracker)
    blob_client.upload_blob(allIDs_bytes, blob_type="BlockBlob")
    ato.edit_chapter_record(chapterNumber, mutexKey,release_date, newRecordStatus='', newRecordState=config.RecordState.excelUploaded)
    ato.release_mutex(chapterNumber, mutexKey, release_date)
    
    ct = datetime.datetime.now()
    logging.info("Chapter "+ str(chapterNumber) + f" of release {release_date}" +" |||Adding items to cosmos end: - " + str(ct))

def getLangchainVectorstore(release: str):
    """Simply returns a langchain reference object to our Cosmos DB

    Args:
        release (str): (each release has its own vectorstore)

    Returns:
        _type_: _description_
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
    container_name = release
    partition_key = PartitionKey(path="/id")
    cosmos_container_properties = {"partition_key": partition_key}
    cosmos_database_properties = {"id": database_name}

    

    #create blank vectorstore (or get an already created one)
    logging.info("Getting langchain vectorstore object.")
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
    logging.info("Langchain vector store returned.")
    return vectorstore

def deleteChapterFromCosmos(chapterNumber: int, release_date: str):
    vectorstore = getLangchainVectorstore(release_date)

    cosmos_ids_filename = release_date + '/' + str(chapterNumber) + '.pkl'
    cosmos_ids_container_client = abo.get_container_client(config.cosmos_ids_container_name)
    blob_client = cosmos_ids_container_client.get_blob_client(cosmos_ids_filename)
    try:
        existing_cosmos_ids_pickle_stream = blob_client.download_blob()
        cosmosIDs: list = pickle.loads(existing_cosmos_ids_pickle_stream.readall())
    except exceptions.ResourceNotFoundError:
        cosmosIDs: list = None
        logging.error("Cannot find a cosmos IDs pickle for the provided chapter: " + str(chapterNumber) + f" of release {release_date}")
        return

    # if required delete existing chapter uploads, to prevent duplicate entries in cosmos db
    try:
        for cosmosID in cosmosIDs:
            vectorstore.delete_document_by_id(cosmosID)
            logging.info("Deleted cosmos ID: " + str(cosmosID))
        blob_client.delete_blob()
    except TypeError as e:
        logging.error("Retrieved existing cosmosIDs list is not an iterable object. Maybe this is the first time this chapter is been uploaded to cosmos. Chapter number: " + str(chapterNumber)+ f'release" {release_date}'+ 'Error: '+ str(e))

