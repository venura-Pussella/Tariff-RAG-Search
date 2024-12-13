import os
import config
import logging
from azure.data.tables import TableServiceClient, TableEntity, UpdateMode

class MutexError(Exception):
    """Custom exception for specific error handling."""
    def __init__(self, chapterNumber: int):
        self.chapterNumber = chapterNumber
        super().__init__(f"Chapter {self.chapterNumber} is under a mutex lock by another user.")


class AzureTableObjects:
    """Provides singleton method for retrieving table client (and table-service-client also but why would you want this?).
    Also provides methods to perform CRUD on entities (i.e. a table row (record)), and to claim and release mutex on a row (record).
    https://learn.microsoft.com/en-us/python/api/overview/azure/data-tables-readme?view=azure-python

    The Azure table is used to track the RecordState and Status of a record (a record is a chapter_number-release_date combo).
    It is also used to manage mutex rights.
    """

    __table_service_client = None
    __table_client = None


    @classmethod
    def get_table_service_client(cls):
        if cls.__table_service_client == None:
            connection_string = os.getenv("AZURE_TABLE_CONNECTION_STRING")
            cls.__table_service_client = TableServiceClient.from_connection_string(connection_string)
            logging.info('table_service_client created')
        return cls.__table_service_client
    
    @classmethod
    def get_table_client(cls):
        if cls.__table_client == None:
            table_service_client = cls.get_table_service_client()
            cls.__table_client = table_service_client.create_table_if_not_exists(table_name=config.azureStorageTableName)
            logging.info('table_client created')
        return cls.__table_client
    

    
    @classmethod
    def create_new_blank_entity(cls, chapterNumber: int, release_date: str):
        rowkey = release_date + ':' + str(chapterNumber)
        entity = {
            'PartitionKey': config.azureStorageTablePartitionKeyValue,
            'RowKey': rowkey, # note rowkey cannot be an int, even tho other fields can be of any data type
            'RecordStatus': '',
            'RecordState': '',
            'MutexKey': '',
            'MutexLock': False
        }
        table_client = cls.get_table_client()
        table_client.create_entity(entity)

    @classmethod
    def get_entity(cls, chapterNumber: int, release_date: str) -> TableEntity:
        rowkey = release_date + ':' + str(chapterNumber)
        table_client = cls.get_table_client()
        return table_client.get_entity(partition_key= config.azureStorageTablePartitionKeyValue, row_key= rowkey)
    
    @classmethod
    def claim_mutex(cls, chapterNumber: int, mutexKey: str, release_date: str):
        entity = cls.get_entity(chapterNumber, release_date)
        if entity['MutexLock'] == False:
            entity['MutexLock'] = True
            entity['MutexKey'] = mutexKey
        elif entity['MutexLock'] == True and entity['MutexKey'] == mutexKey: pass
        else: raise MutexError(chapterNumber)

        table_client = cls.get_table_client()
        table_client.update_entity(mode= UpdateMode.REPLACE, entity=entity)

    @classmethod
    def release_mutex(cls, chapterNumber: int, mutexKey: str, release_date: str):
        entity = cls.get_entity(chapterNumber, release_date)
        if entity['MutexKey'] == mutexKey:
            entity['MutexLock'] = False
            entity['MutexKey'] = ''
        else: raise MutexError(chapterNumber)

        table_client = cls.get_table_client()
        table_client.update_entity(mode= UpdateMode.REPLACE, entity=entity)

    @classmethod
    def edit_entity(cls, chapterNumber: int, mutexKey: str, release_date: str, newRecordStatus: str = None, newRecordState = None):
        entity = cls.get_entity(chapterNumber, release_date)
        if entity['MutexKey'] != mutexKey: raise MutexError(chapterNumber)

        if newRecordStatus != None:
            entity['RecordStatus'] = newRecordStatus
        if newRecordState != None:
            entity['RecordState'] = newRecordState

        table_client = cls.get_table_client()
        table_client.update_entity(mode= UpdateMode.REPLACE, entity=entity)

    @classmethod
    def delete_entity(cls, chapterNumber: int, mutexKey: str, release_date: str):
        entity = cls.get_entity(chapterNumber, release_date)
        if entity['MutexKey'] != mutexKey: raise MutexError(chapterNumber)

        table_client = cls.get_table_client()
        table_client.delete_entity(partition_key=config.azureStorageTablePartitionKeyValue, row_key=f"{release_date}:{str(chapterNumber)}")

    @classmethod
    def get_all_entities(cls) -> list[TableEntity]:
        table_client = cls.get_table_client()
        return list(table_client.list_entities())
    
    @classmethod
    def search_entities(cls, field: str, content: str, release_date: str) -> list[int]:
        """Searches all chapters for a given release that match your filter for a specified field.
        Returns the list of chapter numbers that match the filter.

        Args:
            field (str): field to search in
            content (str): Search filter
            release_date (str): Release

        Returns:
            list[int]: chapter numbers
        """
        entities = cls.get_all_entities()
        chapters: list[int] = []
        for entity in entities:
            rowkey = entity['RowKey']
            entity_release_date = rowkey.rsplit(':')[0]
            if entity_release_date==release_date and entity[field] == content: chapters.append(int(rowkey.rsplit(':')[1]))
        return chapters
