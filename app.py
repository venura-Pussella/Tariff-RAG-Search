import os

from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for)
from app_functions import findByHSCode
from app_functions import vectorStoreSearch
from app_functions import findBySCCode
from initializers import loadJSONAtRuntime as lj
from initializers import loadID_HSCodesAtRuntime as idhs
from initializers import loadSCCodeToHSCodeMappingAtRuntime as schs
from app_functions.tokenTracker import TokenTracker as toks

app = Flask(__name__)

data_dict = lj.loadJSONsAtRuntime()
ids_hscodes_dict = idhs.loadID_HSCodesAtRuntime()
scToHSMapping = schs.getSCCodeToHSCodeMapping()
vectorstore = vectorStoreSearch.getVectorStore()

@app.route("/", methods=["GET", "POST"])
def hscode_search():
    print('Request for hscode_search page received')
    results = None
    user_query = None
    if request.method == "POST":
        user_query = request.form.get("query")
        print("app.py: user_query is: " + user_query)
        results = findByHSCode.findByHSCode(user_query, data_dict)  # Call the Python function
    return render_template("hscode_search.html", results=results, user_query=user_query)


@app.route("/sccode_search", methods=["GET", "POST"])
def sccode_search():
    print('Request for sccode_search page received')
    results = None
    user_query = None
    if request.method == "POST":
        user_query = request.form.get("query")
        print("app.py: user_query is: " + user_query)
        results = findBySCCode.findBySCCode(user_query,data_dict,scToHSMapping)
    return render_template("sccode_search.html", results=results, user_query=user_query)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/vector_store_search", methods=["GET", "POST"])
def vector_store_search():
    print('Request for vector search page received')
    hsCodes_of_results = None
    user_query = None
    if request.method == "POST":
        user_query = request.form.get("query")
        user_query = user_query[:500] # cap to 500 characters to avoid accidential/malicious long query which can incur high embedding costs
        toks.updateTokens(user_query)
        print("app.py: user_query is: " + user_query)
        hsCodes_of_results = vectorStoreSearch.vectorStoreSearch(user_query, data_dict, vectorstore, ids_hscodes_dict)  # Call the Python function
        print("no. of results:  " + str(len(hsCodes_of_results)))
    return render_template("vector_store_search.html", results=hsCodes_of_results, user_query=user_query)



if __name__ == '__main__':
   app.run()
