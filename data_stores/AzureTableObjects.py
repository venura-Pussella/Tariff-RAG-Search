import os
import config
from azure.data.tables import TableServiceClient, TableEntity, UpdateMode

class AzureTableObjects:

    __table_service_client = None
    __table_client = None


    @classmethod
    def get_table_service_client(cls):
        if cls.__table_service_client == None:
            connection_string = os.getenv("AZURE_TABLE_CONNECTION_STRING")
            cls.__table_service_client = TableServiceClient.from_connection_string(connection_string)
        return cls.__table_service_client
    
    @classmethod
    def get_table_client(cls):
        if cls.__table_client == None:
            table_service_client = cls.get_table_service_client()
            cls.__table_client = table_service_client.create_table_if_not_exists(table_name=config.azureStorageTableName)
        return cls.__table_client
    
    
    
    @classmethod
    def create_new_blank_entity(cls, chapterNumber: int):
        entity = {
            'PartitionKey': config.azureStorageTablePartitionKeyValue,
            'RowKey': chapterNumber,
            'Status': '',
            'Operation': 'None'
        }
        table_client = cls.get_table_client()
        table_client.create_entity(entity)

    @classmethod
    def get_entity(cls, chapterNumber: int) -> TableEntity:
        table_client = cls.get_table_client()
        return table_client.get_entity(partition_key= config.azureStorageTablePartitionKeyValue, row_key= chapterNumber)
    
    @classmethod
    def edit_entity(cls, chapterNumber: int, newStatus: str = None, newOperation = None):
        if newStatus == None and newOperation == None: return # nothing to update

        entity = cls.get_entity(chapterNumber)
        if newStatus != None:
            entity['Status'] = newStatus
        if newOperation != None:
            entity['Operation'] = newOperation
        table_client = cls.get_table_client()
        table_client.update_entity(mode= UpdateMode.REPLACE, entity=entity)

    @classmethod
    def delete_entity(cls, chapterNumber: int):
        table_client = cls.get_table_client()
        table_client.delete_entity(partition_key=config.azureStorageTablePartitionKeyValue, row_key=chapterNumber)
