import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # read local .env file
import markdown
import config
import secrets
import zipfile
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
from data_stores.AzureTableObjects import MutexError
from azure.core.exceptions import ResourceNotFoundError
import concurrent.futures
from io import BytesIO
import logging
import log_handling

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # Needed for flask flash messages, which is used to communicate success/error messages with user
app.config['MAX_CONTENT_LENGTH'] = config.flask_max_accepted_file_size # Max accepted file size by Flask app

log_handling.configure_logging()

ds.updateJSONdictsFromAzureBlob() # update the on-memory json-store from Azure blob

@app.route("/", methods=["GET", "POST"])
def hscode_search():
    logging.info('Request for hscode_search page received')
    results = None
    user_query = None
    if request.method == "POST":
        user_query = request.form.get("query")
        logging.info("app.py: user_query for hscode_search is: " + user_query)
        results = findByHSCode.findByHSCode(user_query)
    return render_template("hscode_search.html", results=results, user_query=user_query)

@app.route("/sccode_search", methods=["GET", "POST"])
def sccode_search():
    logging.info('Request for sccode_search page received')
    results = None
    user_query = None
    if request.method == "POST":
        user_query = request.form.get("query")
        logging.info("app.py: user_query for sccode_search is: " + user_query)
        results = findBySCCode.findBySCCode(user_query)
    return render_template("sccode_search.html", results=results, user_query=user_query)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/line_item_search", methods=["GET", "POST"])
def vector_store_search():
    logging.info('Request for line item search page received')
    user_query = None
    itemsAndScores = None
    if request.method == "POST":
        user_query = request.form.get("query")
        user_query = user_query[:500] # cap to 500 characters to avoid accidential/malicious long query which can incur high embedding costs
        toks.updateTokens(user_query) # update token count tracker
        logging.info("app.py: user_query for line_item_search is: " + user_query)
        itemsAndScores = vectorstoreSearch.vectorStoreSearch(user_query)
    return render_template("line_item_search.html", results=itemsAndScores, user_query=user_query)

@app.route("/rag", methods=["GET", "POST"])
def chatbot():
    logging.info('Request for RAG page received')
    user_query = None
    answer_html = None
    if request.method == "POST":
        user_query = request.form.get("query")
        user_query = user_query[:500] # cap to 500 characters to avoid accidential/malicious long query which can incur high embedding costs
        toks.updateTokens_chatbot(user_query) # update token count tracker
        logging.info("app.py: user_query for RAG page is: " + user_query)
        logging.log(15,"app.py: user_query for RAG page is: " + user_query)
        answer = chatBot.getChatBotAnswer(user_query)
        answer_html = markdown.markdown(answer,extensions=['tables'])
        logging.log(15,'LLM Final answer: \n' + answer + '\n' + answer_html)
    return render_template("rag.html", results=answer_html, user_query=user_query)

@app.route('/file_management')
def file_management():
    logging.info('Request for file management page received')
    tableRows = fm.generateArrayForTableRows()
    return render_template('file_management.html', tableRows = tableRows)

@app.route('/pdf_upload', methods=['POST'])
def pdf_upload():
    logging.info('PDF upload request received.')
    # Get the data POSTED to the server
    chapterNumber = request.form.get('chapterNumber')
    file = request.files['file']
    filename = file.filename
    try: chapterNumber = int(chapterNumber)
    except ValueError: chapterNumber = None

    # Validate
    errors = fm.validateUpload('pdf', file)
    if errors != '':
        logging.error(f'Uploaded file with name {file.filename} error. {errors}')
        return redirect(url_for('file_management'))
    
    # Process upload sequence
    file_stream = BytesIO(file.stream.read())
    file_stream.seek(0)
    executor = concurrent.futures.ThreadPoolExecutor()
    executor.submit(fm.upload_pdf,file_stream,int(chapterNumber),filename)
    executor.shutdown(wait=False)
    return redirect(url_for('file_management'))

