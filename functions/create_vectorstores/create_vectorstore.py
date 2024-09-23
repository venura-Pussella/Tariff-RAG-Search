import json
from pathlib import Path
from pprint import pprint
#from loadJSONAtRuntime.loadJSONAtRuntime import loadJSONAtRuntime
from functions.loadJSONAtRuntime.loadJSONAtRuntime import loadJSONAtRuntime

# load the json data into a dictionary
# ......................................... #
json_dicts = loadJSONAtRuntime()
# ......................................... #

# create langchain documents with the data we need
# ......................................... #
from langchain_core.documents import Document

docs = []

for json_dict in json_dicts:

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
import os
import openai

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
openai.api_key = os.environ['OPENAI_API_KEY']

from langchain.embeddings.openai import OpenAIEmbeddings
embedding = OpenAIEmbeddings()


from langchain.vectorstores import Chroma

persist_directory = "functions\create_vectorstores\\vectorstores\chroma"


vectordb = Chroma.from_documents(
    documents=docs,
    embedding=embedding,
    persist_directory=persist_directory
)
# ......................................... #



