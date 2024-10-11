import os
import markdown
import platform
import config
from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for, flash, send_file)
from werkzeug.utils import secure_filename
from app_functions import findByHSCode
from app_functions import findBySCCode
import app_functions.chatBot as chatBot
from app_functions import vectorstoreSearch
from other_funcs.tokenTracker import TokenTracker as toks
from initializers import file_management as fm
from initializers.extract_data_to_json_store import saveExcelAndDictToJSON2
import subprocess

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # Needed for flash messages

@app.route("/", methods=["GET", "POST"])
def hscode_search():
    print('Request for hscode_search page received')
    results = None
    user_query = None
    if request.method == "POST":
        user_query = request.form.get("query")
        print("app.py: user_query is: " + user_query)
        results = findByHSCode.findByHSCode(user_query)
    return render_template("hscode_search.html", results=results, user_query=user_query)


@app.route("/sccode_search", methods=["GET", "POST"])
def sccode_search():
    print('Request for sccode_search page received')
    results = None
    user_query = None
    if request.method == "POST":
        user_query = request.form.get("query")
        print("app.py: user_query is: " + user_query)
        results = findBySCCode.findBySCCode(user_query)
    return render_template("sccode_search.html", results=results, user_query=user_query)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/vector_store_search", methods=["GET", "POST"])
def vector_store_search():
    print('Request for vector search page received')
    user_query = None
    itemsAndScores = None
    if request.method == "POST":
        user_query = request.form.get("query")
        user_query = user_query[:500] # cap to 500 characters to avoid accidential/malicious long query which can incur high embedding costs
        toks.updateTokens(user_query)
        print("app.py: user_query is: " + user_query)
        itemsAndScores = vectorstoreSearch.vectorStoreSearch(user_query)
    return render_template("vector_store_search.html", results=itemsAndScores, user_query=user_query)


@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    print('Request for RAG page received')
    user_query = None
    answer_html = None
    if request.method == "POST":
        user_query = request.form.get("query")
        user_query = user_query[:500] # cap to 500 characters to avoid accidential/malicious long query which can incur high embedding costs
        toks.updateTokens_chatbot(user_query)
        print("app.py: user_query is: " + user_query)
        answer = chatBot.getChatBotAnswer(user_query)
        answer_html = markdown.markdown(answer,extensions=['tables'])
    return render_template("chatbot.html", results=answer_html, user_query=user_query)


@app.route('/file_management')
def file_management():
    print('Request for file management page received')
    tableRows = fm.generateArrayForTableRows()
    return render_template('file_management.html', tableRows = tableRows)

@app.route('/pdf_upload', methods=['POST'])
def pdf_upload():
    print('PDF upload request received.')
    # Check if the request has the file part
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('file_management'))
    
    file = request.files['file']
    chapterNumber = request.form.get('chapterNumber')
    
    # If no file was selected
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('file_management'))
    
    if file and not fm.allowed_file(file.filename, 'pdf'):
        flash('Incompatible file type or extension.') 
        return redirect(url_for('file_management'))

    if file and fm.allowed_file(file.filename, 'pdf'):
        # Save the file securely
        filename = secure_filename(file.filename)
        filename = filename.rsplit(".")[-1]
        filename = str(chapterNumber) + '.' + filename
        filepath = os.path.join('files/', filename)
        file.save(filepath)
        fm.upload_blob_file(filepath, config.pdf_container_name)
        flash('File successfully uploaded')
        reviewFilepaths = fm.convertPDFToExcelForReview(filepath)
        print("PDF converted to excel and dict for review.")
        os.remove(filepath)
        fm.upload_blob_file(reviewFilepaths[0],config.generatedExcel_container_name)
        fm.upload_blob_file(reviewFilepaths[1],config.generatedDict_container_name)
        os.remove(reviewFilepaths[0])
        os.remove(reviewFilepaths[1])
        print("Uploaded pdf and dict for review")
        return redirect(url_for('file_management'))


@app.route('/excel_upload', methods=['POST'])
def excel_upload():
    print('Excel upload request received.')
    # Check if the request has the file part
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('file_management'))
    
    file = request.files['file']
    chapterNumber = request.form.get('chapterNumber')
    
    # If no file was selected
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('file_management'))
    
    if file and not fm.allowed_file(file.filename, 'xlsx'):
        flash('Incompatible file type or extension.') 
        return redirect(url_for('file_management'))

    if file and fm.allowed_file(file.filename, 'xlsx'):
        # Save the file securely
        filename = secure_filename(file.filename)
        filename = filename.rsplit(".")[-1]
        filename = str(chapterNumber) + '.' + filename
        excelFilepath = os.path.join('files/reviewed_data/', filename)
        file.save(excelFilepath)
        fm.upload_blob_file(excelFilepath, config.reviewedExcel_container_name)
        flash('File successfully uploaded')
        dictFileName = str(chapterNumber) + '.pkl'
        dictPath = 'files/reviewed_data/' + dictFileName
        fm.download_blob_file(dictFileName, config.generatedDict_container_name, dictPath)
        jsonPath = 'files/reviewed_data/' + str(chapterNumber) + '.json'
        saveExcelAndDictToJSON2(excelFilepath,dictPath,jsonPath)
        print("Excel converted to json.")
        os.remove(dictPath)
        os.remove(excelFilepath)
        fm.upload_blob_file(jsonPath,config.json_container_name)
        os.remove(jsonPath)
        print("Uploaded json")
        subprocess.Popen(["python", "initializers/create_vectorstore.py"])
        return redirect(url_for('file_management'))

    
@app.route('/file_clicked', methods=['POST'])
def file_clicked():
    filename = request.json['cell_value']
    filetype = request.json['file_type']
    print(f"Cell clicked with value: {filename}, of type {filetype}")
    containerName = None
    fileTypeToContainerNameMapping = {
        'pdf':config.pdf_container_name,
        'genExcel':config.generatedExcel_container_name,
        'correctedExcel':config.reviewedExcel_container_name,
        'json':config.json_container_name
    }
    containerName = fileTypeToContainerNameMapping[filetype]
    savepath = 'files/tempDownloadToOfferUser/' + filename
    fm.download_blob_file(filename, containerName, savepath)
    response = send_file(savepath, as_attachment=True, download_name=filename)
    if platform.system() != 'Windows': # had issues with Windows (at least the Browns laptop) where the file was still 'in-use' even after the response was created. Shouldn't be an issue in deployment because we are using an Azure linux app service.
        os.remove(savepath)
    return response


if __name__ == '__main__':
   app.run()
