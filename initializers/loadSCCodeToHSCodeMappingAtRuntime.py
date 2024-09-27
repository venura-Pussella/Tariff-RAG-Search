def getSCCodeToHSCodeMapping() -> dict[str,list[str]]:
    """Retrieves SCCode to HSCode mapping from the filepath defined inside the function.
    Returns:
        dictionary with key as SCCode and value as python list of HSCodes
    """
    
    import csv

    csv_file = 'initializers/extract_data/SCCode_HSCode_Mapping Sorted.csv'
    rows = []

    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)

        for row in csv_reader:
            rows.append(row)

    scToHSMapping = {}

    for n in range(1,len(rows)):
        row = rows[n]
        currentHSCode = row[0]
        currentSCCode = row[1]
        if currentSCCode in scToHSMapping:
            scToHSMapping[currentSCCode].append(currentHSCode)
        else:
            scToHSMapping[currentSCCode] = [currentHSCode]
    
    if not bool(scToHSMapping): print("WARNING: SC Code to HS Code dictionary is empty!")

    return scToHSMapping