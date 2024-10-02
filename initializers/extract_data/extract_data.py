# SCRIPT

# Extracts data from the tariff PDFs, converts them into line items and stores them as .json files
# One .json file per PDF, it includes metadata about the chapter, and an array of line items as json objects

import os


def isEmpty(string) -> bool:
    """ Returns true if the given string is '' or None
    """
    if string == "" or string == None:
        return True
    return False



def getHSCodeToSCCodeMapping() -> dict[str,str]:
    """Retrieves HSCode to SCCode mapping from the filepath defined inside the function.
    Returns:
        dictionary with key as HSCode and value as SCCode
    """
    
    import csv

    csv_file = 'initializers/extract_data/SCCode_HSCode_Mapping Sorted.csv'
    rows = []

    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        csv_reader = csv.reader(file)

        for row in csv_reader:
            rows.append(row)

    # HS Code format: ####.##.##N

    hsToSCMapping = {}

    for n in range(1,len(rows)):
        row = rows[n]
        key = row[0]
        value = row[1]
        hsToSCMapping[key] = value
    
    if not bool(hsToSCMapping): print("WARNING: HS Code to SC Code dictionary is empty!")

    return hsToSCMapping



def standardizeHSCode(hscode) -> str:
    """ Changes hscodes of the various known formats into a standardized format '####.##.##N'

    Args:
        hscode: (str) The HS Code to be standardized
    Returns:
        Standardized HS Code (str)
    Raises:
        ValueError - if HS Code of unknown format is passed in.
    """
    if len(hscode) == 7: # eg: '8202.10'
        hscode += '.00N'
    elif len(hscode) == 10: # eg: '8202.10.20'
        hscode += 'N'
    elif len(hscode) == 5: # eg: '28.03'
        hscode += '.00.00N'
    else:
        raise ValueError("HS Code of unknown format passed in: {}".format(hscode))
    return hscode

def extractTableAndTextFromPDF(filepath):
    """Extracts table and pre-table text from the pdf given in the filepath.
    #### Discussion:
        Use pdf plumber to extract the data from the pdfs
    All the text that comes before the table are saved in the allText array (one item is a page)
    The table is converted into a pandas dataframe (as-is, not processed to remove empty rows, etc.)
    Args:
        filepath: filepath with the pdf
    Returns:
        df: Pandas dataframe containing the table 
        
        allText: list[str] containing the textual data that comes before the table

    """
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

    return df, allText

def extractTableAndTextFromPDFNonStrictly(filepath):
    """Extracts table and pre-table text from the pdf given in the filepath.
    #### Discussion:
        Use pdf plumber to extract the data from the pdfs
    All the text that comes before the table are saved in the allText array (one item is a page)
    The table is converted into a pandas dataframe (as-is, not processed to remove empty rows, etc.)
    Args:
        filepath: filepath with the pdf
    Returns:
        df: Pandas dataframe containing the table 
        
        allText: list[str] containing the textual data that comes before the table

    """
    import pdfplumber

    allText = []
    rows = []

    pdf = pdfplumber.open(filepath)

    allText.append(pdf.pages[0].extract_text())

    for page in pdf.pages:
        rowsPerPage = page.extract_table()
        if rowsPerPage == None: continue
        for row in rowsPerPage:
            rows.append(row)

    pdf.close()

    import pandas as pd
    df = pd.DataFrame(rows)

    return df, allText

