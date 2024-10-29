from openai import AzureOpenAI
import numpy as np
import config
import os
import concurrent.futures
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # read local .env file
AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS = os.getenv('AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS')
AZURE_OPENAI_API_VERSION_FOR_EMBEDDINGS = AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS.rsplit('api-version=')[1]

class Line_Item:
    """An object to hold a line item that goes into the cosmos vectorstore.
    Holds a dictionary of fields that should be embedded (text fields - chapter name, hs heading, prefix and description).
    Holds a dictionary of metadata fields that we use for identification (eg: HS code)
    Holds the vector embedding of the fields to be embedded (None at first, updated when the vectorize() method is called)
    """

    def __init__(self, fields_to_embed: dict, metadata_fields: dict) -> None:
        """Creates an object to hold a line item that goes into the cosmos vectorstore.
        Be sure to called the vectorize method to generate the vector for the text.

        Args:
            fields_to_embed (dict): dictionary of fields that should be embedded (text fields - chapter name, hs heading, prefix and description).
            metadata_fields (dict): dictionary of metadata fields that we use for identification (eg: HS code)
        """
        self.fields_to_embed = fields_to_embed
        self.metadata_fields = metadata_fields
        self.vector: list[float] = None

    def vectorize(self):
        """Generates a single vector embedding for the text fields and stores it in the vector attribute.
        """
        vectors = []
        futures = []
        client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS, api_version=AZURE_OPENAI_API_VERSION_FOR_EMBEDDINGS)

        def get_vector_for_fieldvalue(text):
                vector = client.embeddings.create(input = text, model=config.embeddingModel).data[0].embedding
                vectors.append(vector)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for field,text in self.fields_to_embed.items():
                futures.append(executor.submit(get_vector_for_fieldvalue, text))
            concurrent.futures.wait(futures)

        mean_vector = np.mean(vectors, axis=0)
        self.vector = mean_vector.tolist()
