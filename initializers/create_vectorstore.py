# SCRIPT
# This script, despite what its name might suggest, does not necessarrily create a vectorstore from scratch.
# It simply:
# 1. Takes 2 commandline arguments (for chapter number and mutex key).
# 2. Retreives json file from Azure storage that corresponds to the chapter number.
# 3. Turns each line-item in the json file to a langchain document.
# 4. Calls a script to upload the langchain documents to the vectorstore specified in the config file.

import sys
import os
# sys.path.append('../tariff-search') # IMPORTANT: required since we manually run this script from this location itself
sys.path.append(os.getcwd()) # IMPORTANT: required since we manually run this script from this location itself
import config
from data_stores.DataStores import DataStores
from langchain_core.documents import Document
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

commandLineArguments = sys.argv
chapterNumber = None
if len(commandLineArguments) == 3:
    chapterNumber = int(commandLineArguments[1])
    mutexKey = commandLineArguments[2]

print("Starting vectorstore creation..." + str(commandLineArguments))

# load the extracted json data into a dictionary
# ......................................... #
print("Loading json files into memory...")
DataStores.updateJSONdictsFromAzureBlob([chapterNumber])
if chapterNumber:
    json_dicts = DataStores.getJson_dicts([chapterNumber])
else:
    json_dicts = DataStores.getJson_dicts()
# ......................................... #


# create langchain documents with the textual data for embedding put into page_content
# and hscodes in metadata
# ......................................... #
docs = []
print("Filtering data...")

for key,value in json_dicts.items():
    json_dict = value

    items = json_dict["Items"]
    chapterName = json_dict["Chapter Name"]

    for item in items:
        prefix = item["Prefix"]
        hsHeadingName = item["HS Hdg Name"]
        hscode = item["HS Code"]
        description = item["Description"]

        content = "Chapter Name: " + chapterName + " , HS Heading Name:" + hsHeadingName + " ,Prefix: " + prefix +  " , Description:" + description
        document = Document(
            page_content=content,
            metadata={ "HS Code": hscode, "Chapter Number": chapterNumber }
        )
        docs.append(document)
# ......................................... #



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



