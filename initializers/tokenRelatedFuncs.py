def getTokenCount(text) -> int:
    """Gets number of tokens that a given string will be split into.
    Args:
        text: the string to check
    Returns:
        (int) The number of tokens in the text.
    """

    import tiktoken
    tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")
    tokens = tokenizer.encode(text)
    num_tokens = len(tokens)
    return num_tokens