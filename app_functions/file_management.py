import os
import config
from data_stores.AzureBlobObjects import AzureBlobObjects as ABO
from data_stores.AzureTableObjects import AzureTableObjects as ato
from flask import url_for, request
from werkzeug.utils import secure_filename
from initializers import deletingFuncs as delf
import concurrent.futures

def allowed_file(filename: str, extension: str) -> bool:
    """Checks if filename has allowed extension.
    Example: filename = '28.pdf', extension = 'pdf' will return true
    """
    actualExtension = filename.rsplit(".")[-1]
    return actualExtension == extension

def validateUpload(extension: str) -> tuple[bool, str, str]:
    """Checks if the document POSTed by the user is a valid file upload.

    Args:
        extension (str): expected extension of the file user is expected to POST

    Returns:
        tuple[bool, str, str]: 1st item indicates validity of upload. 2nd item is the message for the flash message to alert the user, 3rd item is url to redirect the user
    """
    
    flashMessage = ''
    redirectMessage = ''

    chapterNumber = request.form.get('chapterNumber')
    try:
        int(chapterNumber)
    except:
        flashMessage = 'Error with entered chapter number'
        redirectMessage = url_for('file_management')

    # Check if the request has the file part
    if 'file' not in request.files:
        flashMessage = 'No file part'
        redirectMessage = url_for('file_management')
    
    file = request.files['file']
    # If no file was selected
    if file.filename == '':
        flashMessage = 'No selected file'
        redirectMessage = url_for('file_management')
    
    if file and not allowed_file(file.filename, extension):
        flashMessage = 'Incompatible file type or extension.'
        redirectMessage = url_for('file_management')

    if flashMessage == '': # i.e. if there is no issue
        return (True, flashMessage, redirectMessage)
    else:
        return (False, flashMessage, redirectMessage)

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

def saveFile(folderpath: str) -> str:
    """Saves the file user has POSTed to the specified folderpath.
    File and Chapter Number from the form is obtained globally thru the Flask requests.

    Returns:
        str: final filepath
    """
    file = request.files['file']
    chapterNumber = request.form.get('chapterNumber')

    filename = secure_filename(file.filename)
    filename = filename.rsplit(".")[-1]
    filename = str(chapterNumber) + '.' + filename
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
    