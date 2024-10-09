import os
import markdown
from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for, flash)
from werkzeug.utils import secure_filename
from app_functions import findByHSCode
from app_functions import findBySCCode
import app_functions.chatBot as chatBot
from app_functions import vectorstoreSearch
from other_funcs.tokenTracker import TokenTracker as toks
from initializers import file_management as fm

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

app = Flask(__name__)
app.secret_key = 'secret_key'  # Needed for flash messages

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
        print("no. of results:  " + str(len(itemsAndScores)))
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
    tableRows = fm.generateArrayForTableRows()
    return render_template('file_management.html', tableRows = tableRows)

@app.route('/pdf_upload', methods=['POST'])
def pdf_upload():
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
        filepath = os.path.join('files/Tariff_PDFs', filename)
        file.save(filepath)
        fm.upload_blob_file(filepath)
        flash('File successfully uploaded')
        return redirect(url_for('pdf_upload'))
    
@app.route('/cell_clicked', methods=['POST'])
def cell_clicked():
    print("triggered")
    print(request.json)
    cell_value = request.json['cell_value']
    print(f"Cell clicked with value: {cell_value}")
    # Trigger any function based on cell value here
    # For now, just return a success message
    return "You clicked on " + str(cell_value)


if __name__ == '__main__':
   app.run()
