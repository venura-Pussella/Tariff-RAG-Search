import pickle
import csv
import os
import json
from pathlib import Path

class DataStores:
    """Singleton class to hold datastores (So that things are loaded from disk only once per item)."""

    __hsCodeToSCCodeMapping: dict[str,str] = None
    __json_dicts = None
    __scCodeToHSCodeMapping = None

    @classmethod
    def getJson_dicts(cls):
        """Singleton to get the extracted jsons (from the PDFs) into memory.
        Loads the .json files (the extracted data from the PDFs) into memory from the filepath defined in the function, and returns them as a dictionary.
	    """
        if DataStores.__json_dicts == None:
            print("Loading jsons into memory")
            filepath = 'files/extracted_data'
            DataStores.__json_dicts = {}

            for filename in os.listdir(filepath):
                f = os.path.join(filepath, filename)
                if os.path.isfile(f):
                    print("Loading json @ " + f)
                    json_dict = json.loads(Path(f).read_text())
                    chapterNumber = json_dict["Chapter Number"]
                    DataStores.__json_dicts[chapterNumber] = json_dict

            print("Loading jsons into memory completed.")
        
        return DataStores.__json_dicts
  
    @classmethod
    def getHSCodeToSCCodeMapping(cls) -> dict[str,str]:
        """Retrieves singleton HSCode to SCCode mapping. Initialized using the filepath defined inside the function.
        Returns:
            dictionary with key as HSCode and value as SCCode
        """

        if DataStores.__hsCodeToSCCodeMapping == None:

            # Read from csv file containing HS Code to SC Code mapping. HS Code is unique.
            csv_file = 'files/HSCode_to_SCCode_Mapping Sorted.csv'
            rows = []

            with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
                csv_reader = csv.reader(file)

                for row in csv_reader:
                    rows.append(row)

            # HS Code format: ####.##.##N

            DataStores.__hsCodeToSCCodeMapping = {}

            for n in range(1,len(rows)):
                row = rows[n]
                key = row[0]
                value = row[1]
                DataStores.__hsCodeToSCCodeMapping[key] = value
            
            if not bool(DataStores.__hsCodeToSCCodeMapping): print("WARNING: HS Code to SC Code dictionary is empty!")

        return DataStores.__hsCodeToSCCodeMapping

    @classmethod
    def getSCCodeToHSCodeMapping(cls) -> dict[str,list[str]]:
        """Retrieves singleton SCCode to HSCode mapping from the filepath defined inside the function.
        Returns:
            dictionary with key as SCCode and value as python list of HSCodes
        """
        if DataStores.__scCodeToHSCodeMapping == None:
            with open('files/scCodeToHSCodeMapping.pkl', 'rb') as f:
                DataStores.__scCodeToHSCodeMapping = pickle.load(f)
            
            if not bool(DataStores.__scCodeToHSCodeMapping): print("WARNING: SC Code to HS Code dictionary is empty!")

        return DataStores.__scCodeToHSCodeMapping