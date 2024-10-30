vectorstore = "azure_cosmos_nosql"  # "chroma" or "azure_cosmos_nosql" # chromaDB only partial implementation, not properly wired up
cosmosNoSQLDBName = "tariff-search-db"
cosmosNoSQLContainerName = "tariff-search-container"
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
            "distanceFunction": "cosine",
            "dimensions": 1536, # since the ada-002 embedding model returns vectors of 1536 dimensions
        }
    ]
}

pdf_container_name = "pdf-container"
generatedExcel_container_name = "generatedexcel-container"
generatedDict_container_name = "generatedict-container"
reviewedExcel_container_name = "reviewedexcel-container"
json_container_name = "json-container"
cosmos_ids_container_name = "cosmos-ids-container"

temp_folderpath_for_pdf_and_excel_uploads = 'files/pdfExcelUploads/'
temp_folderpath_for_pdf_and_json_downloads = 'files/pdfJsonDownloads/'
temp_folderpath_for_genExcel_downloads = 'files/genExcelDownloads/'
temp_folderpath_for_reviewedExcel_downloads = 'files/reviewedExcelDownloads/'
temp_folderpath_for_data_to_review = 'files/review_data/'
temp_folderpath_for_reviewed_data = 'files/reviewed_data/'

azureStorageTableName = 'chaptertracker12345'
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