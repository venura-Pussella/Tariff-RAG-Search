def createVectorstoreUsingChroma(docs: list):
    import os
    import openai
    import shutil

    from dotenv import load_dotenv, find_dotenv
    _ = load_dotenv(find_dotenv()) # read local .env file
    openai.api_key = os.environ['OPENAI_API_KEY']

    from langchain.embeddings.openai import OpenAIEmbeddings
    embedding = OpenAIEmbeddings()


    from langchain.vectorstores import Chroma

    persist_directory = "initializers\create_vectorstores\\vectorstores\chroma"
    print("Deleting existing vectorstore...")
    shutil.rmtree(persist_directory)

    print("Creating vectorstore...")
    vectordb = Chroma.from_documents(
        documents=docs,
        embedding=embedding,
        persist_directory=persist_directory
    )
    vectordbCollectionCount = vectordb._collection.count()
    print("Vector store created with collection count: " + str(vectordbCollectionCount))