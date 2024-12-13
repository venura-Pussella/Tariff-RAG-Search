import os
import config
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # read local .env file
from azure.data.tables import TableServiceClient


connection_string = os.getenv("AZURE_TABLE_CONNECTION_STRING")

table_service_client = TableServiceClient.from_connection_string(connection_string)
table_client = table_service_client.create_table_if_not_exists(config.azureStorageTableName)

my_filter = f"PartitionKey eq '{config.azureStorageTablePartitionKeyValue}'"
entities = table_client.query_entities(my_filter)
for entity in entities:
    for key in entity.keys():
        print(f"{key}: {entity[key]}")
    print()

# entity = table_client.delete_entity(config.azureStorageTablePartitionKeyValue,'2024-11-18:28')
# entity = table_client.delete_entity(config.azureStorageTablePartitionKeyValue,'2024-11-18:31')