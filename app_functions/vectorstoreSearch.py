from other_funcs.getEmbeddings import getEmbeddings
from app_functions import findByHSCode as fhsc
from data_stores.CosmosObjects import CosmosObjects

def vectorStoreSearch(question: str) -> list[dict]:
    """Searches text fields of a line-item for matches with the user's query.
    Works by embedding the user's question and getting a vector, and comparing it with the vectors in Cosmos DB (vector similarity search).
    The top k results from Cosmos have HS code as a metadata, so now we use this to carry out a regular HS code search.

    Args:
        question (str): user's question

    Returns:
        list[dict]: list of search results (line items)
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

def convertHSCodeToItem(hscode: str) -> dict:
    """Gets the json line item that corresponds to the HS code.
    """
    item = {}
    resultList = fhsc.findByHSCode(hscode)
    try: item = resultList[0] # came across one case where a line item had been created without an hs code because there was a row without a line item but with a unit
    except Exception as e: print(e)

    return item   

def similarity_search_with_score(queryEmbeddings: list[float], k: int = 4) -> list[tuple[str, float]]:
    """Performs a similarity search vectorsearch against Cosmos.

    Args:
        queryEmbeddings (list[float]): The embeddings of the user query (vector)
        k (int, optional): Top how much to return. Defaults to 4.

    Returns:
        list[tuple[str, float]]: A list of (HS Codes, Similarity Score)
    """
    query = "SELECT TOP " + str(k)
    query += ' c["HS Code"], VectorDistance(c.embedding, '
    query += str(queryEmbeddings) + ") "
    query += "AS similarityScore FROM c "

    query += "ORDER BY VectorDistance(c.embedding, " + str(queryEmbeddings) + ")"

    hscodesAndScores = []

    items = list(
        CosmosObjects.getCosmosContainer().query_items(query=query, enable_cross_partition_query=True)
    )
    for item in items:
        hscode = item["HS Code"]
        score = item["similarityScore"]
        hscodesAndScores.append((hscode,score))

    # sorted_hscodesAndScores = sorted(hscodesAndScores, key=lambda x: x[1], reverse=True) # ~10 milliseconds to sort 1913 results
    return hscodesAndScores