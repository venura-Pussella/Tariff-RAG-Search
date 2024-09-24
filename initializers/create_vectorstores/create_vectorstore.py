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

persist_directory = "initializers\create_vectorstores\\vectorstores\chroma"
print("Deleting existing vectorstore...")
shutil.rmtree(persist_directory)

print("Creating vectorstore...")
vectordb = Chroma.from_documents(
    documents=docs,
    embedding=embedding,
    persist_directory=persist_directory
)
vectordbCollectionCount = vectordb._collection.count()
print("Vector store created with collection count: " + str(vectordbCollectionCount))
# ......................................... #



