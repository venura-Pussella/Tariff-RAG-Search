def findBySCCode(query: str, data_dict: dict, scToHSMapping: dict) -> list[dict]:
    """Searches the dictionary containing all tariff pdf information for line items whose SCCodes match the search query,
     and returns a list of line items
     Args:
          query: query for a sccode
          data_dict: dictionary containing all tariff pdf information
          scToHSMapping: dictionary containing scToHSMapping
     Returns:
          List of line items
     """
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
        results = fhs.findByHSCode(hscode, data_dict)
        allResults = allResults + results
    
    return allResults