from data_stores.DataStores import DataStores

def findBySCCode(query: str) -> list[dict]:
    """Temporariry implementation. May not be efficient.
    """
    # formatting user query to match dictionary
    sccode = ''
    if len(query) == 3:
        sccode = 'SC' + query
    elif len(query) == 2:
        sccode = 'SC0' + query
    else:
        sccode = query

    data_dict = DataStores.getJson_dicts()
    hscodes = []
    for chapter in data_dict.keys():
        chapter_dict = data_dict[chapter]
        items = chapter_dict['Items']
        for item in items:
            if item['SC Code'] == sccode: hscodes.append(item['HS Code'])
    
    from app_functions import findByHSCode as fhs
    allResults = []
    for hscode in hscodes:
        results = fhs.findByHSCode(hscode)
        allResults = allResults + results
    
    return allResults