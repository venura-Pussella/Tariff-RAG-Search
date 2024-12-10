import logging
import sys

log_messages = []

def configure_logging():
    # otherwise Azure info logs are too numerous
    logging.getLogger('azure').setLevel('WARNING')

    # remaining lines are to configure the flask logging - we can get them in Azure app service when running from a docker container)
    
    # custom logging levels
    logging.addLevelName(25,'USER') # because INFO is too much for the end user
    logging.addLevelName(15,'LLM') # for developers to track LLM
    
    # make custom logging.Handler inherited class to store log messages in the log_messages list
    class ListHandler(logging.Handler):

        def emit(self, record):
            log_entry = self.format(record)
            log_messages.append(log_entry)

    format_string = "[%(asctime)s: %(levelname)s: %(module)s: %(message)s]"
    list_handler = ListHandler()


    logging.basicConfig(
        level=logging.INFO,
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout), # To send logs to terminal output
            list_handler
        ]
    )
