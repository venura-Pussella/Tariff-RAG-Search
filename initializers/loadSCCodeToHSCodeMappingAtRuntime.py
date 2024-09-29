def getSCCodeToHSCodeMapping() -> dict[str,list[str]]:
    """Retrieves SCCode to HSCode mapping from the filepath defined inside the function.
    Returns:
        dictionary with key as SCCode and value as python list of HSCodes
    """
    
    import pickle 
            
    with open('initializers/extract_data/scCodeToHSCodeMapping.pkl', 'rb') as f:
        scToHSMapping = pickle.load(f)
    
    if not bool(scToHSMapping): print("WARNING: SC Code to HS Code dictionary is empty!")

    return scToHSMapping