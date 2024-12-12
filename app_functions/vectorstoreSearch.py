import logging

from other_funcs.getEmbeddings import getEmbeddings
from app_functions import findByHSCode as fhsc
from data_stores.CosmosObjects import CosmosObjects

def vectorStoreSearch(question: str, releases: list[str]) -> list[dict]:
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


    logging.info("Vector store search called")

    embeddings = getEmbeddings.getEmbeddings()
    embeddedQuestion = embeddings.embed_query(question)

    search_results = []
    for release in releases:

        resultingHSCodesAndScores = similarity_search_with_score(embeddedQuestion, release, k=10)

        for resultingHSCodeAndScore in resultingHSCodesAndScores:
            hscode = resultingHSCodeAndScore[0]
            score = resultingHSCodeAndScore[1]
            results = fhsc.findByHSCode(hscode)
            for result in results:
                if result['Release'] == release:
                    search_results.append((result, score))
    print('SEARCH RESULTS')
    print(search_results) 
    sorted_search_results = sorted(search_results, key=lambda x: x[1], reverse=True)  
    return sorted_search_results
 

def similarity_search_with_score(queryEmbeddings: list[float], release: str, k: int = 4) -> list[tuple[str, float]]:
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
        CosmosObjects.getCosmosContainer(release).query_items(query=query, enable_cross_partition_query=True)
    )
    for item in items:
        hscode = item["HS Code"]
        score = item["similarityScore"]
        hscodesAndScores.append((hscode,score))

    # sorted_hscodesAndScores = sorted(hscodesAndScores, key=lambda x: x[1], reverse=True) # ~10 milliseconds to sort 1913 results
    return hscodesAndScores