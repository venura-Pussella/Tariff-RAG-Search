from data_stores.DataStores import DataStores

def findByHSCode(query: str) -> list[dict]:
     """Searches the dictionary containing all tariff pdf information for line items whose HSCodes match the search query,
     and returns a list of line items
     ### Args:
          query: query for a hscode
          data_dict: dictionary containing all tariff pdf information
     ### Returns:
          List of line items
     """
     if query == None or query == '': return[]

     data_dict = DataStores.getJson_dicts()
     
     results = []
     chapterNumber = 0

     # find the chapter number from the hs code
     try:
          dotIndex = query.find('.')
          if dotIndex == -1 and int(query)>=100: # eg: 2800, 200 which correspond to ch.28 and ch.2
               chapterNumber = int(query) // 100
          elif dotIndex == -1: # eg: 28,2 which correspond to ch.28 and ch.2
               chapterNumber = int(query)
          else: # eg: 2802, 2802.10
               chapterNumber = int(query[:dotIndex]) // 100
     except ValueError as e:
          print("Value error raised, user must have enterted text or an unexpected format")
          print(e)
          return []

     if not (chapterNumber in data_dict): return []
     
     items = data_dict[chapterNumber]["Items"]
     for item in items:
          # todo: implement binary search
          if query in item["HS Code"]:
               results.append(item)
     return results

