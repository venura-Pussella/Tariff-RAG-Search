import json
from pathlib import Path
import pprint

class findByHSCode:

    cached_json_dict = {}
    file_path_that_was_cached = ""

    @staticmethod
    def findByHSCode(query: str) -> list:
        results = []
        file_path='functions\extract_data\extracted_data\ch28.json'

        if findByHSCode.file_path_that_was_cached == file_path:
            json_dict = findByHSCode.cached_json_dict
            print("Used cache.")
        else:
            json_dict = json.loads(Path(file_path).read_text())
            findByHSCode.cached_json_dict = json_dict
            findByHSCode.file_path_that_was_cached = file_path
            print(file_path + " cached.")

        items = json_dict["Items"]
        for item in items:
            # did not use binary search cuz then can search for any part of the hs code
            if query in item["HS Code"] or query == item["HS Code"]:
                results.append(item)

        return results


# query = input("Enter query:")
# results = findByHSCode.findByHSCode(query)

# json_string = json.dumps(results)
# with open('hs_code_search_results.json','w') as file:
#     file.write(json_string)