@app.route('/pdf_upload_batch', methods=['POST'])
def pdf_upload_batch():
    logging.info('Batch PDF upload request received.')
    files = request.files.getlist("files")

    # Validate and add OK files to an array
    file_streams: list[BytesIO] = []
    filenames: list[str] = []
    for file in files:
        errors = fm.validateUpload('pdf', file)
        if errors != '':
            logging.error(f'Uploaded file with filename {file.filename} has error: {errors}')
        else:
            file_stream = BytesIO(file.stream.read())
            file_stream.seek(0)
            file_streams.append(file_stream)
            filenames.append(file.filename)
    executor = concurrent.futures.ThreadPoolExecutor()
    executor.submit(fm.batch_upload_pdfs,file_streams,filenames)
    executor.shutdown(wait=False)
    return redirect(url_for('file_management'))

@app.route('/excel_upload', methods=['POST'])
def excel_upload():
    logging.info('Excel upload request received.')
    # Get the data POSTED to the server
    chapterNumber = request.form.get('chapterNumber')
    file = request.files['file']
    filename = file.filename
    try: chapterNumber = int(chapterNumber)
    except ValueError: chapterNumber = None

    # Validate
    errors = fm.validateUpload('xlsx', file)
    if errors != '':
        logging.error(f'Uploaded file with name {file.filename} error. {errors}')
        return redirect(url_for('file_management'))
    
    # Process upload sequence
    file_stream = BytesIO(file.stream.read())
    file_stream.seek(0)
    executor = concurrent.futures.ThreadPoolExecutor()
    executor.submit(fm.upload_excel,file_stream,filename,chapterNumber)
    executor.shutdown(wait=False)
    return redirect(url_for('file_management'))


@app.route('/excel_upload_batch', methods=['POST'])
def excel_upload_batch():
    logging.info('Batch Excel upload request received.')
    files = request.files.getlist("files")

    # Validate and add OK files to an array
    file_streams: list[BytesIO] = []
    filenames: list[str] = []
    for file in files:
        errors = fm.validateUpload('xlsx', file)
        if errors != '':
            logging.error(f'Uploaded file with filename {file.filename} has error: {errors}')
        else:
            file_stream = BytesIO(file.stream.read())
            file_stream.seek(0)
            file_streams.append(file_stream)
            filenames.append(file.filename)
    executor = concurrent.futures.ThreadPoolExecutor()
    executor.submit(fm.batch_upload_excels,file_streams,filenames)
    executor.shutdown(wait=False)
    
    return redirect(url_for('file_management'))

@app.route('/file_clicked', methods=['POST'])
# called when user clicks on downloadables on the dynamic table in the html
def file_clicked():
    filename = request.json['cell_value']
    filename = secure_filename(filename)
    filetype = request.json['file_type']
    logging.info(f"Cell clicked with value: {filename}, of type {filetype}")
    containerName = None
    fileTypeToContainerNameMapping = {
        'pdf':config.pdf_container_name,
        'genExcel':config.generatedExcel_container_name,
        'correctedExcel':config.reviewedExcel_container_name,
        'json':config.json_container_name
    }
    containerName = fileTypeToContainerNameMapping[filetype]
    filestream = abo.download_blob_file_to_stream(filename, containerName)
    filestream.seek(0)
    response = send_file(filestream, as_attachment=True, download_name=filename)
    return response

@app.route('/delete_till_corrected_excel', methods=['POST'])
def delete_till_corrected_excel():
    chapterNumber = request.form.get('chapterNumber')
    logging.info(f'Request to delete_till_corrected_excel - chapter {chapterNumber} received.')

    try: entity = ato.get_entity(chapterNumber)
    except ResourceNotFoundError:
        logging.error(f'The chapter {chapterNumber} was not found.')
        flash('The chapter was not found.')
        return redirect(url_for('file_management'))
    if entity['RecordState'] != config.RecordState.excelUploaded:
        logging.error(f'Nothing to delete yet.(till corrected excel) Chapter {chapterNumber}')
        flash('Nothing to delete yet.')
        return redirect(url_for('file_management'))
    

    mutexKey = secrets.token_hex()
    try: ato.claim_mutex(chapterNumber, mutexKey)
    except MutexError as e:
        logging.error(e.__str__())
        flash(e.__str__())
        return redirect(url_for('file_management'))
    

    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.beginDeleteExcel)
    fm.delete_upto_corrected_excel(int(chapterNumber))
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus='', newRecordState=config.RecordState.pdfUploaded)
    ato.release_mutex(chapterNumber, mutexKey)
    logging.log(25, 'Deleted upto corrected excel - chapter ' + str(chapterNumber))
    flash('Deleted upto corrected excel - chapter ' + str(chapterNumber))
    return redirect(url_for('file_management'))

