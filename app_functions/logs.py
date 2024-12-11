import log_handling

def generate_array_for_log_tablerows():
    tableRows: list[list[str]] = []
    for log in log_handling.log_messages:
        log = log[1:-1] # get rid of the square brackets surrounding the log message
        splits = log.rsplit(':')
        timestamp = splits[0] + splits[1] + splits[2]
        level = splits[3]
        module = splits[4]
        message = ''
        for remaining in splits[5:]:
            message += remaining + ':'
        message = message[:-1] # get rid of last colon
        row = [timestamp, level, module, message]
        tableRows.append(row)
    return tableRows

def get_filtered_logs(tableRows: list[list[str]], filter: str) -> list[list[str]]:
    filtered_tableRows = []
    filters = ['DEBUG', 'LLM', 'INFO', 'USER', 'WARNING', 'ERROR']
    if filter == 'Debug': pass
    elif filter == 'LLM': filters = filters[1:]
    elif filter == 'Info': filters = filters[2:]
    elif filter == 'User': filters = filters[3:]
    elif filter == 'Warning': filters = filters[4:]
    else: filters = filters[5:]
    for row in tableRows:
        level = row[1].strip() # lol this is actually needed
        if level in filters: 
            filtered_tableRows.append(row)
    return filtered_tableRows