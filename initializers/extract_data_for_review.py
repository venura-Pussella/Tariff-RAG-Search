# This file has only one public function - convertPDFToExcelForReview
# It is used to do most of the uploadPDF stage, as mentioned in the developer guide in section 3.1.3

from io import BytesIO
import logging
import pickle

import pdfplumber
import pandas as pd


def __removeNewLineCharactersFromDataframe(dataframe):
    """Removes new line character ('\n') from the dataframe. Done in place. Returns void.
    """
    numOfRows = dataframe.shape[0]
    numOfCols = dataframe.shape[1]
    for r in range(0,numOfRows):
        for c in range(0,numOfCols):
            if dataframe.iloc[r,c] == None: continue
            dataframe.iloc[r,c] = dataframe.iloc[r,c].replace('\n',' ')
    
def __isSeriesALineItem(series, numOfColumns) -> bool:
    """Checks if a dataframe row (i.e. a series), qualifies as a line item (i.e. has values from the unit column onwards)"""
    for col in range(4,numOfColumns):
        value = series.iloc[col]
        if not __isEmpty(value): return True
    return False

def __getDataframeHeadernameToColumnNumberMapping() -> dict[str,int]:
    """Returns a dictionary mapping an easy to use column name for the dataframe, with its corresponsing column number.
    """
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
    return dict(zip(keys, values))

def __isEmpty(string) -> bool:
    """ Returns true if the given string is '' or None
    """
    if string == "" or string == None:
        return True
    return False

def __standardizeHSCode(hscode: str) -> str:
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
        hscode = hscode.replace('.','')
        hscode += '.00.00N'
    else:
        raise ValueError("HS Code of unknown format passed in: {}".format(hscode))
    return hscode

def __extractTableAndTextFromPDF(file: BytesIO) -> tuple[pd.DataFrame,list[str]]:
    """Extracts the table from the tariff PDF and the text that comes before the table.

    Uses pdf plumber to extract the data from the pdfs
    All the text that comes before the table are saved in the allText array (one item is a page)
    The table is converted into a pandas dataframe (as-is, not processed to remove empty rows, etc.)

    Args:
        file (BytesIO): the PDF file

    Returns:
        tuple[pd.DataFrame,list[str]]: table as pandas dataframe, text (one item is a page)
    """
    allText = []
    rows = []
    tableReached = False

    pdf = pdfplumber.open(file)

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

    
    df = pd.DataFrame(rows)

    return df, allText

def __extractTableAndTextFromPDFNonStrictly(file: BytesIO):
    """Extracts the table from the tariff PDF and text on the first page.

    Uses pdf plumber to extract the data from the pdfs
    The text of the first page is saved in the allText array (one item is a page)
    The table is converted into a pandas dataframe (as-is, not processed to remove empty rows, etc.)

    Args:
        file (BytesIO): the PDF file

    Returns:
        tuple[pd.DataFrame,list[str]]: table as pandas dataframe, text (one item is a page)
    """

    allText = []
    rows = []

    pdf = pdfplumber.open(file)

    allText.append(pdf.pages[0].extract_text())

    for page in pdf.pages:
        rowsPerPage = page.extract_table()
        if rowsPerPage == None: continue
        for row in rowsPerPage:
            rows.append(row)

    pdf.close()

    df = pd.DataFrame(rows)

    return df, allText

