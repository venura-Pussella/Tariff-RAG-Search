import logging

from data_stores.DataStores import DataStores

def findByHSCode(query: str, whitelist_releases: list[str] = None) -> list[dict]:
     """Searches the json dictionary containing all tariff pdf information for line items whose HSCodes match the search query,
     and returns a list of line items.

     Args:
         query (str): user query (expects an hs code)

     Returns:
         list[dict]: list of search results (line items)
     """
     if query == None or query == '': return[]

     data_dict = DataStores.getJson_dicts()
     
     results = []
     chapterNumber = 0

     # find the chapter number from the hs code (we restrict the search just to that chapter)
     try:
          dotIndex = query.find('.')
          if dotIndex == -1 and int(query)>=100: # eg: 2800, 200 which correspond to ch.28 and ch.2
               chapterNumber = int(query) // 100
          elif dotIndex == -1: # eg: 28,2 which correspond to ch.28 and ch.2
               chapterNumber = int(query)
          else: # eg: 2802, 2802.10
               chapterNumber = int(query[:dotIndex]) // 100
     except ValueError as e:
          logging.error("Value error raised, user must have enterted text or an unexpected format")
          logging.error(e)
          return []

     keys = []
     for key in data_dict.keys():
          if key[0] == chapterNumber: keys.append(key)
     if len(keys) == 0: return []
     
     for key in keys:
          if whitelist_releases:
               if key[1] not in whitelist_releases: continue
          items = data_dict[key]["Items"]
          for item in items:
               # todo: implement binary search
               if query in item["HS Code"]:
                    item["Release"] = key[1] # Adding this because we want a link to the PDF to be displayed with the result
                    item["Chapter Number"] = str(chapterNumber) # Adding this because we want a link to the PDF to be displayed with the result
                    results.append(item)

     sorted_results = sorted(results, key=lambda x: (x["HS Code"], x["Release"]))
     return sorted_results

