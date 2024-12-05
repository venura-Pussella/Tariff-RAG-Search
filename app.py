import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # read local .env file
import markdown
import platform
import config
import secrets
from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for, flash, send_file)
from werkzeug.utils import secure_filename
from app_functions import findByHSCode
from app_functions import findBySCCode
import app_functions.chatBot as chatBot
from app_functions import vectorstoreSearch
from other_funcs.tokenTracker import TokenTracker as toks
from app_functions import file_management as fm
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from data_stores.AzureTableObjects import AzureTableObjects as ato
from data_stores.DataStores import DataStores as ds
from initializers.extract_data_for_review import convertPDFToExcelForReview
import subprocess
from initializers.extract_data_to_json_store import extract_data_to_json_store
from data_stores.AzureTableObjects import MutexError
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import uuid

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # Needed for flask flash messages, which is used to communicate success/error messages with user

ds.updateJSONdictsFromAzureBlob() # update the on-memory json-store from Azure blob

@app.route("/", methods=["GET", "POST"])
def hscode_search():
    print('Request for hscode_search page received')
    results = None
    user_query = None
    if request.method == "POST":
        user_query = request.form.get("query")
        print("app.py: user_query for hscode_search is: " + user_query)
        results = findByHSCode.findByHSCode(user_query)
    return render_template("hscode_search.html", results=results, user_query=user_query)

@app.route("/sccode_search", methods=["GET", "POST"])
def sccode_search():
    print('Request for sccode_search page received')
    results = None
    user_query = None
    if request.method == "POST":
        user_query = request.form.get("query")
        print("app.py: user_query for sccode_search is: " + user_query)
        results = findBySCCode.findBySCCode(user_query)
    return render_template("sccode_search.html", results=results, user_query=user_query)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/line_item_search", methods=["GET", "POST"])
def vector_store_search():
    print('Request for line item search page received')
    user_query = None
    itemsAndScores = None
    if request.method == "POST":
        user_query = request.form.get("query")
        user_query = user_query[:500] # cap to 500 characters to avoid accidential/malicious long query which can incur high embedding costs
        toks.updateTokens(user_query) # update token count tracker
        print("app.py: user_query for line_item_search is: " + user_query)
        itemsAndScores = vectorstoreSearch.vectorStoreSearch(user_query)
    return render_template("line_item_search.html", results=itemsAndScores, user_query=user_query)

@app.route("/rag", methods=["GET", "POST"])
def chatbot():
    print('Request for RAG page received')
    user_query = None
    answer_html = None
    if request.method == "POST":
        user_query = request.form.get("query")
        user_query = user_query[:500] # cap to 500 characters to avoid accidential/malicious long query which can incur high embedding costs
        toks.updateTokens_chatbot(user_query) # update token count tracker
        print("app.py: user_query for RAG page is: " + user_query)
        answer = chatBot.getChatBotAnswer(user_query)
        answer_html = markdown.markdown(answer,extensions=['tables'])
    return render_template("rag.html", results=answer_html, user_query=user_query)

@app.route('/file_management')
def file_management():
    print('Request for file management page received')
    tableRows = fm.generateArrayForTableRows()
    return render_template('file_management.html', tableRows = tableRows)

@app.route('/pdf_upload', methods=['POST'])
def pdf_upload():
    print('PDF upload request received.')
    chapterNumber = request.form.get('chapterNumber')
    file = request.files['file']
    filename = str(uuid.uuid4()) + file.filename
    filepath = fm.saveFile(config.temp_folderpath_for_pdf_and_excel_uploads ,file, filename)
    subprocess.Popen(["python", "initializers/uploadPDF_script.py", filepath, chapterNumber])
    return redirect(url_for('file_management'))

@app.route('/pdf_upload_batch', methods=['POST'])
def pdf_upload_batch():
    print('Batch PDF upload request received.')
    files = request.files.getlist("files")
    for file in files:
        filename = str(uuid.uuid4()) + file.filename
        filepath = fm.saveFile(config.temp_folderpath_for_pdf_and_excel_uploads ,file, filename)
        subprocess.Popen(["python", "initializers/uploadPDF_script.py", filepath])
    return redirect(url_for('file_management'))

@app.route('/excel_upload', methods=['POST'])
def excel_upload():
    print('Excel upload request received.')
    chapterNumber = request.form.get('chapterNumber')
    file = request.files['file']
    filename = str(uuid.uuid4()) + file.filename
    excelFilepath = fm.saveFile(config.temp_folderpath_for_pdf_and_excel_uploads ,file, filename)

    mutexKey = secrets.token_hex()
    try: ato.claim_mutex(chapterNumber, mutexKey)
    except MutexError as e:
        if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
            os.remove(excelFilepath)
        flash(e.__str__())
        return redirect(url_for('file_management'))
    except ResourceNotFoundError:
        if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
            os.remove(excelFilepath)
        flash('The chapter was not found. Perhaps you must create the chapter record by uploading a PDF.')
        return redirect(url_for('file_management'))

    isSuccess = extract_data_to_json_store(int(chapterNumber), excelFilepath, mutexKey)
    # Code upto here must be executed on main program (bcuz need to keep in-memory JSON store updated)

    if isSuccess:
        flash('Excel and generated json successfully uploaded.')
    else:
        flash('Excel was rejected due to an error. Maybe at least one of the HS codes provided did not match the entered chapter number.')
        return redirect(url_for('file_management'))
    
    subprocess.Popen(["python", "initializers/create_vectorstore.py", str(chapterNumber), mutexKey]) # continue remaining processing in the background
    return redirect(url_for('file_management'))