def __get_excel_and_dictionary_from_pdf(file: BytesIO, userEnteredChapterNumber: int = None, filename: str = None, strict=True) -> tuple[BytesIO,BytesIO,int]:
    """Data is ripped from the PDF to excel (and a dictionary), so that user will eventually review the excel.

    The text and other data (basically data other than the table), are saved to a dictionary as a pickle binary.
    The table which is extracted as a pandas dataframe is extracted in the form of an excel file, for easy reviewing and editing.
    Args:
        file (BytesIO): the pdf file
        userEnteredChapterNumber (int, optional): If availalbe, used to verify is this matches the chapter number in the PDF. Defaults to None.
        filename (str, optional): If available, used to handle cases where the chapter number extraction of the PDF must be hardcoded due to issues in the PDF. Defaults to None.
        strict (bool, optional): whether to use strict extraction. If strict is not used, parts of the first bit of the table in the pdf may end up in the pre-table-notes section of the dictionary.. Defaults to True.

    Raises:
        Exception: 'User entered chapter number does not match that of the PDF'

    Returns:
        tuple[BytesIO,BytesIO,int]: dictionary pickle, excel, chapter number
    """   
    headerNumber = __getDataframeHeadernameToColumnNumberMapping()

    if strict:
        df, allText = __extractTableAndTextFromPDF(file)
    else:
        df, allText = __extractTableAndTextFromPDFNonStrictly(file) 
    __removeNewLineCharactersFromDataframe(df)
    # isolate chapter number and name from the PDF text
    # ......................................... #
    firstLineEndIndex = allText[0].find('\n')
    try:
        if filename[-12:] == "63 Final.pdf" or filename[-6:] == "63.pdf": # hard-coded cuz isolated issue with this pdf, been unable to get the chapter number
            chapterNumber = 63
        elif filename[-12:] == "62 Final.pdf" or filename[-6:] == "62.pdf": chapterNumber = 62
        else:
            chapterNumber = int(allText[0][7:firstLineEndIndex])
    except IndexError: chapterNumber = int(allText[0][7:firstLineEndIndex])
    startOfNotesIndex = allText[0].find('Notes.')
    if startOfNotesIndex == -1:
        startOfNotesIndex = allText[0].find('Note.')
    chapterName = allText[0][firstLineEndIndex+1:startOfNotesIndex]
    chapterName = chapterName.replace("\n"," ")
    # ......................................... #
    if userEnteredChapterNumber:
        if chapterNumber != userEnteredChapterNumber:
            raise Exception('User entered chapter number does not match that of the PDF')
        
    if __suspect_unknown_column_header_schema(df): 
        logging.warning(f'An unknown column header schema is detected in chapter {chapterNumber} during PDF processing')
        logging.log(25,f'An unknown column header schema is detected in chapter {chapterNumber} during PDF processing')
    
    df['LineItem?'] = None  
   
    # create a dictionary for creating a json for the whole pdf
    # ......................................... #
    dictionaryForThisPDF = dict.fromkeys(["Chapter Number", "Chapter Name", "Pre-Table Notes", "Items"])

    dictionaryForThisPDF["Chapter Number"] = chapterNumber
    dictionaryForThisPDF["Chapter Name"] = chapterName
    preTableNotes = ""
    for text in allText:
        preTableNotes += text
    dictionaryForThisPDF["Pre-Table Notes"] = preTableNotes

    dictionary_stream = BytesIO()
    pickle.dump(dictionaryForThisPDF, dictionary_stream)
    dictionary_stream.seek(0)
    # ......................................... #

    
    # extract line items with HS codes from the table, only rows with a valid unit are considered to be a valid line item
    # ......................................... #
    ongoing_prefix = ""
    numOfColumns = df.shape[1]
    
    numOfRows = df.shape[0] # rows
    # only a row with a non-null unit will be considered a valid item
    for n in range(0,numOfRows): # starting from 3 because 0-2 are just table headers all over the place
        current_series = df.loc[n]
        current_hshdg = current_series.values[headerNumber['HS Hdg']]; 
        if current_hshdg == None: current_hshdg = ''
        current_hscode = current_series.values[headerNumber['HS Code']]
        if current_hscode == None: current_hscode = ''
        current_description = current_series.values[headerNumber['Description']]
        if current_description == None: current_description = ''

        if __isEmpty(current_description) or (current_hshdg == "HS Hdg"): # row is considered empty
            df.loc[n, 'LineItem?'] = 'empty'
            continue
        if __isEmpty(current_hshdg) and not __isSeriesALineItem(current_series, numOfColumns): # description considered a prefix
            df.loc[n, 'LineItem?'] = 'prefix'
            ongoing_prefix = current_description
            continue
        if (not __isEmpty(current_hshdg)) and not __isSeriesALineItem(current_series, numOfColumns): # row has a HS Hdg no. but no HS code no.
            df.loc[n, 'LineItem?'] = 'just HS heading'
            ongoing_prefix = "" # reset on-going prefix since we have moved to a new hs hdg
            if not __isSeriesALineItem(current_series, numOfColumns): # not an item
                continue
            else:
                current_hscode = current_hshdg # the hs.hdg is assigned to the hscode
        if (not __isEmpty(current_hshdg)) and __isSeriesALineItem(current_series, numOfColumns) and __isEmpty(current_hscode):
            current_hscode = current_hshdg
        if __isSeriesALineItem(current_series, numOfColumns): # this is a valid item
            # create a json item
            df.loc[n, 'LineItem?'] = 'line item'
            try: __standardizeHSCode(current_hscode)
            except Exception as e: 
                df.loc[n, 'LineItem?'] = 'hscode error'
                # logging.error("Exception occured at Hs hdg: " + current_hshdg + " current description: " + current_description + " prefix: " + ongoing_prefix)
                # logging.error(type(e))
                # logging.error(e)

            #if description contains "other", reset prefix
            current_description_uppercase = current_description.upper()
            if "OTHER" in current_description_uppercase:
                ongoing_prefix = "" # reset on-going prefix since we have reached "other" description
    excel_stream = BytesIO()
    df.to_excel(excel_stream, engine='openpyxl')
    excel_stream.seek(0)
    return (dictionary_stream, excel_stream, chapterNumber)
         
