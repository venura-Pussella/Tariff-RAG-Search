import pandas as pd
import json
import pickle 
from data_stores.DataStores import DataStores
import config
import os
from data_stores.DataStores import DataStores as ds
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from data_stores.AzureTableObjects import AzureTableObjects as ato


def getDataframeHeadernameToColumnNumberMapping() -> dict[str,int]:
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

def isEmpty(string) -> bool:
    """ Returns true if the given string is '' or None
    """
    if string == "" or string == None:
        return True
    return False

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
        errorText = "HS Code of unknown format passed in: {}".format(hscode)
        print(errorText)
        raise ValueError()
    return hscode
          
def doesHSCodeMatchChapterNumber(hscode: str, chapterNumber: int) -> bool:
    standardizedHSCode = standardizeHSCode(hscode)
    chapterNumberPart = standardizedHSCode[:2] # extract the chapter number part from the standardized hs code
    if int(chapterNumberPart) == chapterNumber: return True
    else: return False

def saveExcelAndDictToJSON2(excelFilePath, dictFilepath, targetPathForJSON, userEnteredChapterNumber: int) -> str:
    """ Reads a single excel file from the specified filepath (and the persisted corresponding pickle dictionary), 
    and saves it as a .json in the location defined inside the function. Also saves the SCCode to HSCode mapping dictionary to disk.
    ### Args:
        filepath: filepath to the pdf (str)
    """
    scCodeToHSCodeMapping = {} # this does nothing for now
    # Create an 'enum' that matches a column name with the matching column number in the dataframe
    # ......................................... #
    headerNumber = getDataframeHeadernameToColumnNumberMapping()
    # ......................................... #


    hsToSCMapping = DataStores.getHSCodeToSCCodeMapping()
   

    df = pd.read_excel(excelFilePath, na_filter=False, dtype=str)
    dictionaryForThisPDF = {}
    print(dictFilepath)
    with open(dictFilepath, 'rb') as f:
        dictionaryForThisPDF = pickle.load(f)


    del df[df.columns[0]]
    numOfColumns = df.shape[1]
    del df[df.columns[numOfColumns - 1]]

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

    def isSeriesALineItem(series, numOfColumns) -> bool:
        for col in range(4,numOfColumns):
            value = series.iloc[col]
            if not isEmpty(value): return True
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

        if isEmpty(current_description) or (current_hshdg == "HS Hdg"): # row is considered empty
            continue
        if isEmpty(current_hshdg) and not isSeriesALineItem(current_series, numOfColumns): # description considered a prefix
            ongoing_prefix = current_description
            continue
        if (not isEmpty(current_hshdg)) and not isSeriesALineItem(current_series, numOfColumns): # row has a HS Hdg no. but no HS code no.
            ongoing_hshdg = current_hshdg
            ongoing_hshdgname = current_description
            ongoing_prefix = "" # reset on-going prefix since we have moved to a new hs hdg
            if not isSeriesALineItem(current_series, numOfColumns): # not an item
                continue
            else:
                current_hscode = current_hshdg # the hs.hdg is assigned to the hscode
        if (not isEmpty(current_hshdg)) and isSeriesALineItem(current_series, numOfColumns) and isEmpty(current_hscode):
            current_hscode = current_hshdg
        if isSeriesALineItem(current_series, numOfColumns) and not isEmpty(current_hscode): # this is a valid item
            # create a json item
            values = [ongoing_prefix] + [ongoing_hshdgname] + list(df.loc[n].values)
            item = dict(zip(keysForAnItem, values))
            item.pop('Blank',item['Blank'])
            item['HS Hdg'] = ongoing_hshdg
            try: standardizedHSCode = standardizeHSCode(current_hscode)
            except Exception as e: 
                standardizedHSCode = current_hscode
                print(current_hscode)
                print("Exception occured at Hs hdg: " + current_hshdg + " current description: " + current_description + " prefix: " + ongoing_prefix)
                print(type(e))
                print(e)
                continue # skip this row
            item['HS Code'] =  standardizedHSCode# this value will be added explicitly in case this is an item that has a hs hdg, but no declared hs code

            if not doesHSCodeMatchChapterNumber(current_hscode, userEnteredChapterNumber):
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
    with open(targetPathForJSON,'w') as file:
        file.write(json_string)

    return json_string
    # ......................................... #

def extract_data_to_json_store(chapterNumber: int, excelFilepath: str, mutexKey: str) -> bool:
    dictFileName = str(chapterNumber) + '.pkl'
    dictPath = config.temp_folderpath_for_reviewed_data + dictFileName
    abo.download_blob_file(dictFileName, config.generatedDict_container_name, dictPath)
    jsonPath = config.temp_folderpath_for_reviewed_data + str(chapterNumber) + '.json'
    try:
        json_string = saveExcelAndDictToJSON2(excelFilepath,dictPath,jsonPath, chapterNumber)
    except Exception as e:
        print(e)
        os.remove(dictPath)
        os.remove(excelFilepath)
        return False

    print("Excel converted to json.")
    abo.upload_blob_file(excelFilepath, config.reviewedExcel_container_name) # Excel uploaded to Azure blob
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.uploadedCorrectedExcel)
    print('Excel @ ' + excelFilepath + ' successfully uploaded')
    os.remove(dictPath)
    os.remove(excelFilepath)
    abo.upload_blob_file(jsonPath,config.json_container_name)
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.uploadedJson)
    ds.insertNewJSONDictManually(json_string, int(chapterNumber))
    os.remove(jsonPath)
    print("Uploaded json")
    return True