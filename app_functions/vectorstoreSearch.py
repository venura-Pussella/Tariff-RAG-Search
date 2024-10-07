from other_funcs.getEmbeddings import getEmbeddings
from app_functions import findByHSCode as fhsc
from data_stores.CosmosObjects import CosmosObjects

def vectorStoreSearch(question):
    """Searches the dictionary containing all tariff pdf information for line items by comparing vectorstore embeddings against 
    the embedding of the user query, and returns a list of line items.
    ### Args:
        question: question/text to embed and compare with the vectorstore
        data_dict: dictionary containing all tariff pdf information
        vectostore: vectorstore reference to be used
        ids_hscodes_dict: contains azure comsos db IDs to HScodes mapping, needed in case azure cosmos db is used (as a workaround due to 
        the langchain similarity search to azure cosmos not returning hs code metadata)
    ### Returns:
        List of line items
    """
    # ct = datetime.datetime.now()
    # print("|||VectorStoreSearch Called - " + str(ct))


    print("Vector store search called")
    results = []

    embeddings = getEmbeddings.getEmbeddings()
    embeddedQuestion = embeddings.embed_query(question)

    resultingHSCodesAndScores = similarity_search_with_score(embeddedQuestion, k=30)


    search_results = []
    for resultingHSCodeAndScore in resultingHSCodesAndScores:
        hscode = resultingHSCodeAndScore[0]
        score = resultingHSCodeAndScore[1]
        item = convertHSCodeToItem(hscode)
        search_results.append((item, score))

    return search_results


def convertHSCodeToItem(hscode) -> dict:
    """ Returns a list of line items that correspond to the search results obtained from a vectorstore
    ### Args:
        search_results: langchain documents returned by a vectorstore
        data_dict: the dictionary containing the .jsons representing tariff pdfs and their line items
        ids_hscodes_dict: dictionary containing mapping of azure cosmos DB ids to HS codes (required in case search results
            are from azure cosmos db, as it does not return our custom metadata (inlcuding hs code) due to a bug/limitation in
            the langchain similarity search function (as seen in its source code))
    ### Returns:
        List of line items
    """
    item = {}
    resultList = fhsc.findByHSCode(hscode)
    try: item = resultList[0] # came across one case where a line item had been created without an hs code because there was a row without a line item but with a unit
    except Exception as e: print(e)

    return item
    

def similarity_search_with_score(queryEmbeddings: list[float], k: int = 4) -> list[tuple[str, float]]:
    """Performs a similarity search vectorsearch against Cosmos.
    ### Args:
        queryEmbeddings: The embeddings of the query (vector)
        k: Top how much to return
    ### Returns:
        A list of (HS Codes, Similarity Score)
    """

    query = "SELECT " + ' c["HS Code"], VectorDistance(c.embedding, '
    query += str(queryEmbeddings) + ") "
    query += "AS similarityScore FROM c "

    # query += "ORDER BY VectorDistance(c.embedding, " + str(queryEmbeddings) + ")"
    # Using ORDER BY massively increases RUs used, and Microsoft documentation mentions something about ORDER BY triggering a brute force approach.

    hscodesAndScores = []

    items = list(
        CosmosObjects.getCosmosContainer().query_items(query=query, enable_cross_partition_query=True)
    )
    for item in items:
        hscode = item["HS Code"]
        score = item["similarityScore"]
        hscodesAndScores.append((hscode,score))

    sorted_hscodesAndScores = sorted(hscodesAndScores, key=lambda x: x[1], reverse=True) # ~10 milliseconds to sort 1913 results
    return sorted_hscodesAndScores[:k]
  