# This file only has one public method - extract_data_to_json_store

import json
import logging
import pickle 
from io import BytesIO

import pandas as pd

from data_stores.DataStores import DataStores
import config
from data_stores.DataStores import DataStores as ds
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from data_stores.AzureTableObjects import AzureTableObjects as ato



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
        errorText = "HS Code of unknown format passed in: {}".format(hscode)
        logging.error(errorText)
        raise ValueError()
    return hscode
          
def __doesHSCodeMatchChapterNumber(hscode: str, chapterNumber: int) -> bool:
    standardizedHSCode = __standardizeHSCode(hscode)
    chapterNumberPart = standardizedHSCode[:2] # extract the chapter number part from the standardized hs code
    if int(chapterNumberPart) == chapterNumber: return True
    else: return False

def __saveExcelAndDictToJSON2(excelFile: BytesIO, dictStream: BytesIO, chapterNumber: int) -> str:
    """ Reads a single excel file from the specified filepath (and the persisted corresponding pickle dictionary), 
    and saves it as a .json in the location defined inside the function. Also saves the SCCode to HSCode mapping dictionary to disk.
    ### Args:
        filepath: filepath to the pdf (str)
    """
    scCodeToHSCodeMapping = {} # this does nothing for now
    # Create an 'enum' that matches a column name with the matching column number in the dataframe
    # ......................................... #
    headerNumber = __getDataframeHeadernameToColumnNumberMapping()
    # ......................................... #


    hsToSCMapping = DataStores.getHSCodeToSCCodeMapping()
   

    df = pd.read_excel(excelFile, na_filter=False, dtype=str)
    dictionaryForThisPDF: dict = pickle.load(dictStream)

    # drop first and last columns (first column is just pandas row numbers, and last column is my 'LineItem?' column)
    del df[df.columns[0]]
    numOfColumns = df.shape[1]
    del df[df.columns[numOfColumns - 1]]

    # extract line items with HS codes from the table, only rows with a valid unit are considered to be a valid line item
    # ......................................... #
    ongoing_prefix = ""
    ongoing_hshdgname = ""
    ongoing_hshdg = ""
    numOfColumns = df.shape[1]
    keysForAnItem = __get_keysForAnItem(df)
    items = []

    def isSeriesALineItem(series, numOfColumns) -> bool:
        for col in range(4,numOfColumns):
            value = series.iloc[col]
            if not __isEmpty(value): return True
        return False

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
            continue
        if __isEmpty(current_hshdg) and not isSeriesALineItem(current_series, numOfColumns): # description considered a prefix
            ongoing_prefix = current_description
            continue
        if (not __isEmpty(current_hshdg)) and not isSeriesALineItem(current_series, numOfColumns): # row has a HS Hdg no. but no HS code no.
            ongoing_hshdg = current_hshdg
            ongoing_hshdgname = current_description
            ongoing_prefix = "" # reset on-going prefix since we have moved to a new hs hdg
            if not isSeriesALineItem(current_series, numOfColumns): # not an item
                continue
            else:
                current_hscode = current_hshdg # the hs.hdg is assigned to the hscode
        if (not __isEmpty(current_hshdg)) and isSeriesALineItem(current_series, numOfColumns) and __isEmpty(current_hscode):
            current_hscode = current_hshdg
        if isSeriesALineItem(current_series, numOfColumns) and not __isEmpty(current_hscode): # this is a valid item
            # create a json item
            values = [ongoing_prefix] + [ongoing_hshdgname] + list(df.loc[n].values)
            item = dict(zip(keysForAnItem, values))
            item.pop('Blank',item['Blank'])
            item['HS Hdg'] = ongoing_hshdg
            try: standardizedHSCode = __standardizeHSCode(current_hscode)
            except Exception as e: 
                standardizedHSCode = current_hscode
                logging.error(current_hscode)
                logging.error("Exception occured at Hs hdg: " + current_hshdg + " current description: " + current_description + " prefix: " + ongoing_prefix)
                logging.error(type(e))
                logging.error(e)
                continue # skip this row
            item['HS Code'] =  standardizedHSCode# this value will be added explicitly in case this is an item that has a hs hdg, but no declared hs code

            if not __doesHSCodeMatchChapterNumber(current_hscode, chapterNumber):
                raise Exception("User entered chapter number does not match at least one of the valid HS codes in the excel file")

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
            # if numOfColumns == 24: # some pdf tables don't have a cess column split into GEN and SG
            #     item["Cess_SG"] = ''
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
    return json_string
    # ......................................... #

