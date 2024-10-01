import config

class getEmbeddings():
    """Singleton class with func to return embeddings according to what's defined in config.py
    ...
    Methods
    ------
        getEmbeddings(): returns embeddings
    """

    embeddings = None

    def getEmbeddings():
        """Returns embedding according to config.py
        Raises:
            ValueError: If Embedding to be used not defined in config.py, or is not known
        """

        if getEmbeddings.embeddings != None:
            return getEmbeddings.embeddings
        

        if config.embeddings == 'OpenAI':
            from langchain_community.embeddings import OpenAIEmbeddings
            embedding = OpenAIEmbeddings()
        elif config.embeddings == "AzureOpenAI":
            from langchain_openai import AzureOpenAIEmbeddings
            embedding = AzureOpenAIEmbeddings()
        else:
            raise ValueError("Embedding to be used not defined in config.py, or is not known")
        
        return embedding