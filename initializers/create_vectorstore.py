# SCRIPT
# Creates a vectorstore with the extracted data and chosen vectorstore in config.py

import sys
sys.path.append('../pdfplumber') # IMPORTANT: required since we manually run this script from this location itself
import config
from data_stores.DataStores import DataStores
from langchain_core.documents import Document
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

print("Starting vectorstore creation...")

# load the extracted json data into a dictionary
# ......................................... #
print("Loading json files into memory...")
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
            metadata={ "HS Code": hscode }
        )
        docs.append(document)
# ......................................... #



# create vectorstore
# ......................................... #
if config.vectorstore == "chroma":
    import initializers.chroma_vectorstore as chr
    chr.createVectorstoreUsingChroma(docs)
elif config.vectorstore == "azure_cosmos_nosql":
    import initializers.az_cosmos_nosql_vectorstore as azcn
    azcn.createVectorstoreUsingAzureCosmosNoSQL(docs)
else:
    print("Type of vectorstore to be created/overwritten not specified in config.py")



# ......................................... #


