import shutil
from other_funcs import getEmbeddings as emb
from langchain.vectorstores import Chroma

def createVectorstoreUsingChroma(docs: list):
    """Creates & persists a chroma vectorstore using the passed in list of langchain documents
    Args:
        docs: list of langchain documents
    Returns:
        Void
    Issues:
        Need to add code to consider rate limit of embeddings.
    """    

    embedding = emb.getEmbeddings.getEmbeddings()
  
    persist_directory = "files/persisted_vectorstores/chroma"
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