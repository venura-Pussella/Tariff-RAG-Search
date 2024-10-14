import pickle
import csv
import os
import json
import config
from pathlib import Path
from initializers.file_management import getListOfFilenamesInContainer, download_blob_file
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, BlobBlock, StandardBlobTier
from data_stores.AzureBlobObjects import AzureBlobObjects as ABO

class DataStores:
    """Singleton class to hold datastores (So that things are loaded from disk only once per item)."""

    __hsCodeToSCCodeMapping: dict[str,str] = {}
    __json_dicts = {}
    __scCodeToHSCodeMapping = {}

    @classmethod
    def getJson_dicts(cls, chapterNumbers: list[int] = None):
        if chapterNumbers:
            dicts = {}
            for chapterNumber in chapterNumbers:
                dicts[chapterNumber] = cls.__json_dicts[chapterNumber]
            return dicts
        return DataStores.__json_dicts
    

    @classmethod
    def updateJSONdictsFromAzureBlob(cls, chapterNumbers: list[int] = None):

        def updateJSONdictFromAzureBlob(jsonName: str):
            blob_client = container_client.get_blob_client(blob=jsonName)
            downloader = blob_client.download_blob(max_concurrency=1, encoding='UTF-8')
            blob_text = downloader.readall()
            json_dict = json.loads(blob_text)
            chapterNumber = json_dict["Chapter Number"]
            DataStores.__json_dicts[chapterNumber] = json_dict

        container_client: ContainerClient = ABO.get_container_client(config.json_container_name)
        jsonNameList = getListOfFilenamesInContainer(config.json_container_name)

        if chapterNumbers:
            for chapterNumber in chapterNumbers:
                jsonName = str(chapterNumber) + '.json'
                updateJSONdictFromAzureBlob(jsonName)
        else:
            for jsonName in jsonNameList:
                updateJSONdictFromAzureBlob(jsonName)
        
        print("Loading jsons from Azure Blob into memory completed.")

    @classmethod
    def insertNewJSONDictManually(cls, json_string, chapterNumber: int):
        new_json_dict = json.loads(json_string)
        cls.__json_dicts[chapterNumber] = new_json_dict


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