@app.route('/excel_upload_batch', methods=['POST'])
def excel_upload_batch():
    print('Batch Excel upload request received.')
    files = request.files.getlist("files")
    for file in files:
        filename = str(uuid.uuid4()) + 'UUIDEND' + file.filename
        excelFilepath = fm.saveFile(config.temp_folderpath_for_pdf_and_excel_uploads ,file, filename)
        try:
            chapterNumber = int(file.filename.rsplit('.')[0])
        except: 
            print(f'Failed to extract chapter number from filename for {file.filename}')
            continue

        mutexKey = secrets.token_hex()
        try: ato.claim_mutex(chapterNumber, mutexKey)
        except MutexError as e:
            if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
                os.remove(excelFilepath)
            flash(e.__str__())
            return redirect(url_for('file_management'))
        except ResourceNotFoundError:
            if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
                os.remove(excelFilepath)
            flash('The chapter was not found. Perhaps you must create the chapter record by uploading a PDF.')
            return redirect(url_for('file_management'))

        isSuccess = extract_data_to_json_store(int(chapterNumber), excelFilepath, mutexKey)
        # Code upto here must be executed on main program (bcuz need to keep in-memory JSON store updated)

        if isSuccess:
            flash('Excel and generated json successfully uploaded.')
        else:
            flash('Excel was rejected due to an error. Maybe at least one of the HS codes provided did not match the entered chapter number.')
            return redirect(url_for('file_management'))
        
        subprocess.Popen(["python", "initializers/create_vectorstore.py", str(chapterNumber), mutexKey]) # continue remaining processing in the background
    return redirect(url_for('file_management'))

@app.route('/file_clicked', methods=['POST'])
# called when user clicks on downloadables on the dynamic table in the html
def file_clicked():
    filename = request.json['cell_value']
    filename = secure_filename(filename)
    filetype = request.json['file_type']
    print(f"Cell clicked with value: {filename}, of type {filetype}")
    containerName = None
    fileTypeToContainerNameMapping = {
        'pdf':config.pdf_container_name,
        'genExcel':config.generatedExcel_container_name,
        'correctedExcel':config.reviewedExcel_container_name,
        'json':config.json_container_name
    }
    fileTypeToFolderpathMapping = {
        'pdf':config.temp_folderpath_for_pdf_and_json_downloads,
        'genExcel':config.temp_folderpath_for_genExcel_downloads,
        'correctedExcel':config.temp_folderpath_for_reviewedExcel_downloads,
        'json':config.temp_folderpath_for_pdf_and_json_downloads
    }
    containerName = fileTypeToContainerNameMapping[filetype]
    savepath = fileTypeToFolderpathMapping[filetype] + filename
    abo.download_blob_file(filename, containerName, savepath)
    response = send_file(savepath, as_attachment=True, download_name=filename)
    if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
        os.remove(savepath)
    return response

@app.route('/delete_till_corrected_excel', methods=['POST'])
def delete_till_corrected_excel():
    chapterNumber = request.form.get('chapterNumber')

    try: entity = ato.get_entity(chapterNumber)
    except ResourceNotFoundError:
        flash('The chapter was not found.')
        return redirect(url_for('file_management'))
    if entity['RecordState'] != config.RecordState.excelUploaded:
        flash('Nothing to delete yet.')
        return redirect(url_for('file_management'))
    

    mutexKey = secrets.token_hex()
    try: ato.claim_mutex(chapterNumber, mutexKey)
    except MutexError as e:
        flash(e.__str__())
        return redirect(url_for('file_management'))
    

    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.beginDeleteExcel)
    fm.delete_upto_corrected_excel(int(chapterNumber))
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus='', newRecordState=config.RecordState.pdfUploaded)
    ato.release_mutex(chapterNumber, mutexKey)
    flash('Deleted upto corrected excel - chapter ' + str(chapterNumber))
    return redirect(url_for('file_management'))

@app.route('/delete_till_pdf', methods=['POST'])
def delete_till_pdf():
    chapterNumber = request.form.get('chapterNumber')

    mutexKey = secrets.token_hex()
    try: ato.claim_mutex(chapterNumber, mutexKey)
    except MutexError as e:
        flash(e.__str__())
        return redirect(url_for('file_management'))
    except ResourceNotFoundError:
        flash('The chapter was not found.')
        return redirect(url_for('file_management'))
    print('haha3')
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.beginDeletePDF)
    fm.delete_upto_pdf(int(chapterNumber))
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.beginDeleteEntity)
    ato.delete_entity(chapterNumber, mutexKey)
    print('Deleted upto pdf (i.e. all) - chapter ' + str(chapterNumber))
    flash('Deleted upto pdf (i.e. all) - chapter ' + str(chapterNumber))
    return redirect(url_for('file_management'))

@app.route('/generate_excel_for_review', methods=['POST'])
def generate_excel_for_review():
    print('Request to generate excel received.')
    chapterNumber = request.form.get('chapterNumber')

    result = fm.validateUpload(extension='pdf')
    if result[0] == False:
        flash(result[1]) 
        return redirect(result[2])
    
    filepath = fm.saveFile(config.temp_folderpath_for_pdf_and_excel_uploads) # User uploaded pdf has been renamed with chapter number and saved to temporary location
    reviewFilepaths = convertPDFToExcelForReview(filepath, int(chapterNumber))

    if not reviewFilepaths: # i.e. an exception was raised when trying to extract data from the pdf
        flash('Error with pdf or entered chapter number')
        return redirect(url_for('file_management'))
    
    filename = reviewFilepaths[0].rsplit("/")[-1]
    response = send_file(reviewFilepaths[0], as_attachment=True, download_name=filename)
    if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
        os.remove(filepath)
        os.remove(reviewFilepaths[0])
        os.remove(reviewFilepaths[1])
    return response

if __name__ == '__main__':
   app.run()
