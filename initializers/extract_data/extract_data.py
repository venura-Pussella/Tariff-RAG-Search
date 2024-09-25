import os

def isEmpty(string):
    if string == "" or string == None:
        return True
    return False

def savePDFToJSON(filepath) -> None:

    # Create an 'enum' for header (column) numbering of the dataframe
    # ......................................... #
    keys = ["HS Hdg", 
            "HS Code", 
            "Blank",
            "Description", 
            "Unit",
            "ICL/SLSI",
            "Preferential Duty_AP",
            "Preferential Duty_AD",
            "Preferential Duty_BN",
            "Preferential Duty_GT",
            "Preferential Duty_IN",
            "Preferential Duty_PK",
            "Preferential Duty_SA",
            "Preferential Duty_SF",
            "Preferential Duty_SD",
            "Preferential Duty_SG",
            "Gen Duty",
            "VAT",
            "PAL_Gen",
            "PAL_SG",
            "Cess_GEN",
            "Cess_SG",
            "Excise SPD",
            "SSCL",
            "SCL"]
    values = list(range(0,25))
    headerNumber = dict(zip(keys, values))
    # ......................................... #


    # use pdf plumber to extract the data from the pdfs
    # ......................................... #
    import pdfplumber

    allText = []
    rows = []
    tableReached = False

    pdf = pdfplumber.open(filepath)

    for page in pdf.pages:
        if tableReached: # if table has already been reached, continue to extract table, no need to find more text due to the document structure having all required text before the table
            rowsPerPage = page.extract_table()
            for row in rowsPerPage:
                rows.append(row)
            continue

        tableInPage = page.find_table()
        if tableInPage == None: # if no table found, extract text from whole page
            textPerPage = page.extract_text()
            allText.append(textPerPage)
        else: # else extract text from the part above the table, and start extracting the table
            tableBBox = tableInPage.bbox
            tableTop = tableBBox[1] # top value is 2nd value of bounding box tuple
            croppedPage = page.within_bbox((0,0,page.width,tableTop)) # bounding box tuple order: left, top, right, bottom
            textPerPage = croppedPage.extract_text()
            allText.append(textPerPage)
            tableReached = True
            rowsPerPage = page.extract_table()
            for row in rowsPerPage:
                rows.append(row)

    pdf.close()

    import pandas as pd
    df = pd.DataFrame(rows)
    # ......................................... #


    # isolate chapter number and name
    # ......................................... #
    firstLineEndIndex = allText[0].find('\n')
    chapterNumber = int(allText[0][7:firstLineEndIndex])
    startOfNotesIndex = allText[0].find('Notes.')
    if startOfNotesIndex == -1:
        startOfNotesIndex = allText[0].find('Note.')
    chapterName = allText[0][firstLineEndIndex+1:startOfNotesIndex]
    chapterName = chapterName.replace("\n"," ")
    # ......................................... #


    # create a dictionary for creating a json for the whole pdf
    # ......................................... #
    dictionaryForThisPDF = dict.fromkeys(["Chapter Number", "Chapter Name", "Pre-Table Notes", "Items"])

    dictionaryForThisPDF["Chapter Number"] = chapterNumber
    dictionaryForThisPDF["Chapter Name"] = chapterName
    preTableNotes = ""
    for text in allText:
        preTableNotes += text
    dictionaryForThisPDF["Pre-Table Notes"] = preTableNotes
    # ......................................... #

    import json


    # extract useful items with HS codes from the table
    # ......................................... #
    ongoing_prefix = ""
    ongoing_hshdgname = ""
    ongoing_hshdg = ""
    numOfColumns = df.shape[1]
    if numOfColumns == 25:
        keysForAnItem = ["Prefix", "HS Hdg Name","HS Hdg","HS Code","Blank", "Description", "Unit","ICL/SLSI","Preferential Duty_AP","Preferential Duty_AD","Preferential Duty_BN","Preferential Duty_GT","Preferential Duty_IN","Preferential Duty_PK","Preferential Duty_SA","Preferential Duty_SF","Preferential Duty_SD","Preferential Duty_SG","Gen Duty","VAT","PAL_Gen","PAL_SG","Cess_GEN","Cess_SG","Excise SPD","SSCL","SCL"]
    else:
        keysForAnItem = ["Prefix", "HS Hdg Name","HS Hdg","HS Code","Blank", "Description", "Unit","ICL/SLSI","Preferential Duty_AP","Preferential Duty_AD","Preferential Duty_BN","Preferential Duty_GT","Preferential Duty_IN","Preferential Duty_PK","Preferential Duty_SA","Preferential Duty_SF","Preferential Duty_SD","Preferential Duty_SG","Gen Duty","VAT","PAL_Gen","PAL_SG","Cess_GEN","Excise SPD","SSCL","SCL"]
    items = []

    numOfRows = df.shape[0] # rows
    # only a row with a non-null unit will be considered a valid item
    for n in range(3,numOfRows):
        current_hshdg = df.loc[n].values[headerNumber['HS Hdg']]
        current_hscode = df.loc[n].values[headerNumber['HS Code']]
        current_description = df.loc[n].values[headerNumber['Description']]
        current_unit = df.loc[n].values[headerNumber['Unit']]

        if isEmpty(current_description) or (current_hshdg == "HS Hdg") or (current_hshdg == None): # row is considered empty
            continue
        if isEmpty(current_hshdg) and isEmpty(current_unit): # description considered a prefix
            ongoing_prefix = current_description
            continue
        if (not isEmpty(current_hshdg)) and isEmpty(current_hscode): # row has a HS Hdg no. and no HS code no.
            ongoing_hshdg = current_hshdg
            ongoing_hshdgname = current_description
            ongoing_prefix = "" # reset on-going prefix since we have moved to a new hs hdg
            if isEmpty(current_unit): #not an item
                continue
            else:
                current_hscode = current_hshdg # becomes a valid item
        if not isEmpty(current_unit): # this is a valid item
            # create a json item
            values = [ongoing_prefix] + [ongoing_hshdgname] + list(df.loc[n].values)
            item = dict(zip(keysForAnItem, values))
            item.pop('Blank',item['Blank'])
            item['HS Hdg'] = ongoing_hshdg
            item['HS Code'] = current_hscode # in case this is an item that has a hs hdg, but no declared hs code
            if numOfColumns == 24:
                item["Cess_SG"] = ''
            items.append(item)

            #if description contains "other", reset prefix
            current_description_uppercase = current_description.upper()
            if "OTHER" in current_description_uppercase:
                ongoing_prefix = "" # reset on-going prefix since we have reached "other" description
            
    # ......................................... #
        

    # create the finalized json dictionary and save as .json
    # ......................................... #
    dictionaryForThisPDF["Items"] = items


    json_string = json.dumps(dictionaryForThisPDF)
    with open('initializers\extract_data\extracted_data\{}.json'.format(chapterNumber),'w') as file:
        file.write(json_string)

    # ......................................... #


filepath = 'Tariff_PDFs'

for filename in os.listdir(filepath):
    f = os.path.join(filepath, filename)
    if os.path.isfile(f):
        print("Reading "+f)
        savePDFToJSON(f)

print("Data extracted from tariff pdfs and saved as .json")