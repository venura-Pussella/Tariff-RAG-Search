import config
import os
import logging

class getEmbeddings():
    """Singleton class with func to return embeddings according to what's defined in config.py
    ### Methods
    ------
        getEmbeddings(): returns embeddings
    """

    __embeddings = None

    def getEmbeddings():
        """Returns embedding according to config.py
        ### Raises:
            ValueError: If Embedding to be used not defined in config.py, or is not known
        """

        if getEmbeddings.__embeddings == None:
            if config.embeddings == 'OpenAI':
                from langchain_community.embeddings import OpenAIEmbeddings
                getEmbeddings.__embeddings = OpenAIEmbeddings()
            elif config.embeddings == "AzureOpenAI":
                from langchain_openai import AzureOpenAIEmbeddings
                AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS = os.getenv('AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS')
                getEmbeddings.__embeddings = AzureOpenAIEmbeddings(azure_endpoint=AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS)
            else:
                raise ValueError("Embedding to be used not defined in config.py, or is not known")
        logging.info('Got the embeddings client')
        
        return getEmbeddings.__embeddings