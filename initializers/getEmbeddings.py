def getEmbeddings():
    """Returns embedding according to config.py
    Raises:
        ValueError: If Embedding to be used not defined in config.py, or is not known
    """
    import config

    if config.embeddings == 'OpenAI':
        from langchain_community.embeddings import OpenAIEmbeddings
        embedding = OpenAIEmbeddings()
    else:
        raise ValueError("Embedding to be used not defined in config.py, or is not known")
    
    return embedding