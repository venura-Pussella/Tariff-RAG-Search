# The name of this file doesn't necessarily reflect what it contains. It only contains one method - read it!

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
import logging
import concurrent.futures
from datetime import datetime

import config
from data_stores.DataStores import DataStores
from initializers.Line_Item import Line_Item


def update_vectorstore(chapterNumber: int, mutexKey: str, release_date: str):
    """Updates the specified chapter_number-release to the vectorstore.
    1. Automatically retrieves corresponding json file from Azure storage.
    2. Turns each line-item in the json file to a Line_Item object.
    3. Uploads them to the vectorstore specified in the config file, with vector embeddings.

    Args:
        chapterNumber (int): _description_
        mutexKey (str): _description_
        release_date (str): _description_
    """
    logging.info(f"Starting addition to vectorstore... chapter {chapterNumber} of release {release_date}")

    # load the extracted json data into a dictionary
    # ......................................... #
    logging.info("Loading json files into memory...")
    DataStores.updateJSONdictsFromAzureBlob([(chapterNumber,release_date)])
    if chapterNumber:
        json_dicts = DataStores.getJson_dicts([(chapterNumber,release_date)])
    else:
        json_dicts = DataStores.getJson_dicts()
    # ......................................... #

    # create Line_Item objects
    # ......................................... #
    docs = []
    logging.info(f"Creating Line Item objects from json chapter(s)... Chapter number:{chapterNumber}, release {release_date}... {datetime.now()}")

    for key,value in json_dicts.items():
        json_dict = value

        items = json_dict["Items"]
        chapterName = json_dict["Chapter Name"]

        def create_line_item(item):
            """Helper function.
            """
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
            
    logging.info(f"END creating Line Item objects from json chapter(s)...Chapter number:{chapterNumber}, release {release_date}... {datetime.now()}")
    # ......................................... #


    # Pass the Line_Item objects for uploading to the vectorstore.
    # ......................................... #
    if config.vectorstore == "chroma":
        import initializers.chroma_vectorstore as chr
        chr.createVectorstoreUsingChroma(docs)
    elif config.vectorstore == "azure_cosmos_nosql":
        import initializers.az_cosmos_nosql_vectorstore as azcn
        azcn.createVectorstoreUsingAzureCosmosNoSQL(docs, chapterNumber, mutexKey, release_date)
    else:
        logging.error("Type of vectorstore to be created/overwritten not specified in config.py")



    # ......................................... #



