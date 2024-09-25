import sys
sys.path.append('../pdfplumber')

import initializers.loadJSONAtRuntime.loadJSONAtRuntime as lj
import shutil

print("Starting vectorstore creation...")

# load the json data into a dictionary
# ......................................... #
print("Loading json files into memory...")
json_dicts = lj.loadJSONsAtRuntime()
# ......................................... #



# create langchain documents with the data we need
# ......................................... #
from langchain_core.documents import Document

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

import config

# create vectorstore
# ......................................... #
if config.vectorstore == "chroma":
    import initializers.create_vectorstores.chroma_vectorstore as chr
    chr.createVectorstoreUsingChroma(docs)
elif config.vectorstore == "azure_cosmos_nosql":
    import initializers.create_vectorstores.az_cosmos_nosql_vectorstore as azcn
    azcn.createVectorstoreUsingAzureCosmosNoSQL(docs)
else:
    print("Type of vectorstore to be created/overwritten not specified in config.py")



# ......................................... #



