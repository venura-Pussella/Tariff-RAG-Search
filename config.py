vectorstore = "azure_cosmos_nosql"  # "chroma" or "azure_cosmos_nosql"
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
        {"path": '/"_etag"/?'}, {"path": "/embedding/*"}
    ],
    "vectorIndexes": [{"path": "/embedding", "type": "diskANN"}],
}
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

pdf_container_name = "pdf-container"
generatedExcel_container_name = "generatedexcel-container"
generatedDict_container_name = "generatedict-container"
reviewedExcel_container_name = "reviewedexcel-container"
json_container_name = "json-container"
