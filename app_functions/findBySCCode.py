from data_stores.DataStores import DataStores

def findBySCCode(query: str) -> list[dict]:
    """Searches the dictionary containing all tariff pdf information for line items whose SCCodes match the search query,
     and returns a list of line items
     ### Args:
          query: query for a sccode
          data_dict: dictionary containing all tariff pdf information
          scToHSMapping: dictionary containing scToHSMapping
     ### Returns:
          List of line items
     """
    
    scToHSMapping = DataStores.getSCCodeToHSCodeMapping()
    data_dict = DataStores.getJson_dicts()

    # formatting user query to match dictionary
    sccode = ''
    if len(query) == 3:
        sccode = 'SC' + query
    elif len(query) == 2:
        sccode = 'SC0' + query
    else:
        sccode = query
    
    hscodes = []
    if sccode in scToHSMapping:
        hscodes = scToHSMapping[sccode]
    else:
        return []
    
    from app_functions import findByHSCode as fhs
    allResults = []
    for hscode in hscodes:
        results = fhs.findByHSCode(hscode)
        allResults = allResults + results
    
    return allResults