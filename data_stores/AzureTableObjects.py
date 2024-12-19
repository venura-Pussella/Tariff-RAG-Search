import os
import uuid
import config
import logging
from datetime import datetime
from azure.data.tables import TableServiceClient, TableEntity, UpdateMode, TableClient

class MutexError(Exception):
    """Custom exception for specific error handling."""
    def __init__(self, chapterNumber: int):
        self.chapterNumber = chapterNumber
        super().__init__(f"Chapter {self.chapterNumber} is under a mutex lock by another user.")


class AzureTableObjects:
    """Provides singleton method for managing table_service_client and table_clients.
    Also provides methods to perform CRUD on entities regarding chapter records.
    https://learn.microsoft.com/en-us/python/api/overview/azure/data-tables-readme?view=azure-python
    """

    __table_service_client = None
    __table_clients: dict[str,TableClient] = {}


    @classmethod
    def get_table_service_client(cls):
        if cls.__table_service_client == None:
            connection_string = os.getenv("AZURE_TABLE_CONNECTION_STRING")
            cls.__table_service_client = TableServiceClient.from_connection_string(connection_string)
            logging.info('table_service_client created')
        return cls.__table_service_client
    
    @classmethod
    def get_table_client(cls, table_name: str):
        if table_name not in cls.__table_clients.keys():
            table_service_client = cls.get_table_service_client()
            table_client = table_service_client.create_table_if_not_exists(table_name=table_name)
            logging.info(f'table_client {table_name} created')
            cls.__table_clients[table_name] = table_client
        return cls.__table_clients[table_name]  

    
    @classmethod
    def create_new_blank_chapter_record(cls, chapterNumber: int, release_date: str):
        rowkey = release_date + ':' + str(chapterNumber) # note the rowkey format
        entity = {
            'PartitionKey': config.azureStorageTablePartitionKeyValue,
            'RowKey': rowkey, # note rowkey cannot be an int, even tho other fields can be of any data type
            'RecordStatus': '',
            'RecordState': '',
            'MutexKey': '',
            'MutexLock': False
        }
        table_client = cls.get_table_client(config.azureStorage_chapterTracker_TableName)
        table_client.create_entity(entity)

    @classmethod
    def get_chapter_record(cls, chapterNumber: int, release_date: str) -> TableEntity:
        rowkey = release_date + ':' + str(chapterNumber)
        table_client = cls.get_table_client(config.azureStorage_chapterTracker_TableName)
        return table_client.get_entity(partition_key= config.azureStorageTablePartitionKeyValue, row_key= rowkey)
    
    @classmethod
    def claim_mutex(cls, chapterNumber: int, mutexKey: str, release_date: str):
        entity = cls.get_chapter_record(chapterNumber, release_date)
        if entity['MutexLock'] == False:
            entity['MutexLock'] = True
            entity['MutexKey'] = mutexKey
        elif entity['MutexLock'] == True and entity['MutexKey'] == mutexKey: pass
        else: raise MutexError(chapterNumber)

        table_client = cls.get_table_client(config.azureStorage_chapterTracker_TableName)
        table_client.update_entity(mode= UpdateMode.REPLACE, entity=entity)

    @classmethod
    def release_mutex(cls, chapterNumber: int, mutexKey: str, release_date: str):
        entity = cls.get_chapter_record(chapterNumber, release_date)
        if entity['MutexKey'] == mutexKey:
            entity['MutexLock'] = False
            entity['MutexKey'] = ''
        else: raise MutexError(chapterNumber)

        table_client = cls.get_table_client(config.azureStorage_chapterTracker_TableName)
        table_client.update_entity(mode= UpdateMode.REPLACE, entity=entity)

    @classmethod
    def edit_chapter_record(cls, chapterNumber: int, mutexKey: str, release_date: str, newRecordStatus: str = None, newRecordState = None):
        entity = cls.get_chapter_record(chapterNumber, release_date)
        if entity['MutexKey'] != mutexKey: raise MutexError(chapterNumber)

        if newRecordStatus != None:
            entity['RecordStatus'] = newRecordStatus
        if newRecordState != None:
            entity['RecordState'] = newRecordState

        table_client = cls.get_table_client(config.azureStorage_chapterTracker_TableName)
        table_client.update_entity(mode= UpdateMode.REPLACE, entity=entity)

    @classmethod
    def delete_chapter_record(cls, chapterNumber: int, mutexKey: str, release_date: str):
        entity = cls.get_chapter_record(chapterNumber, release_date)
        if entity['MutexKey'] != mutexKey: raise MutexError(chapterNumber)

        table_client = cls.get_table_client(config.azureStorage_chapterTracker_TableName)
        table_client.delete_entity(partition_key=config.azureStorageTablePartitionKeyValue, row_key=f"{release_date}:{str(chapterNumber)}")

    @classmethod
    def get_all_chapter_records(cls) -> list[TableEntity]:
        table_client = cls.get_table_client(config.azureStorage_chapterTracker_TableName)
        return list(table_client.list_entities())
    
    @classmethod
    def search_chapter_records(cls, field: str, content: str, release_date: str) -> list[int]:
        """Searches all chapters for a given release that match your filter for a specified field.
        Returns the list of chapter numbers that match the filter.

        Args:
            field (str): field to search in
            content (str): Search filter
            release_date (str): Release

        Returns:
            list[int]: chapter numbers
        """
        entities = cls.get_all_chapter_records()
        chapters: list[int] = []
        for entity in entities:
            rowkey = entity['RowKey']
            entity_release_date = rowkey.rsplit(':')[0]
            if entity_release_date==release_date and entity[field] == content: chapters.append(int(rowkey.rsplit(':')[1]))
        return chapters
    
    @classmethod
    def create_new_job(cls, function_name: str, job_description: str) -> str:
        """Creates new job in the job tracker.

        Args:
            function_name (str): Name of the function that does the job
            job_description (str): Add description of job goals

        Returns:
            str: unique id to identify the job in the tracker
        """
        rowkey = str(uuid.uuid4())
        entity = {
            'PartitionKey': config.azureStorageTablePartitionKeyValue,
            'RowKey': rowkey, # note rowkey cannot be an int, even tho other fields can be of any data type
            'StartTime': str(datetime.now()),
            'Function': function_name,
            'Description': job_description,
            'EndTime': '',
            'Progress': ''
        }
        table_client = cls.get_table_client(config.job_tracker_tableName)
        table_client.create_entity(entity)
        return rowkey
    
    @classmethod
    def get_job_progress(cls, job_id: str) -> str:
        table_client = cls.get_table_client(config.job_tracker_tableName)
        entity = table_client.get_entity(config.azureStorageTablePartitionKeyValue, job_id)
        return entity['Progress']
    
    @classmethod
    def set_job_progress(cls, job_id: str, progress: str) -> str:
        table_client = cls.get_table_client(config.job_tracker_tableName)
        entity = table_client.get_entity(config.azureStorageTablePartitionKeyValue, job_id)
        entity['Progress'] = progress
        table_client.update_entity(mode= UpdateMode.REPLACE, entity=entity)

    @classmethod
    def end_job(cls, job_id: str):
        table_client = cls.get_table_client(config.job_tracker_tableName)
        entity = table_client.get_entity(config.azureStorageTablePartitionKeyValue, job_id)
        entity['EndTime'] = str(datetime.now())
        table_client.update_entity(mode= UpdateMode.REPLACE, entity=entity)
        log_message = ''
        for key in entity.keys():
            log_message += f'{key}: {entity[key]}\n'
        logging.log(14,f'{log_message}')

        # if too many jobs in the azure table, trigger a cleanup
        if len(cls.get_all_jobs()) > config.total_jobs_threshold:
            cls.delete_old_completed_jobs()

    @classmethod
    def get_all_jobs(cls) -> list[TableEntity]:
        table_client = cls.get_table_client(config.job_tracker_tableName)
        return list(table_client.list_entities())
    
    @classmethod
    def get_all_jobs_classified(cls) -> tuple[list[TableEntity],list[TableEntity]]:
        """Gets all jobs classified into active and completed job categories (sorted)

        Returns:
            tuple[list[TableEntity],list[TableEntity]]: active_jobs_sorted - most recent started job first,completed_jobs_sorted - most recent ended job first
        """
        jobs = cls.get_all_jobs()
        active_jobs = []
        completed_jobs = []

        for job in jobs:
            if job['EndTime'] == '': active_jobs.append(job)
            else: completed_jobs.append(job)

        active_jobs_sorted = sorted(active_jobs, key=lambda x: x["StartTime"], reverse=True)
        completed_jobs_sorted = sorted(completed_jobs, key=lambda x: x["EndTime"], reverse=True)
        return active_jobs_sorted,completed_jobs_sorted
    
    @classmethod
    def delete_old_completed_jobs(cls):
        """Deleted old completed jobs according to the parameters specified in the config file."""
        _,completed_jobs_sorted = cls.get_all_jobs_classified()
        count = len(completed_jobs_sorted)
        start_deleting_index = int(count*(1 - config.ratio_of_completed_jobs_to_delete_when_threshold_is_hit))
        jobs_to_delete = completed_jobs_sorted[start_deleting_index:]
        table_client = cls.get_table_client(config.job_tracker_tableName)
        for job in jobs_to_delete:
            table_client.delete_entity(config.azureStorageTablePartitionKeyValue,job['RowKey'])


