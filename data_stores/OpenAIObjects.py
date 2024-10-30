from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # read local .env file
import os
from openai import AzureOpenAI

class OpenAIObjects:

    __open_ai_client = None

    @classmethod
    def getOpenAIClient(cls):
        """Singleton method to return a Open AI client"""
        if cls.__open_ai_client == None:
            AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS = os.getenv('AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS')
            AZURE_OPENAI_API_VERSION_FOR_EMBEDDINGS = AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS.rsplit('api-version=')[1]
            cls.__open_ai_client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT_FOR_EMBEDDINGS, api_version=AZURE_OPENAI_API_VERSION_FOR_EMBEDDINGS)
            print("Open AI client created")

        return cls.__open_ai_client