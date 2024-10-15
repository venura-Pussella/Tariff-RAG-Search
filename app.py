import os
import markdown
import platform
import config
from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for, flash, send_file)
from app_functions import findByHSCode
from app_functions import findBySCCode
import app_functions.chatBot as chatBot
from app_functions import vectorstoreSearch
from other_funcs.tokenTracker import TokenTracker as toks
from app_functions import file_management as fm
from data_stores.AzureBlobObjects import AzureBlobObjects as abo
from data_stores.DataStores import DataStores as ds
from initializers.extract_data_for_review import convertPDFToExcelForReview
import subprocess
from initializers.extract_data_to_json_store import extract_data_to_json_store

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # Needed for flash messages

ds.updateJSONdictsFromAzureBlob()

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

@app.route("/vector_store_search", methods=["GET", "POST"])
def vector_store_search():
    print('Request for vector search page received')
    user_query = None
    itemsAndScores = None
    if request.method == "POST":
        user_query = request.form.get("query")
        user_query = user_query[:500] # cap to 500 characters to avoid accidential/malicious long query which can incur high embedding costs
        toks.updateTokens(user_query)
        print("app.py: user_query for vector_search is: " + user_query)
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
        print("app.py: user_query for RAG page is: " + user_query)
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
    
    abo.upload_blob_file(filepath, config.pdf_container_name) # PDF uploaded to azure blob
    print('PDF @ ' + filepath + ' successfully uploaded')
    flash('PDF successfully uploaded')

    subprocess.Popen(["python", "initializers/post_PDF_dataExtraction_tasks.py", reviewFilepaths[0], reviewFilepaths[1], filepath]) # continue PDF processing in background
    return redirect(url_for('file_management'))

@app.route('/excel_upload', methods=['POST'])
def excel_upload():
    print('Excel upload request received.')
    
    result = fm.validateUpload(extension='xlsx')
    if result[0] == False:
        flash(result[1]) 
        return redirect(result[2])
    
    chapterNumber = request.form.get('chapterNumber')
    excelFilepath = fm.saveFile(config.temp_folderpath_for_pdf_and_excel_uploads) # User uploaded pdf has been renamed with chapter number and saved to temporary location
    
    isSuccess = extract_data_to_json_store(int(chapterNumber), excelFilepath)
    if isSuccess:
        flash('Excel and generated json successfully uploaded.')
    else:
        flash('Excel was rejected due to an error. Maybe at least one of the HS codes provided did not match the entered chapter number.')
        return redirect(url_for('file_management'))
    
    subprocess.Popen(["python", "initializers/create_vectorstore.py", str(chapterNumber)]) # continue remaining processing in the background
    return redirect(url_for('file_management'))

@app.route('/file_clicked', methods=['POST'])
# called when user clicks on downloadables on the dynamic table in the html
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
    fm.delete_upto_corrected_excel(int(chapterNumber))
    flash('Deleted upto corrected excel - chapter ' + str(chapterNumber))
    return redirect(url_for('file_management'))

@app.route('/delete_till_pdf', methods=['POST'])
def delete_till_pdf():
    chapterNumber = request.form.get('chapterNumber')
    fm.delete_upto_pdf(int(chapterNumber))
    print('Deleted upto pdf (i.e. all) - chapter ' + str(chapterNumber))
    flash('Deleted upto pdf (i.e. all) - chapter ' + str(chapterNumber))
    return redirect(url_for('file_management'))

if __name__ == '__main__':
   app.run()
