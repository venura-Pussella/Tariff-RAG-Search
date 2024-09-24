def vectorStoreSearch(question):

    print("vector store search called")

    import os

    import openai

    from dotenv import load_dotenv, find_dotenv
    _ = load_dotenv(find_dotenv()) # read local .env file
    openai.api_key = os.environ['OPENAI_API_KEY']

    from app_functions.findByHSCode import findByHSCode


    from langchain_community.vectorstores import Chroma
    persist_directory = 'initializers\create_vectorstores\\vectorstores\chroma'

    from langchain_community.embeddings import OpenAIEmbeddings
    embedding = OpenAIEmbeddings()

    vectordb = Chroma(
        embedding_function=embedding,
        persist_directory=persist_directory
    )
    print("vector db collection count:")
    print(vectordb._collection.count())

    search_results = vectordb.max_marginal_relevance_search(question,k=20,lambda_mult=0.25)

    results = []
    for search_result in search_results:
        hscode = search_result.metadata["HS Code"]
        item = findByHSCode.findByHSCode(hscode)
        results.append(item[0])

    return results