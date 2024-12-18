vectorstore = "azure_cosmos_nosql"  # "chroma" or "azure_cosmos_nosql" # chromaDB only partial implementation, not properly wired up
cosmosNoSQLDBName = "tariff-search-db"
embeddings = "AzureOpenAI" # 'OpenAI' or 'AzureOpenAI'
lifetimeTokenLimit = 10000000
lifetimeTokenLimit_chatbot = 10000000
modelForChatBot = "gpt-4o-mini"
embeddingModel = "text-embedding-ada-002"
indexing_policy = {
    "indexingMode": "consistent",
    "includedPaths": [{"path": "/*"}],
    "excludedPaths": [
        {"path": '/"_etag"/?'}, {"path": "/embedding/*"} # vector path is added to excludedPaths for improved insertion performance and less insertion RU cost: https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search
    ],
    "vectorIndexes": [{"path": "/embedding", "type": "diskANN"}],
}
vector_embedding_policy = {
    "vectorEmbeddings": [
        {
            "path": "/embedding",
            "dataType": "float32",
            "distanceFunction": "dotproduct",
            "dimensions": 1536, # since the ada-002 embedding model returns vectors of 1536 dimensions
        }
    ]
}

# Azure Blob container names
pdf_container_name = "pdf-container"
generatedExcel_container_name = "generatedexcel-container"
generatedDict_container_name = "generatedict-container"
reviewedExcel_container_name = "reviewedexcel-container"
json_container_name = "json-container"
cosmos_ids_container_name = "cosmos-ids-container"
release_holder_container_name = "release-holder"
release_holder_filename = "releases.txt"

# Azure Storage Table
azureStorage_chapterTracker_TableName = 'chaptertracker12345'
azureStorageTablePartitionKeyValue = 'a'

class RecordStatus:
    uploadingPDF = 'uploading PDF'
    uploadingGeneratedDocuments = 'uploading documents generated from PDF'
    uploadingCorrectedExcel = 'uploading reviewed/corrected excel'
    uploadingJson = 'uploading generated json file'
    beginDeleteExcel = 'deleting Cosmos and Json and Corrected Excel'
    beginDeletePDF = 'deleting all docs upto pdf'
    beginDeleteEntity = 'deleting the azure table entry'
    addingdNewDocsToCosmos = 'adding the new line items to cosmos'
    addingNewCosmosIdTracker = 'uploading cosmos ID tracker'
    deletingExistingCosmosDocs = 'deleting existing line items from cosmos'
    deletingExistingCosmosIDTracker = 'deleting existing cosmos id tracker'

class RecordState:
    pdfUploaded = 'pdfUploaded'
    excelUploaded = 'excelUploaded'

flask_max_accepted_file_size = 100 * 1024 * 1024
in_memory_log_message_count = 100000
