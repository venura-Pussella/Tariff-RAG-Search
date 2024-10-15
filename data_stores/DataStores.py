import json
import config
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from azure.storage.blob import ContainerClient
from azure.core.exceptions import ResourceNotFoundError

class DataStores:
    """Used to hold and manipulate the json dictionaries, and HScode-SCcode mappings.
    
    Attributes:
        __hsCodeToSCCodeMapping: dict[str,str]: SC Code functionality temporarily removed. This holds an empty dictionary.
        __scCodeToHSCodeMapping: dict[str,str]: SC Code functionality temporarily removed. This holds an empty dictionary.
        __json_dicts: dict[int,str]: Maps chapter number with the chapter dictionary.

    Methods:
        getJson_dicts(cls, chapterNumbers: list[int] = None) -> dict[int,str]: Returns the class variable containing the dictionary of chapter dictionaries.
        updateJSONdictsFromAzureBlob(cls, chapterNumbers: list[int] = None) -> None: Updates the class variable containing the dictionary of chapter dictionaries.
        insertNewJSONDictManually(cls, json_string: str, chapterNumber: int) -> None: Inserts a dictionary for a specified chapter number in the dictionary of chapter dictionaries.
        getHSCodeToSCCodeMapping(cls) -> dict[str,str]: SC Code functionality temporarily removed. This just returns an empty dictionary.
        getSCCodeToHSCodeMapping(cls) -> dict[str,list[str]]: SC Code functionality temporarily removed. This just returns an empty dictionary.
    """

    __hsCodeToSCCodeMapping: dict[str,str] = {}
    __json_dicts: dict[int,str] = {}
    __scCodeToHSCodeMapping: dict[str,list[str]] = {}

    @classmethod
    def getJson_dicts(cls, chapterNumbers: list[int] = None) -> dict[int,str]:
        """Returns the class variable containing the dictionary of chapter dictionaries. Make sure to update this using updateJSONdictsFromAzureBlob if required.

        Args:
            chapterNumbers (list[int], Optional, defaults to None): If not none, returns a filtered dictionary, otherwise no filter.
        
        Returns:
            Dictionary with chapter dictionaries (chapter number maps to chapter dictionary)
        """
        if chapterNumbers:
            dicts = {}
            for chapterNumber in chapterNumbers:
                dicts[chapterNumber] = cls.__json_dicts[chapterNumber]
            return dicts
        return DataStores.__json_dicts
    
    @classmethod
    def updateJSONdictsFromAzureBlob(cls, chapterNumbers: list[int] = None) -> None:
        """Updates the class variable containing the dictionary of chapter dictionaries.

        Args:
            chapterNumbers (list[int], Optional, defaults to None): If not none, updates from all chapters found in the blob, else just the ones specified,
        
        Returns:
            Dictionary with chapter dictionaries (chapter number maps to chapter dictionary)
        """
        def updateJSONdictFromAzureBlob(jsonName: str, chapterNumber: int):
            blob_client = container_client.get_blob_client(blob=jsonName)
            try:
                downloader = blob_client.download_blob(max_concurrency=1, encoding='UTF-8')
                blob_text = downloader.readall()
                json_dict = json.loads(blob_text)
                cls.__json_dicts[chapterNumber] = json_dict
            except ResourceNotFoundError: # that means the chapter does not exist (probably has been deleted). Therefore it must be removed from cls.__json_dicts
                del cls.__json_dicts[chapterNumber]
            

        container_client: ContainerClient = abo.get_container_client(config.json_container_name)
        jsonNameList = abo.getListOfFilenamesInContainer(config.json_container_name)

        if chapterNumbers:
            for chapterNumber in chapterNumbers:
                jsonName = str(chapterNumber) + '.json'
                updateJSONdictFromAzureBlob(jsonName, chapterNumber)
        else:
            for jsonName in jsonNameList:
                updateJSONdictFromAzureBlob(jsonName)
        print("Loading jsons from Azure Blob into memory completed.")

    @classmethod
    def insertNewJSONDictManually(cls, json_string: str, chapterNumber: int) -> None:
        """Inserts a dictionary for a specified chapter number in the dictionary of chapter dictionaries.

        Args:
            json_string: (str) the json formatted string from which to create the dictionary for the specified chapter number
            chapterNumber: (int)

        Returns: 
            void
        """
        new_json_dict = json.loads(json_string)
        cls.__json_dicts[chapterNumber] = new_json_dict

    @classmethod
    def getHSCodeToSCCodeMapping(cls) -> dict[str,str]:
        """SC Code functionality temporarily removed. This just returns an empty dictionary.
        """
        # if DataStores.__hsCodeToSCCodeMapping == None:

        #     # Read from csv file containing HS Code to SC Code mapping. HS Code is unique.
        #     csv_file = 'files/HSCode_to_SCCode_Mapping Sorted.csv'
        #     rows = []

        #     with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        #         csv_reader = csv.reader(file)

        #         for row in csv_reader:
        #             rows.append(row)

        #     # HS Code format: ####.##.##N

        #     DataStores.__hsCodeToSCCodeMapping = {}

        #     for n in range(1,len(rows)):
        #         row = rows[n]
        #         key = row[0]
        #         value = row[1]
        #         DataStores.__hsCodeToSCCodeMapping[key] = value
            
        #     if not bool(DataStores.__hsCodeToSCCodeMapping): print("WARNING: HS Code to SC Code dictionary is empty!")

        # return DataStores.__hsCodeToSCCodeMapping
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