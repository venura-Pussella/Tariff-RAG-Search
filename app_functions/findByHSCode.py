import json
from pathlib import Path

# search jsons by HS Code
def findByHSCode(query: str, data_dict: dict) -> list:
        if query == None or query == '' or (not float(query)):
          return[]
        
        results = []
        chapterNumber = 0

        # find the chapter number from the hs code
        dotIndex = query.find('.')
        if dotIndex == -1 and int(query)>=100:
             chapterNumber = int(query) // 100
        elif dotIndex == -1:
             chapterNumber = int(query)
        else:
             chapterNumber = int(query[:dotIndex]) // 100

        if not (chapterNumber in data_dict):
             return []
        items = data_dict[chapterNumber]["Items"]
        for item in items:
            # implement binary search
            if query in item["HS Code"] or query == item["HS Code"]:
                results.append(item)

        return results

    


# query = input("Enter query:")
# results = findByHSCode.findByHSCode(query)

# json_string = json.dumps(results)
# with open('hs_code_search_results.json','w') as file:
#     file.write(json_string)
