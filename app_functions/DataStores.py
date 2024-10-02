import config
import csv
import app_functions.findByHSCode as fhsc
from langchain_community.vectorstores.azure_cosmos_db_no_sql import AzureCosmosDBNoSqlVectorSearch
from initializers.getEmbeddings import getEmbeddings
from langchain_core.documents import Document
from initializers.CosmosObjects import CosmosObjects

class DataStores:

    __vectorstore = None
    __hsCodeToSCCodeMapping: dict[str,str] = None

    @staticmethod
    def vectorStoreSearch(question, data_dict):
        """Searches the dictionary containing all tariff pdf information for line items by comparing vectorstore embeddings against 
        the embedding of the user query, and returns a list of line items.
        Args:
            question: question/text to embed and compare with the vectorstore
            data_dict: dictionary containing all tariff pdf information
            vectostore: vectorstore reference to be used
            ids_hscodes_dict: contains azure comsos db IDs to HScodes mapping, needed in case azure cosmos db is used (as a workaround due to 
                the langchain similarity search to azure cosmos not returning hs code metadata)
        Returns:
            List of line items
        """
        # ct = datetime.datetime.now()
        # print("|||VectorStoreSearch Called - " + str(ct))


        print("Vector store search called")
        vectorstore = DataStores.getVectorStore()
        results = []

        embeddings = getEmbeddings.getEmbeddings()
        embeddedQuestion = embeddings.embed_query(question)

        resultingHSCodesAndScores = DataStores.__similarity_search_with_score(vectorstore, embeddedQuestion, k=30)


        search_results = []
        scores = []
        for resultingHSCodeAndScore in resultingHSCodesAndScores:
            search_results.append(resultingHSCodeAndScore[0])
            scores.append(resultingHSCodeAndScore[1])

        results = DataStores.__convertSearchResults(search_results, data_dict)

        return (results, scores)

    @staticmethod
    def __convertSearchResults(hscodes, data_dict) -> list[dict]:
        """ Returns a list of line items that correspond to the search results obtained from a vectorstore
        Args:
            search_results: langchain documents returned by a vectorstore
            data_dict: the dictionary containing the .jsons representing tariff pdfs and their line items
            ids_hscodes_dict: dictionary containing mapping of azure cosmos DB ids to HS codes (required in case search results
                are from azure cosmos db, as it does not return our custom metadata (inlcuding hs code) due to a bug/limitation in
                the langchain similarity search function (as seen in its source code))
        Returns:
            List of line items
        """
        results = []
        for hscode in hscodes:
            item = fhsc.findByHSCode(hscode, data_dict)
            try: results.append(item[0]) # came across one case where a line item had been created without an hs code because there was a row without a line item but with a unit
            except Exception as e: print(e); continue

        return results
        
    @classmethod
    def getVectorStore(cls):

        if DataStores.__vectorstore == None:
            if config.vectorstore == "azure_cosmos_nosql":
                DataStores.__vectorstore = DataStores.__getAzureCosmosVectorstore()
            elif config.vectorstore == "chroma":
                print("Code for getting chroma vectorstore not yet implemented")
            else:
                print("Valid vectorstore not configured in config.py")

        return DataStores.__vectorstore

    def __getAzureCosmosVectorstore():
        """Connects to and tries to return Azure Cosmos vectorstore object.
        Returns:
            vectorstore: OPTIONAL (AzureCosmosDBNoSqlVectorSearch)
        """
        try:
            print("Creating Azure Cosmos NoSQL vectorstore reference...")

            from azure.cosmos import PartitionKey
            from langchain_community.vectorstores.azure_cosmos_db_no_sql import (
                AzureCosmosDBNoSqlVectorSearch,
            )

            cosmos_client = CosmosObjects.getCosmosClient()
            database_name = config.cosmosNoSQLDBName
            container_name = config.cosmosNoSQLContainerName
            partition_key = PartitionKey(path="/id")
            cosmos_container_properties = {"partition_key": partition_key}
            cosmos_database_properties = {"id": database_name}

            from initializers import getEmbeddings as emb
            embedding = emb.getEmbeddings.getEmbeddings()

            vectorstore = AzureCosmosDBNoSqlVectorSearch(
                cosmos_client=cosmos_client,
                embedding=embedding,
                database_name=database_name,
                container_name=container_name,
                vector_embedding_policy=CosmosObjects.vector_embedding_policy,
                indexing_policy=CosmosObjects.indexing_policy,
                cosmos_container_properties=cosmos_container_properties,
                cosmos_database_properties=cosmos_database_properties
            )

            return vectorstore
        except Exception as e: 
            print("Exception @ getAzureCosmosVectorstore() ")
            print(e)
            return None

    def __similarity_search_with_score(
            vectorstore: AzureCosmosDBNoSqlVectorSearch,
            embeddings: list[float],
            k: int = 4,
            pre_filter: (dict | None) = None,
            with_embedding: bool = False,
        ) -> list[tuple[Document, float]]:
            # query = "SELECT TOP " + str(k) + ' c["HS Code"], VectorDistance(c.embedding, '
            query = "SELECT " + ' c["HS Code"], VectorDistance(c.embedding, '
            query += str(embeddings) + ") "
            query += "AS similarityScore FROM c "

            # query += "ORDER BY VectorDistance(c.embedding, " + str(embeddings) + ")"

            hscodesAndScores = []

            items = list(
                vectorstore._container.query_items(
                    query=query, enable_cross_partition_query=True
                )
            )
            for item in items:
                hscode = item["HS Code"]
                score = item["similarityScore"]
                hscodesAndScores.append((hscode,score))

            sorted_hscodesAndScores = sorted(hscodesAndScores, key=lambda x: x[1], reverse=True) # ~10 milliseconds to sort 1913 results
            return sorted_hscodesAndScores[:k]
    
    @classmethod
    def getHSCodeToSCCodeMapping(cls) -> dict[str,str]:
        """Retrieves singleton HSCode to SCCode mapping. Initialized using the filepath defined inside the function.
        Returns:
            dictionary with key as HSCode and value as SCCode
        """

        if DataStores.__hsCodeToSCCodeMapping == None:

            # Read from csv file containing HS Code to SC Code mapping. HS Code is unique.
            csv_file = 'initializers/extract_data/HSCode_to_SCCode_Mapping Sorted.csv'
            rows = []

            with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
                csv_reader = csv.reader(file)

                for row in csv_reader:
                    rows.append(row)

            # HS Code format: ####.##.##N

            DataStores.__hsCodeToSCCodeMapping = {}

            for n in range(1,len(rows)):
                row = rows[n]
                key = row[0]
                value = row[1]
                DataStores.__hsCodeToSCCodeMapping[key] = value
            
            if not bool(DataStores.__hsCodeToSCCodeMapping): print("WARNING: HS Code to SC Code dictionary is empty!")

        return DataStores.__hsCodeToSCCodeMapping
