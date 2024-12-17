import json
import logging
import config
import csv
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from azure.storage.blob import ContainerClient
from azure.core.exceptions import ResourceNotFoundError

class DataStores:
    """Used to hold and manipulate the json dictionaries, and HScode-SCcode mappings(depreciated).
    
    Attributes:
        __hsCodeToSCCodeMapping: dict[str,str]: SC Code functionality temporarily removed. This holds an empty dictionary.
        __scCodeToHSCodeMapping: dict[str,str]: SC Code functionality temporarily removed. This holds an empty dictionary.
        __json_dicts: dict[int,str]: Maps chapter_number-release_date with the chapter dictionary (a json string).
    """

    __hsCodeToSCCodeMapping: dict[str,str] = {}
    __json_dicts: dict[tuple[str,int],str] = {} # Maps chapter_number-release_date with the chapter dictionary (a json string).
    __scCodeToHSCodeMapping: dict[str,list[str]] = {}

    @classmethod
    def getJson_dicts(cls, chapterNumber_releaseDate_combos: list[tuple[int,str]] = None) -> dict[tuple[str,int],str]:
        """Returns the singleton object containing the dictionary of chapter dictionaries (mapping chapter_number-release_date with the chapter dictionary (a json string)). Make sure to update this using updateJSONdictsFromAzureBlob if required.

        Args:
            chapterNumber_releaseDate_combos (list[tuple[int,str]], optional): If specified, filters the returned dictionary to these combos. Defaults to None.

        Returns:
            dict[tuple[str,int],str]: Dictionary mapping a chapter_number-release_date to its json string.
        """
        if chapterNumber_releaseDate_combos:
            dicts = {}
            for combo in chapterNumber_releaseDate_combos:
                dicts[(combo[0],combo[1])] = cls.__json_dicts[(combo[0],combo[1])]
            return dicts
        return DataStores.__json_dicts
    
    @classmethod
    def updateJSONdictsFromAzureBlob(cls, chapterNumber_releaseDate_combos: list[tuple[int,str]] = None) -> None:
        """Updates the singleton object containing the dictionary of chapter-release dictionaries from Azure storage.

        Args:
            chapterNumber_releaseDate_combos (list[tuple[int,str]], optional): If specified, only updates the items matching this filter. Defaults to None.
        """
        def updateJSONdictFromAzureBlob(_jsonName: str, _chapterNumber: int, _release_date: str):
            """Helper method for updateJSONdictsFromAzureBlob parent function.
            """
            blob_client = container_client.get_blob_client(blob=_jsonName)
            try:
                downloader = blob_client.download_blob(max_concurrency=1, encoding='UTF-8')
                blob_text = downloader.readall()
                json_dict = json.loads(blob_text)
                cls.__json_dicts[(_chapterNumber, _release_date)] = json_dict
            except ResourceNotFoundError: # that means the chapter does not exist (probably has been deleted). Therefore it must be removed from cls.__json_dicts
                try: del cls.__json_dicts[(_chapterNumber, _release_date)]
                except KeyError: pass # the chapter was not in cls.__json_dicts anyway, so nothing to do
            

        container_client: ContainerClient = abo.get_container_client(config.json_container_name)
        jsonNameList = abo.getListOfFilenamesInContainer(config.json_container_name)

        if chapterNumber_releaseDate_combos:
            for combo in chapterNumber_releaseDate_combos:
                chapter_number = combo[0]
                release_date = combo[1]
                jsonName = release_date + '/'+ str(chapter_number) + '.json'
                updateJSONdictFromAzureBlob(jsonName, chapter_number, release_date)
        else:
            for jsonName in jsonNameList:
                release_date = jsonName.rsplit('/')[0]
                chapter_number = int(jsonName.rsplit('/')[1].rsplit('.')[0])
                updateJSONdictFromAzureBlob(jsonName, chapter_number, release_date)
        logging.info("Loading jsons from Azure Blob into memory completed.")

    @classmethod
    def insertNewJSONDictManually(cls, json_string: str, chapterNumber: int, release_date: str) -> None:
        """Inserts a dictionary for a specified chapter_number-release_date in the singleton object 
        holding all of the chapter_number-release_date to json string mapping.
        """
        new_json_dict = json.loads(json_string)
        cls.__json_dicts[(chapterNumber, release_date)] = new_json_dict

    @classmethod
    def getHSCodeToSCCodeMapping(cls) -> dict[str,str]:
        """Temporary implementation. Reads hscode to sc code mapping from the csv file.
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
        return {}

    @classmethod
    def getSCCodeToHSCodeMapping(cls) -> dict[str,list[str]]:
        """SC Code functionality temporarily removed. This just returns an empty dictionary.
        """
        # if DataStores.__scCodeToHSCodeMapping == None:
        #     with open('files/scCodeToHSCodeMapping.pkl', 'rb') as f:
        #         DataStores.__scCodeToHSCodeMapping = pickle.load(f)
            
        #     if not bool(DataStores.__scCodeToHSCodeMapping): print("WARNING: SC Code to HS Code dictionary is empty!")

        # return DataStores.__scCodeToHSCodeMapping
        return {}