class TokenTracker:
    """Static class.
    Static attribute:
        lifetimeTokens: Used to track lifetime tokens.
    Static method:
        updateTokens: Used to track lifetime tokens, if limit is hit, app exits.
    """

    lifetimeTokens = 0

    @classmethod
    def updateTokens(self,text):
        """Static method to track lifetime token count. If lifetime token limit in config.py is exceeded, exits app.
        Args:
            text: Text that will be tokenized, and thus its token count must be added to lifetime tokens.
        """
        from initializers import tokenRelatedFuncs
        import config
        numOfTokens = tokenRelatedFuncs.getTokenCount(text)
        TokenTracker.lifetimeTokens += numOfTokens
        print("Lifetime tokens: " + str(TokenTracker.lifetimeTokens))
        if TokenTracker.lifetimeTokens > config.lifetimeTokenLimit:
            print("Hit Lifetime token limit. Exiting!")
            exit()