@app.route('/delete_till_pdf', methods=['POST'])
def delete_till_pdf():
    chapterNumber = request.form.get('chapterNumber')
    logging.info(f'Request to delete_till_pdf - chapter {chapterNumber} received.')

    mutexKey = secrets.token_hex()
    try: ato.claim_mutex(chapterNumber, mutexKey)
    except MutexError as e:
        logging.error(e.__str__())
        flash(e.__str__())
        return redirect(url_for('file_management'))
    except ResourceNotFoundError:
        logging.error(f'The chapter {chapterNumber} was not found.')
        flash('The chapter was not found.')
        return redirect(url_for('file_management'))
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.beginDeletePDF)
    fm.delete_upto_pdf(int(chapterNumber))
    ato.edit_entity(chapterNumber, mutexKey, newRecordStatus=config.RecordStatus.beginDeleteEntity)
    ato.delete_entity(chapterNumber, mutexKey)
    logging.log(25,'Deleted upto pdf (i.e. all) - chapter ' + str(chapterNumber))
    flash('Deleted upto pdf (i.e. all) - chapter ' + str(chapterNumber))
    return redirect(url_for('file_management'))

@app.route('/generate_excel_for_review', methods=['POST'])
def generate_excel_for_review():
    # Get the data POSTED to the server
    chapterNumber = request.form.get('chapterNumber')
    logging.info(f'Request to generate excel received for chapter {chapterNumber}')
    file = request.files['file']
    filename = file.filename
    try: chapterNumber = int(chapterNumber)
    except ValueError: chapterNumber = None

    # Validate
    errors = fm.validateUpload('pdf', file)
    if errors != '':
        logging.error(f'Uploaded file with name {file.filename} error. {errors}')
        return redirect(url_for('file_management'))
    
    # Process (generate the excel)
    file_stream = BytesIO(file.stream.read())
    file_stream.seek(0)
    _, excel_stream, chapterNumber = convertPDFToExcelForReview(file_stream,chapterNumber,filename)
    if not excel_stream: # i.e. an exception was raised when trying to extract data from the pdf
        logging.error(f'Error with pdf or entered chapter number - generate_excel_for_review - Chapter {str(chapterNumber)}')
        flash('Error with pdf or entered chapter number')
        return redirect(url_for('file_management'))
    ## change filename to same filename with xlsx extension
    filename = filename.replace('.pdf','.xlsx')

    response = send_file(excel_stream, as_attachment=True, download_name=filename)
    return response

@app.route('/download_uncommitted_excels', methods=['GET'])
def download_uncommitted_excels():
    logging.info('Request to download uncommitted excels received')
    chapters = ato.search_entities('RecordState', config.RecordState.pdfUploaded)

    # download the excel-to-review for each chapter
    excels: list[tuple[str,BytesIO]] = []
    for chapter in chapters:
        filename = str(chapter) + '.xlsx'
        excel = abo.download_blob_file_to_stream(filename, config.generatedExcel_container_name)
        excel.seek(0)
        excels.append((filename,excel))

    # zip them
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for name, file in excels:
            zip_file.writestr(name, file.getvalue())
    zip_buffer.seek(0)

    # return the zip as a response
    response = send_file(zip_buffer, as_attachment=True, download_name='excels_for_review.zip')
    return response

@app.route('/logs', methods=['GET'])
def print_logs():
    print('LOGS:')
    for log in log_handling.log_messages:
        print(log)
    print('LOGS END')
    return render_template('logs.html')

if __name__ == '__main__':
   app.run()
