import os
import config
from data_stores.AzureBlobObjects import AzureBlobObjects as ABO
from flask import url_for, request
from werkzeug.utils import secure_filename

def allowed_file(filename: str, extension: str):
    """Checks if filename has allowed extension.
    ### Example:
    filename = '28.pdf', extension = 'pdf' will return true
    """
    actualExtension = filename.rsplit(".")[-1]
    return actualExtension == extension

def validateUpload(extension: str) -> tuple[bool, str, str]:
    # Check if the request has the file part
    flashMessage = ''
    redirectMessage = ''
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

def generateArrayForTableRows():
    tableRows = []
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
        tableRow += ['status']
        # tableRows.append([chapterNumber,name,'d1','d2','d3','uploaded'])
        tableRows.append(tableRow)
    return tableRows

def saveFile(folderpath: str) -> str:
    file = request.files['file']
    chapterNumber = request.form.get('chapterNumber')

    filename = secure_filename(file.filename)
    filename = filename.rsplit(".")[-1]
    filename = str(chapterNumber) + '.' + filename
    filepath = os.path.join(folderpath, filename)
    file.save(filepath)

    return filepath