import config
import json
import os
import logging
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import AzureChatOpenAI
from data_stores.DataStores import DataStores as ds
from app_functions import vectorstoreSearch as vs
AZURE_OPENAI_ENDPOINT_FOR_CHATCOMPLETION = os.getenv('AZURE_OPENAI_ENDPOINT_FOR_CHATCOMPLETION')
AZURE_OPENAI_API_VERSION_FOR_CHATCOMPLETION = AZURE_OPENAI_ENDPOINT_FOR_CHATCOMPLETION.rsplit('api-version=')[1]

def generateDescriptionSearchQueryFromUserQueryToChatBot(userQuery_to_chatBot:str) -> str:
    """A user can ask a very general/complex question from the chat bot. The documents needed to answer the question (RAG) must be fetched from the vectorstore using a similarity search (or similar). For this
    the user's question must be simplified to drop information that may not have been embedded in the vectorstore.
    ( eg: If the user query is 'What is the preferential_duty_SF for a tractor.' the description_search to fetch documents should be 'tractor' )

    Args:
        userQuery_to_chatBot (str): question user passed to chatbot.

    Returns:
        str: Search query suitable for the vectorstore search.
    """

    template_for_generating_description_search = """You are a help desk agent at a logistics company. \
    A user has given you a question regarding tariffs of a certain item or a range of items. \
    You need to retrieve related documents required to answer the question, but these documents must be retrieved from a vectorstore. \
    The document has a json structure as shown in the following example delimited by double backticks: \
    ``"Prefix": "Plates, sheets, strip and foil :", "HS Hdg Name": "Lead plates, sheets, strip and foil; lead\npowders and flakes.", "HS Hdg": "78.04", "HS Code": "7804.11.00N", "Description": "Sheets, strip and foil of a thickness (excluding\nany backing) exceeding 0.2 mm", "Unit": "kg", "ICL/SLSI": "", "Preferential Duty_AP": "", "Preferential Duty_AD": "", "Preferential Duty_BN": "", "Preferential Duty_GT": "", "Preferential Duty_IN": "Free", "Preferential Duty_PK": "Free", "Preferential Duty_SA": "", "Preferential Duty_SF": "Free", "Preferential Duty_SD": "Free", "Preferential Duty_SG": "Free", "Gen Duty": "Free", "VAT": "18%", "PAL_Gen": "10%", "PAL_SG": "6%", "Cess_GEN": "", "Excise SPD": "", "SSCL": "2.5%", "SCL": "", "SC Code": "", "Cess_SG": ""`` \
    However note that the documents stored in the vectorstore only contains textual fields- i.e. the fields Prefix, HS Hdg Name and Description. \
    Generate the shortest but most precise query possible to pass into a similarity search in order to retrieve the documents. \
    The question is as follows (delimited by triple backticks): ```{question}```
    Tell me the answer only, no need to offer any explanations.
    """

    prompt_template = ChatPromptTemplate.from_template(template_for_generating_description_search)
    humanMessage_and_promtTemplate = prompt_template.format_messages(question=userQuery_to_chatBot)

    chat = AzureChatOpenAI(temperature=0.0, model=config.modelForChatBot, azure_endpoint=AZURE_OPENAI_ENDPOINT_FOR_CHATCOMPLETION, api_version=AZURE_OPENAI_API_VERSION_FOR_CHATCOMPLETION)
    response_humaizedQueryForDescSearch = chat(humanMessage_and_promtTemplate)

    return response_humaizedQueryForDescSearch.content

def getChatBotAnswer(userQuery_to_chatBot: str, release: str) -> str:
    """Takes a user's query, retrieves suitable documents using vector search and returns an answer.

    Args:
        userQuery_to_chatBot (str): The user's question

    Returns:
        str: llm generated answer
    """
    descriptionSearchQuery = generateDescriptionSearchQueryFromUserQueryToChatBot(userQuery_to_chatBot)
    logging.log(15,f'descriptionSearchQuery: {descriptionSearchQuery}')
    resultsAndScores = vs.vectorStoreSearch(descriptionSearchQuery, [release])
    lineItems = resultsAndScores[0]
    lineItemsJSONString = json.dumps(lineItems)
    logging.log(15,f'line items retrieved: {lineItemsJSONString}')

    template_for_answering_userQuery_with_retrieved_docs = """You are a help desk agent at a logistics company. \
    A user has given you a question regarding tariffs of a certain item or a range of items. \
    Use the documents (in the form of a json formatted string) delimited by double backticks to answer the user's question. \
    ``{docs}``
    The textual data you need to consider when making a decision fall under the keys: 'HS Hdg Name','Description' and 'Prefix'.
    The user's question is as follows (delimited by triple backticks): ```{question}``` \
    Give your answer in markdown, using tables if required.
    """

    prompt_template = ChatPromptTemplate.from_template(template_for_answering_userQuery_with_retrieved_docs)
    humanMessage_and_promtTemplate = prompt_template.format_messages(question=userQuery_to_chatBot, docs=lineItemsJSONString)

    chat = AzureChatOpenAI(temperature=0.0, model=config.modelForChatBot, azure_endpoint=AZURE_OPENAI_ENDPOINT_FOR_CHATCOMPLETION, api_version=AZURE_OPENAI_API_VERSION_FOR_CHATCOMPLETION)
    response_humaizedQueryForDescSearch = chat(humanMessage_and_promtTemplate)

    return response_humaizedQueryForDescSearch.content