def savePDFToJSON(filepath,strict=True):
    """ Reads a single pdf file from the specified filepath, and saves it as a .json in the location defined inside the function. Also saves the SCCode to HSCode mapping dictionary to disk.
    Args:
        filepath: filepath to the pdf (str)
        strict: If true extracts text by strictly checking for table dimensions, to identify the part of the document before the table,
            If false, just extracts text from the first page.
    """

    # Create an 'enum' that matches a column name with the matching column number in the dataframe
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


    hsToSCMapping = getHSCodeToSCCodeMapping()


    if strict:
        df, allText = extractTableAndTextFromPDF(filepath)
    else:
        df, allText = extractTableAndTextFromPDFNonStrictly(filepath)



    # isolate chapter number and name
    # ......................................... #
    firstLineEndIndex = allText[0].find('\n')
    if filepath[-12:] == "63 Final.pdf":
        chapterNumber = 63
    else:
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


    # extract line items with HS codes from the table, only rows with a valid unit are considered to be a valid line item
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
    for n in range(3,numOfRows): # starting from 3 because 0-2 are just table headers all over the place
        current_hshdg = df.loc[n].values[headerNumber['HS Hdg']]
        current_hscode = df.loc[n].values[headerNumber['HS Code']]
        current_description = df.loc[n].values[headerNumber['Description']]
        current_unit = df.loc[n].values[headerNumber['Unit']]

        if isEmpty(current_description) or (current_hshdg == "HS Hdg") or (current_hshdg == None): # row is considered empty
            continue
        if isEmpty(current_hshdg) and isEmpty(current_unit): # description considered a prefix
            ongoing_prefix = current_description
            continue
        if (not isEmpty(current_hshdg)) and isEmpty(current_hscode): # row has a HS Hdg no. but no HS code no.
            ongoing_hshdg = current_hshdg
            ongoing_hshdgname = current_description
            ongoing_prefix = "" # reset on-going prefix since we have moved to a new hs hdg
            if isEmpty(current_unit): # not an item
                continue
            else:
                current_hscode = current_hshdg # the hs.hdg is assigned to the hscode
        if not isEmpty(current_unit): # this is a valid item
            # create a json item
            values = [ongoing_prefix] + [ongoing_hshdgname] + list(df.loc[n].values)
            item = dict(zip(keysForAnItem, values))
            item.pop('Blank',item['Blank'])
            item['HS Hdg'] = ongoing_hshdg
            try: standardizedHSCode = standardizeHSCode(current_hscode)
            except Exception as e: 
                standardizedHSCode = current_hscode
                print(e)
                print("Exception occured at Hs hdg: " + current_hshdg + " current description: " + current_description + " prefix: " + ongoing_prefix)
            item['HS Code'] =  standardizedHSCode# this value will be added explicitly in case this is an item that has a hs hdg, but no declared hs code

            standardizedHSCode2 = standardizedHSCode[:-3] + "00N"
            standardizedHSCode3 = standardizedHSCode2[:-6]+"00.00N"
            if standardizedHSCode in hsToSCMapping:
                item['SC Code'] = hsToSCMapping[standardizedHSCode]
            elif standardizedHSCode2 in hsToSCMapping:
                item['SC Code'] = hsToSCMapping[standardizedHSCode2]
            elif standardizedHSCode3 in hsToSCMapping:
                item['SC Code'] = hsToSCMapping[standardizedHSCode3]
            else:
                item['SC Code'] = ''
            if numOfColumns == 24: # some pdf tables don't have a cess column split into GEN and SG
                item["Cess_SG"] = ''
            items.append(item)

            if item['SC Code'] == '':
                pass
            elif item['SC Code'] in scCodeToHSCodeMapping:
                scCodeToHSCodeMapping[item['SC Code']].append(item['HS Code'])
            else:
                scCodeToHSCodeMapping[item['SC Code']] = [item['HS Code']]

            #if description contains "other", reset prefix
            current_description_uppercase = current_description.upper()
            if "OTHER" in current_description_uppercase:
                ongoing_prefix = "" # reset on-going prefix since we have reached "other" description
            
    # ......................................... #
        

    # create the finalized json dictionary and save as .json
    # ......................................... #
    dictionaryForThisPDF["Items"] = items


    json_string = json.dumps(dictionaryForThisPDF)
    with open('initializers/extract_data/extracted_data/{}.json'.format(chapterNumber),'w') as file:
        file.write(json_string)

    # ......................................... #




# SCRIPT
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

filepathWithPDFs = 'Tariff_PDFs'
scCodeToHSCodeMapping = {}

for filename in os.listdir(filepathWithPDFs):
    f = os.path.join(filepathWithPDFs, filename)
    if os.path.isfile(f):
        print("Reading "+f)
        try: savePDFToJSON(f)
        except Exception as e:
            print("Error processing file @ " + f + " Error: " + str(e))
            # tb = traceback.format_exc()
            # print("traceback:")
            # print(tb)
            print("Using non-strict extraction")
            try: savePDFToJSON(f,strict=False)
            except Exception as e:
                print("Error processing file non-strictly @ " + f + " Error: " + str(e))
                # tb = traceback.format_exc()
                # print("traceback:")
                # print(tb)
            

print("Data extracted from tariff pdfs and saved as .json")


import pickle 

with open('initializers/extract_data/scCodeToHSCodeMapping.pkl', 'wb') as f:
    pickle.dump(scCodeToHSCodeMapping, f)
print("SCCode to HSCode dictionary saved as binary.")