def extract_data_to_json_store(excelfile: BytesIO, mutexKey: str, chapterNumber: int, release_date: str) -> bool:
    """Extracts data from a reviewed excel, and converts it to json and uploads releveant files to Azure Blob storage.

    Args:
        excelfile (BytesIO): _description_
        mutexKey (str): _description_
        chapterNumber (int): _description_
        release_date (str): _description_

    Returns:
        bool: if the process was successful
    """
    dictFileName = release_date + '/' + str(chapterNumber) + '.pkl'
    dictStream = abo.download_blob_file_to_stream(dictFileName, config.generatedDict_container_name)
    try:
        json_string = __saveExcelAndDictToJSON2(excelfile, dictStream, chapterNumber)
    except Exception as e:
        logging.error(e)
        return False

    json_stream = BytesIO(json_string.encode('utf-8')) 
    json_stream.seek(0); dictStream.seek(0); excelfile.seek(0)

    logging.info(f"Excel converted to json. (chapter {chapterNumber} of release {release_date})")
    ato.edit_entity(chapterNumber, mutexKey, release_date, newRecordStatus=config.RecordStatus.uploadingCorrectedExcel)
    abo.upload_to_blob_from_stream(excelfile, config.reviewedExcel_container_name,  f'{release_date}/{chapterNumber}.xlsx') # Excel uploaded to Azure blob
    logging.info('Excel @ ' + f'{release_date}/{chapterNumber}.xlsx' + ' successfully uploaded')
    ato.edit_entity(chapterNumber, mutexKey, release_date, newRecordStatus=config.RecordStatus.uploadingJson)
    abo.upload_to_blob_from_stream(json_stream, config.json_container_name,  f'{release_date}/{chapterNumber}.json') # Json uploaded to Azure blob
    ds.insertNewJSONDictManually(json_string, int(chapterNumber), release_date)
    logging.info(f"Uploaded json for chapternumber {chapterNumber} of release {release_date}")
    return True


def __get_keysForAnItem(_df: pd.DataFrame) -> list[str]:
    """Returns the dictionary keys for a given extracted table depending on its column headers.

    The indirect approach seen in the implementation is used because reading the column headers from the extracted table is unreliable 
    (sometimes the text is written vertically) causing incorrect text to be extraced, etc.

    Args:
        _df (pd.DataFrame): extracted table from the PDF

    Returns:
        _type_: _description_
    """

    # Find the first row where the first column value is 'HS Hdg' (sometimes pre-table text may appear on the first few rows)
    row_index = _df[_df.iloc[:, 0] == 'HS Hdg'].index[0]

    # Assert 'Cess' appears on the 20th column (0-indexing). No variation in headers till that point.
    keysForAnItem = ["Prefix", "HS Hdg Name","HS Hdg","HS Code","Blank", "Description", "Unit","ICL/SLSI","Preferential Duty_AP",
                     "Preferential Duty_AD","Preferential Duty_BN","Preferential Duty_GT","Preferential Duty_IN","Preferential Duty_PK","Preferential Duty_SA",
                     "Preferential Duty_SF","Preferential Duty_SD","Preferential Duty_SG","Gen Duty","VAT","PAL_Gen","PAL_SG"]
    
    # some tables only have 'cess' while others have 'cess_gen' and 'cess_sg'
    if _df.iloc[row_index,21] == '' or _df.iloc[row_index,21] == None: 
        keysForAnItem += ["Cess_GEN", "Cess_SG"]
        next_col = 22
    else: 
        keysForAnItem += ["Cess_GEN"]
        next_col = 21

    # You can have either just excise, just surcharge, or both - but if there're both, surcharge comes after excise in the column order
    if 'Excise' in _df.iloc[row_index,next_col] and 'Surcharge' in _df.iloc[row_index,next_col+1]: 
        keysForAnItem += ["Excise SPD","Surcharge on Customs Duty","SSCL","SCL"]
    elif 'Excise' in _df.iloc[row_index,next_col]:
        keysForAnItem += ["Excise SPD","SSCL","SCL"]
    elif 'Surcharge' in _df.iloc[row_index,next_col]:
        keysForAnItem += ["Surcharge on Customs Duty","SSCL","SCL"]

    return keysForAnItem
