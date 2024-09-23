
from langchain_community.document_loaders import JSONLoader

import json
from pathlib import Path
from pprint import pprint

# load the json data into a dictionary
# ......................................... #
file_path='functions\extract_data\extracted_data\ch28.json'
json_dict = json.loads(Path(file_path).read_text())
# ......................................... #


# create langchain documents with the data we need
# ......................................... #
from langchain_core.documents import Document

docs = []
items = json_dict["Items"]
source = json_dict["Document Name"]

for item in items:
    prefix = item["Prefix"]
    hsHeadingName = item["HS Hdg Name"]
    hscode = item["HS Code"]
    description = item["Description"]

    content = "Prefix: " + prefix + " , HS Heading Name:" + hsHeadingName + " , Description:" + description
    document = Document(
        page_content=content,
        metadata={
            "source": source,
            "HS Code": hscode   
        }
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