def convertPDFToExcelForReview(file: BytesIO, userEnteredChapterNumber: int = None, filename: str = None) -> tuple[BytesIO,BytesIO,int]:
    """Converts the pdf to excel (and dictionary pickle). This is done so the user can review the data extraction process.

    Args:
        file (BytesIO): _description_
        userEnteredChapterNumber (int, optional): Optionally used for validation. Defaults to None.
        filename (str, optional): Used for hardcoding in cases where the chapter number cannot be extracted from the top of the PDF because of pdf structure/identification issues. Defaults to None.

    Returns:
        tuple[BytesIO,BytesIO,int]: dictionary pickle, excel, chapter number
    """
    results = None
    try: results = __get_excel_and_dictionary_from_pdf(file, userEnteredChapterNumber, filename)
    except Exception as e:
        logging.warning("Error processing file " + filename + " Error: " + str(type(e)) + ": " + str(e) + '\nWill try using non-strict extraction')
        try: results = __get_excel_and_dictionary_from_pdf(file,userEnteredChapterNumber,filename, strict=False)
        except Exception as e:
            logging.error("Error processing file non-strictly " + filename + " Error: " + str(type(e)) + ": " + str(e))
            return None,None,None
    return results

def __suspect_unknown_column_header_schema(dataframe: pd.DataFrame) -> bool:
    """The indirect approach seen in the implementation is used because reading the column headers from the extracted table is unreliable 
    (sometimes the text is written vertically) causing incorrect text to be extraced, etc.
    So this method may not always pick up an new column header scheme (i.e. can have true negatives), but will never have false positives.

    Args:
        dataframe (pd.DataFrame): _description_

    Returns:
        bool: True if we suspect an unknown column header scheme
    """

    try:
        # Find the first row where the first column value is 'HS Hdg' (sometimes pre-table text may appear on the first few rows)
        # Then get the values from the 2 header rows
        top_row_index = dataframe[dataframe.iloc[:, 0] == 'HS Hdg'].index[0]
        bottom_row_index = top_row_index + 1
        top_row_values = dataframe.iloc[top_row_index].tolist()
        bottom_row_values = dataframe.iloc[bottom_row_index].tolist()

        # due to PDF inconsistencies and things like vertical text, directly reading the values is unreliable (incorrect text maybe extracted)
        # Therefore we just make an estimate based on common structure

        # top_row_values index 0 and 1 should contain 'HS', 2 should be blank, 3 is 'Description', 4 is 'Unit', 5 is too unreliable to read so skip
        # corresponding bottom_row_values values should be blank (skip 5 cuz ICL/SLSI may leak down)
        if 'HS' not in top_row_values[0] or 'HS' not in top_row_values[1] or 'Description' not in top_row_values[3] or 'Unit' not in top_row_values[4]: return True
        if top_row_values[2] != None:
            if top_row_values[2].rstrip() != '': return True
        for i in range(0,5):
            if bottom_row_values[i] != None:
                if bottom_row_values[i].rstrip() != '': return True

        # check the preferential duty column headers
        if 'Preferential' not in top_row_values[6]: return True
        for i in range(6,16):
            subheaders = ['AP','AD','BN','GT','IN','PK','SA','SF','SD','SG']
            if bottom_row_values[i] == None: return True
            if bottom_row_values[i].rstrip() != subheaders[i-6]: return True
        for i in range(7,16):
            if top_row_values[i] != None:
                if top_row_values[i].rstrip() != '': return True

        # check Gen Duty, VAT, PAL_Gen, PAL_SG column headers
        if 'Gen' not in top_row_values[16] or 'VAT' not in top_row_values[17] or 'PAL' not in top_row_values[18] or 'Gen' not in bottom_row_values[18] or 'SG' not in bottom_row_values[19]: return True
        if top_row_values[19] != None:
            if top_row_values[19].rstrip() != '': return True
        if bottom_row_values[16] != None:
            if bottom_row_values[16].rstrip() != '': return True
        if bottom_row_values[17] != None:
            if bottom_row_values[17].rstrip() != '': return True

        # some tables only have 'cess' while others have 'cess_gen' and 'cess_sg'
        if top_row_values[21] == '' or top_row_values[21] == None: next_col = 22
        else: next_col = 21
        if 'Cess' not in top_row_values[20]: return True

        # You can have either just excise, just surcharge, or both - but if there're both, surcharge comes after excise in the column order
        if 'Excise' in top_row_values[next_col] and 'Surcharge' in top_row_values[next_col + 1]: next_col += 2
        elif 'Excise' in top_row_values[next_col]: next_col += 1
        elif 'Surcharge' in top_row_values[next_col]: next_col += 1
        else: return True

        # final 2 columns (SSCL and SCL) are too unreliable to be checked (often printed vertically). But cannot have any more columns more than that.
        scl_index = next_col + 1
        if len(top_row_values) > scl_index + 1: return True

        return False

    except TypeError: return True # happens if a cell we expect not to be blank is blank 
    # eg: if 'HS' not in top_row_values[0] <- if top_row_values[0] is None, TypeError will be raised


