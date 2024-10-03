import config

class TokenTracker:

    lifetimeTokens = 0
    lifetimeTokens_chatbot = 0

    @classmethod
    def updateTokens(cls,text):
        """Static method to track lifetime token count. If lifetime token limit in config.py is exceeded, exits app.
        Args:
            text: Text that will be tokenized, and thus its token count must be added to lifetime tokens.
        """

        numOfTokens = TokenTracker.getTokenCount(text)
        TokenTracker.lifetimeTokens += numOfTokens
        print("Lifetime tokens: " + str(TokenTracker.lifetimeTokens))
        if TokenTracker.lifetimeTokens > config.lifetimeTokenLimit:
            print("Hit Lifetime token limit. Exiting!")
            exit()

    @classmethod
    def updateTokens_chatbot(cls,text):
        """Static method to track lifetime token count of chatbot. If lifetime token limit in config.py is exceeded, exits app.
        Args:
            text: Text that will be tokenized, and thus its token count must be added to lifetime tokens of chatbot.
        """

        numOfTokens = TokenTracker.getTokenCount(text)
        TokenTracker.lifetimeTokens_chatbot += numOfTokens
        print("Lifetime tokens of chatbot: " + str(TokenTracker.lifetimeTokens_chatbot))
        if TokenTracker.lifetimeTokens_chatbot > config.lifetimeTokenLimit_chatbot:
            print("Hit Lifetime token limit of chatbot. Exiting!")
            exit()


    @staticmethod
    def getTokenCount(text) -> int:
        """Gets number of tokens that a given string will be split into.
        Args:
            text: the string to check
        Returns:
            (int) The number of tokens in the text.
        """

        import tiktoken
        tokenizer = tiktoken.encoding_for_model(config.embeddingModel)
        tokens = tokenizer.encode(text)
        num_tokens = len(tokens)
        return num_tokens