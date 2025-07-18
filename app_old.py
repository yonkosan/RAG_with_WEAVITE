# import os
# from flask import Flask, request, render_template, redirect, url_for, flash
# from werkzeug.utils import secure_filename

# #  The UPLOAD_FOLDER is where we will store the uploaded files and 
# # the ALLOWED_EXTENSIONS is the set of allowed file extensions.
# UPLOAD_FOLDER = '/upload'
# os.makedirs(UPLOAD_FOLDER,exist_ok=True)
# ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'json'}

# app = Flask(__name__)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# @app.route('/', methods=['POST'] )
# def index():
#     return render_template('index.html')

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if request.method == 'POST':
#         # check if the post request has the file part
#         if 'file' not in request.files:
#             flash('No file part')
#             return redirect(request.url)
#         file = request.files['file']
#         # If the user does not select a file, the browser submits an
#         # empty file without a filename.
#         if file.filename == '':
#             flash('No selected file','error')
#             return redirect(request.url)
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             return redirect(url_for('download_file', name=filename))
#     return

# from flask import send_from_directory
# # be able to serve the uploaded files so they can be downloaded by users
# @app.route('/uploads/<name>')
# def download_file(name):
#     return send_from_directory(app.config["UPLOAD_FOLDER"], name)

# if __name__=="__main__" :
#     app.run(debug=True)

# import weaviate

# client = weaviate.connect_to_local()

# print(client.is_ready())  # Should print: `True`

# client.close()  # Free up resources


import os
from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import weaviate

# Configuration
UPLOAD_FOLDER = 'uploads'  # Changed to relative path
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'json'}

app = Flask(__name__)
app.secret_key = 'my_secret_key'  # Added secret key for flash messages
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If the user does not select a file, the browser submits an
        # empty file without a filename
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            flash('File uploaded successfully', 'success')
            return redirect(url_for('download_file', name=filename))
        
        else:
            flash('File type not allowed', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/uploads/<name>')
def download_file(name):
    try:
        return send_from_directory(app.config["UPLOAD_FOLDER"], name)
    except FileNotFoundError:
        flash('File not found', 'error')
        return redirect(url_for('index'))

# Weaviate Connection
def setup_weaviate_client():
    try:
        client = weaviate.connect_to_local()
        print("Weaviate client connected successfully")
        print("Weaviate client ready:", client.is_ready())
        return client
    except Exception as e:
        print(f"Error connecting to Weaviate: {e}")
        return None

if __name__ == "__main__":
    # Setup Weaviate client
    weaviate_client = setup_weaviate_client()
    
    try:
        # Run Flask app
        app.run(debug=True)
    finally:
        # Ensure client is closed
        if weaviate_client:
            weaviate_client.close()

#Implementing functions to parse different document formats.
from pdfminer.high_level import extract_text
from docx import Document
import json

def parse_pdf(file_path):
    return extract_text(file_path)

def parse_docx(file_path):
    doc = Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

def parse_txt(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def parse_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)
    
import weaviate
from weaviate.classes.config import Configure

client = weaviate.connect_to_local()

questions = client.collections.create(
    name="Question",
    vectorizer_config=Configure.Vectorizer.text2vec_ollama(     # Configure the Ollama embedding integration
        api_endpoint="http://host.docker.internal:11434",       # Allow Weaviate from within a Docker container to contact your Ollama instance
        model="nomic-embed-text",                               # The model to use
    ),
    generative_config=Configure.Generative.ollama(              # Configure the Ollama generative integration
        api_endpoint="http://host.docker.internal:11434",       # Allow Weaviate from within a Docker container to contact your Ollama instance
        model="llama3.2",                                       # The model to use
    )
)

client.close()  # Free up resources