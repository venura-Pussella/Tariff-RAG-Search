import os
import config
import secrets
from data_stores.AzureBlobObjects import AzureBlobObjects as ABO
from data_stores.AzureTableObjects import AzureTableObjects as ato
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from werkzeug.datastructures import FileStorage
from initializers import deletingFuncs as delf
from initializers import extract_data_for_review
from azure.core.exceptions import ResourceExistsError
from data_stores.AzureTableObjects import MutexError
import concurrent.futures
from io import BytesIO

def allowed_file(filename: str, extension: str) -> bool:
    """Checks if filename has allowed extension.
    Example: filename = '28.pdf', extension = 'pdf' will return true
    """
    actualExtension = filename.rsplit(".")[-1]
    return actualExtension == extension

def validateUpload(extension: str, file: FileStorage) -> str:
    """Checks if the document POSTed by the user matches the extension

    Args:
        extension (str): expected extension of the file user is expected to POST. eg: 'pdf'

    Returns:
        str: errors. Blank string if no error
    """
    
    errors = ''
    
    if file and not allowed_file(file.filename, extension):
        errors = f'File does not match extension {extension}'

    return errors

def generateArrayForTableRows() -> list[list[str]]:
    """Generates the list required to construct the dynamic table in the file management interface.
    The list contains lists representing items in a single table row (i.e. file names, and status)

    Returns:
        list[list[str]]: table rows
    """
    tableRows: list[list[str]] = []
    listOfPDFNames = ABO.getListOfFilenamesInContainer(config.pdf_container_name)
    listOfGeneratedExcelNames = ABO.getListOfFilenamesInContainer(config.generatedExcel_container_name)
    listOfReviewedExcelNames = ABO.getListOfFilenamesInContainer(config.reviewedExcel_container_name)
    listOfJSONs = ABO.getListOfFilenamesInContainer(config.json_container_name)
    for name in listOfPDFNames:
        chapterNumber = name.rsplit('.')[0]
        excelName = chapterNumber + '.xlsx'
        jsonName = chapterNumber + '.json'
        tableRow = [chapterNumber,name]
        if excelName in listOfGeneratedExcelNames: tableRow.append(excelName)
        else: tableRow.append('Nil')
        if excelName in listOfReviewedExcelNames: tableRow.append(excelName)
        else: tableRow.append('Nil')
        if jsonName in listOfJSONs: tableRow.append(jsonName)
        else: tableRow.append('Nil')
        entity = ato.get_entity(chapterNumber)
        status = entity['RecordStatus']
        tableRow += [status]
        tableRows.append(tableRow)
    return tableRows

def saveFile(folderpath: str, file: FileStorage, filename: str) -> str:
    """Saves the file user has POSTed to the specified folderpath.
    File and Chapter Number from the form is obtained globally thru the Flask requests.

    Returns:
        str: final filepath
    """
    filepath = os.path.join(folderpath, filename)
    file.save(filepath)

    return filepath

def delete_upto_corrected_excel(chapterNumber: int):
    """Deletes a file record upto and including the corrected excel.

    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(delf.deleteChapterFromCosmos(chapterNumber)), 
            executor.submit(delf.deleteChapterJsonBlob(chapterNumber)), 
            executor.submit(delf.deleteChapterReviewedExcelBlob(chapterNumber))
        ]
        concurrent.futures.wait(futures)
    
def delete_upto_pdf(chapterNumber: int):
    """Deletes the entire file record.

    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(delete_upto_corrected_excel(chapterNumber)),
            executor.submit(delf.deleteChapterDictPickleBlob(chapterNumber)),
            executor.submit(delf.deleteChapterGeneratedExcelBlob(chapterNumber)),
            executor.submit(delf.deleteChapterPDFBlob(chapterNumber))
        ]
        concurrent.futures.wait(futures)
    
def upload_pdf(pdffile: BytesIO, user_entered_chapter_number: int = None, filename: str = None):
    print('UPLOAD PDF CALLED')
    
    # convert the PDF into the dictionary, excel and identified chapter number
    dictionary_pkl_stream, excel_stream, chapterNumber = extract_data_for_review.convertPDFToExcelForReview(pdffile,user_entered_chapter_number,filename)
    if not dictionary_pkl_stream: # i.e. an exception was raised when trying to extract data from the pdf
        print('Error with pdf or entered chapter number')
        return
    print('PASSED CONVERSION')
    
    try: ato.create_new_blank_entity(chapterNumber)
    except ResourceExistsError: 
        print(f'A record for chapter {chapterNumber} already exists. Delete it if you want to upload a new PDF.')
        return
    print('MADE TABLE ENTRY')

    mutexKey = secrets.token_hex()
    print('MADE MUTEX KEY')
    try: ato.claim_mutex(chapterNumber, mutexKey)
    except MutexError as e:
        print(e.__str__())
        return
    print('CLAIMED MUTEX')
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.uploadingPDF)
    print('GOING TO UPLOAD PDF')
    pdffile.seek(0)
    abo.upload_to_blob_from_stream(pdffile, config.pdf_container_name, f'{chapterNumber}.pdf') # PDF uploaded to azure blob
    print('UPLOADED PDF')
    print(f'{chapterNumber}.pdf' + ' successfully uploaded')

    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.uploadingGeneratedDocuments)
    abo.upload_to_blob_from_stream(dictionary_pkl_stream, config.generatedDict_container_name, f'{chapterNumber}.pkl') # upload generated excel to azure blob
    abo.upload_to_blob_from_stream(excel_stream, config.generatedExcel_container_name, f'{chapterNumber}.xlsx') # upload dictionary pickle to azure blob
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus='', newRecordState=config.RecordState.pdfUploaded)
    ato.release_mutex(chapterNumber, mutexKey)
      
    print("Data extracted from tariff pdfs and saved as excel (and text data dictionary pickle) for review.")

def batch_upload_pdfs(pdffiles: list[BytesIO], filenames: list[str] = None):
    for i,pdffile in enumerate(pdffiles): # uploads happen in series, so time taken for the total upload process is the same, but memory is saved
        filename = filenames[i]
        upload_pdf(pdffile,filename=filename)
