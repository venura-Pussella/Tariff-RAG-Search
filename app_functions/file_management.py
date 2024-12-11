import config
import secrets
import logging
from data_stores.AzureBlobObjects import AzureBlobObjects as ABO
from data_stores.AzureTableObjects import AzureTableObjects as ato
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from werkzeug.datastructures import FileStorage
from initializers import deletingFuncs as delf
from initializers import extract_data_for_review
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from data_stores.AzureTableObjects import MutexError
import concurrent.futures
from io import BytesIO
from initializers.extract_data_to_json_store import extract_data_to_json_store
from initializers.create_vectorstore import update_vectorstore

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
        release_date = name.rsplit('/')[0]
        chapterNumber = name.rsplit('/')[1].rsplit('.')[0]
        excelName = chapterNumber + '.xlsx'
        jsonName = chapterNumber + '.json'
        tableRow = [release_date,chapterNumber,f'{chapterNumber}.pdf']
        if f'{release_date}/{excelName}' in listOfGeneratedExcelNames: tableRow.append(excelName)
        else: tableRow.append('Nil')
        if f'{release_date}/{excelName}' in listOfReviewedExcelNames: tableRow.append(excelName)
        else: tableRow.append('Nil')
        if f'{release_date}/{jsonName}' in listOfJSONs: tableRow.append(jsonName)
        else: tableRow.append('Nil')
        entity = ato.get_entity(chapterNumber, release_date)
        status = entity['RecordStatus']
        tableRow += [status]
        tableRows.append(tableRow)
    return tableRows

def delete_upto_corrected_excel(chapterNumber: int):
    """Deletes a file record upto and including the corrected excel.

    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(delf.deleteChapterFromCosmos, chapterNumber), 
            executor.submit(delf.deleteChapterJsonBlob, chapterNumber), 
            executor.submit(delf.deleteChapterReviewedExcelBlob, chapterNumber)
        ]
        concurrent.futures.wait(futures)
    
def delete_upto_pdf(chapterNumber: int):
    """Deletes the entire file record.

    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(delete_upto_corrected_excel, chapterNumber),
            executor.submit(delf.deleteChapterDictPickleBlob, chapterNumber),
            executor.submit(delf.deleteChapterGeneratedExcelBlob, chapterNumber),
            executor.submit(delf.deleteChapterPDFBlob, chapterNumber)
        ]
        concurrent.futures.wait(futures)
    
def upload_pdf(pdffile: BytesIO, release_date: str,user_entered_chapter_number: int = None, filename: str = None):
   
    # convert the PDF into the dictionary, excel and identified chapter number
    dictionary_pkl_stream, excel_stream, chapterNumber = extract_data_for_review.convertPDFToExcelForReview(pdffile,user_entered_chapter_number,filename)
    if not dictionary_pkl_stream: # i.e. an exception was raised when trying to extract data from the pdf
        if user_entered_chapter_number:
            logging.error(f'Error with pdf or entered chapter number. User entered chapter number: {user_entered_chapter_number}. Release {release_date}')
        elif filename:
            logging.error(f"Error with pdf or entered chapter number. User uploaded file's filename: {filename}. Release {release_date}")
        elif chapterNumber:
            logging.error(f"Error with pdf or entered chapter number. Filename and user_entered_chapter_number not received. Identified chapter number: {str(chapterNumber)}. Release {release_date}")
        return
    
    try: ato.create_new_blank_entity(chapterNumber, release_date)
    except ResourceExistsError: 
        logging.error(f'A record for chapter {chapterNumber} (release {release_date}) already exists. Delete it if you want to upload a new PDF.')
        return

    mutexKey = secrets.token_hex()
    try: ato.claim_mutex(chapterNumber, mutexKey, release_date)
    except MutexError as e:
        logging.error(e.__str__())
        return
    ato.edit_entity(chapterNumber, mutexKey, release_date, newRecordStatus=config.RecordStatus.uploadingPDF)
    pdffile.seek(0)
    abo.upload_to_blob_from_stream(pdffile, config.pdf_container_name, f'{chapterNumber}.pdf', release_date) # PDF uploaded to azure blob
    logging.log(25,f'{chapterNumber}.pdf' + f' of release {release_date} ' + ' successfully uploaded')

    ato.edit_entity(chapterNumber, mutexKey, release_date, newRecordStatus=config.RecordStatus.uploadingGeneratedDocuments)
    abo.upload_to_blob_from_stream(dictionary_pkl_stream, config.generatedDict_container_name, f'{chapterNumber}.pkl', release_date) # upload generated excel to azure blob
    abo.upload_to_blob_from_stream(excel_stream, config.generatedExcel_container_name, f'{chapterNumber}.xlsx', release_date) # upload dictionary pickle to azure blob
    ato.edit_entity(chapterNumber, mutexKey, release_date, newRecordStatus='', newRecordState=config.RecordState.pdfUploaded)
    ato.release_mutex(chapterNumber, mutexKey, release_date)
      
    logging.info("Data extracted from tariff pdfs and saved as excel (and text data dictionary pickle) for review.")

def batch_upload_pdfs(pdffiles: list[BytesIO], release_date: str, filenames: list[str] = None):
    for i,pdffile in enumerate(pdffiles): # uploads happen in series, so time taken for the total upload process is the same, but memory is saved
        filename = filenames[i]
        upload_pdf(pdffile,release_date,filename=filename)

def upload_excel(excelfile: BytesIO, filename: str, user_entered_chapter_number: int = None):
    # if user has entered the chapter number, that is taken as the chapterNumber, otherwise it's taken from the filename
    if user_entered_chapter_number: chapterNumber = user_entered_chapter_number
    else: 
        chapterNumber = filename.rsplit('.')[0]
        try: chapterNumber = int(chapterNumber)
        except ValueError: 
            logging.error(f'Cannot identify the chapter number the excel {filename} refers to')
            return

    mutexKey = secrets.token_hex()
    try: ato.claim_mutex(chapterNumber, mutexKey)
    except MutexError as e:
        logging.error(e.__str__())
        return
    except ResourceNotFoundError:
        logging.error(f'The chapter was not found. Perhaps you must create the chapter record by uploading a PDF. Excel: {filename}')
        return

    isSuccess = extract_data_to_json_store(excelfile, mutexKey, chapterNumber)
    if isSuccess:
        logging.log(25,'Excel and generated json successfully uploaded.')
    else:
        logging.error(f'Excel was rejected due to an error. Maybe at least one of the HS codes provided did not match the entered chapter number. Excel: {filename}')
        ato.release_mutex(chapterNumber, mutexKey)
        return
    
    update_vectorstore(chapterNumber, mutexKey)

def batch_upload_excels(excelfiles: list[BytesIO], filenames: list[str] = None):
    for i,excelfile in enumerate(excelfiles): # uploads happen in series, so time taken for the total upload process is the same, but memory is saved
        filename = filenames[i]
        upload_excel(excelfile,filename=filename)
    