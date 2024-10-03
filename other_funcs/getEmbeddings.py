import config

class getEmbeddings():
    """Singleton class with func to return embeddings according to what's defined in config.py
    ...
    Methods
    ------
        getEmbeddings(): returns embeddings
    """

    __embeddings = None

    def getEmbeddings():
        """Returns embedding according to config.py
        Raises:
            ValueError: If Embedding to be used not defined in config.py, or is not known
        """

        if getEmbeddings.__embeddings == None:
            if config.embeddings == 'OpenAI':
                from langchain_community.embeddings import OpenAIEmbeddings
                getEmbeddings.__embeddings = OpenAIEmbeddings()
            elif config.embeddings == "AzureOpenAI":
                from langchain_openai import AzureOpenAIEmbeddings
                getEmbeddings.__embeddings = AzureOpenAIEmbeddings()
            else:
                raise ValueError("Embedding to be used not defined in config.py, or is not known")
        
        return getEmbeddings.__embeddings