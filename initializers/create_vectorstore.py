# SCRIPT
# This script, despite what its name might suggest, does not necessarrily create a vectorstore from scratch.
# It simply:
# 1. Takes 2 commandline arguments (for chapter number and mutex key).
# 2. Retreives json file from Azure storage that corresponds to the chapter number.
# 3. Turns each line-item in the json file to a Line_Item object.
# 4. Calls a script to upload the Line_Item objects with vector embeddings to the vectorstore specified in the config file.

import sys
import os
# sys.path.append('../tariff-search') # IMPORTANT: required since we manually run this script from this location itself
sys.path.append(os.getcwd()) # IMPORTANT: required since we manually run this script from this location itself
import config
from data_stores.DataStores import DataStores
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
from initializers.Line_Item import Line_Item
import concurrent.futures
from datetime import datetime

commandLineArguments = sys.argv
chapterNumber = None
if len(commandLineArguments) == 3:
    chapterNumber = int(commandLineArguments[1])
    mutexKey = commandLineArguments[2]

print("Starting addition to vectorstore..." + str(commandLineArguments))

# load the extracted json data into a dictionary
# ......................................... #
print("Loading json files into memory...")
DataStores.updateJSONdictsFromAzureBlob([chapterNumber])
if chapterNumber:
    json_dicts = DataStores.getJson_dicts([chapterNumber])
else:
    json_dicts = DataStores.getJson_dicts()
# ......................................... #


# create Line_Item objects
# ......................................... #
docs = []
print(f"Creating Line Item objects from json chapter(s)... {datetime.now()}")

for key,value in json_dicts.items():
    json_dict = value

    items = json_dict["Items"]
    chapterName = json_dict["Chapter Name"]

    def create_line_item(item):
        prefix: str = item["Prefix"]
        hsHeadingName = item["HS Hdg Name"]
        hscode = item["HS Code"]
        description = item["Description"]
        prefix = prefix.strip()
        if len(prefix) > 0:
            if prefix[len(prefix) - 1] == ':':
                prefix_and_description = prefix + ' ' + description
            else:
                prefix_and_description = prefix + ': ' + description
        else:
            prefix_and_description = description
        # print(f'started creating line item for hscode {hscode} at time {datetime.now()}')

        # create a 'document' - a dictionary containing all the information I want to create a line item in cosmsos DB
        # this includes the fields that need to be embedded and then combined to a single vector, and metadata fields
        fields_to_embed = {
            "Chapter Name": chapterName,
            "HS Heading Name": hsHeadingName,
            "Prefix and Description": prefix_and_description
        }
        metadata_fields = {
            "HS Code": hscode
        }
        line_item = Line_Item(fields_to_embed, metadata_fields)
        line_item.vectorize()
        docs.append(line_item)
        # print(f'Ended creating line item for hscode {hscode} at time {datetime.now()}')

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for item in items:
            futures.append(executor.submit(create_line_item, item))
        concurrent.futures.wait(futures)
        
print(f"END creating Line Item objects from json chapter(s)... {datetime.now()}")
# ......................................... #


# Pass the Line_Item objects for uploading to the vectorstore.
# ......................................... #
if config.vectorstore == "chroma":
    import initializers.chroma_vectorstore as chr
    chr.createVectorstoreUsingChroma(docs)
elif config.vectorstore == "azure_cosmos_nosql":
    import initializers.az_cosmos_nosql_vectorstore as azcn
    azcn.createVectorstoreUsingAzureCosmosNoSQL(docs, chapterNumber, mutexKey)
else:
    print("Type of vectorstore to be created/overwritten not specified in config.py")



# ......................................... #



