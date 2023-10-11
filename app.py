# app.py
import subprocess
import uuid
from flask import Flask, request, jsonify, send_file
import requests
from werkzeug.utils import secure_filename
import os
import ffmpeg
from scipy.spatial import distance


def create_app():
    app = Flask(__name__, static_folder='uploads', static_url_path='/uploads')
    app.config['UPLOAD_FOLDER'] = '/app/uploads/'
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    # Other setup code...
    return app


app = create_app()


@app.route('/', methods=['GET'])
def homepage():
    return "Homepage"


@app.route('/hello', methods=['GET'])
def hello():
    return "Hello"


from urllib.parse import urlparse
from PyPDF2 import PdfReader
from io import BytesIO
import logging 

@app.route('/extract_text', methods=['POST'])
def extract_text():
    data = request.json
        
    # Validate JSON payload
    if 'url' not in data:
        logging.error("Missing URL in JSON payload")
        return jsonify({'error': 'Missing URL'}), 400
        
    pdf_url = data['url']
        
    # Validate URL
    try:
        a = urlparse(pdf_url)
        if not all([a.scheme, a.netloc]):
            raise ValueError("Invalid URL")
    except ValueError as e:
        logging.error("Invalid URL: %s", e)
        return jsonify({'error': str(e)}), 400
        
    # Attempt to download the pdf file
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error("Failed to download PDF: %s", e)
        return jsonify({'error': 'Failed to download the PDF file. Error: ' + str(e)}), 400
        
    # Extract text from the downloaded pdf file
    try:
        with BytesIO(response.content) as pdf_file:
            pdf_reader = PdfReader(pdf_file)
            if pdf_reader.is_encrypted:  # Use is_encrypted instead of isEncrypted
                pdf_reader.decrypt('')
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            
            if not text.strip():  # Check if the extracted text is empty or whitespace
                logging.error("No extractable text found in PDF")
                raise ValueError("The PDF does not contain any extractable text")
    except Exception as e:
        logging.error("Failed to extract text: %s", e)
        return jsonify({'error': 'Failed to extract text. Error: ' + str(e)}), 400
        
    return jsonify({'text': text})



import cloudconvert
from flask import Flask, request, jsonify
import requests

cloudconvert.configure(api_key='eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiY2JkODUwNjBjYTUyZTU3OWIyZGNjOGIyNjJjYTQ4NGIwYzI3OTg5YmZlY2I4YTcxZWRhNTc0NjE0MDE4ZmU4NDQ3NGZlMTlhMjkyZTM3NjciLCJpYXQiOjE2OTYxNzY3NzAuODU0ODcyLCJuYmYiOjE2OTYxNzY3NzAuODU0ODc1LCJleHAiOjQ4NTE4NTAzNzAuODQ3NCwic3ViIjoiNjU0NDgxNjYiLCJzY29wZXMiOlsidGFzay53cml0ZSIsInRhc2sucmVhZCJdfQ.RxTh0xCwZ9pOKzw4QpbQ_PEKfpUt3LEwxo-rfvNoySbmD3VIYjnamslK6mZZHzo_TvyprcoYv7aUdqQfMP-X9sAPazb-m5KL3T8NkPd9ZRTI4WfGcupUKD0IZ2bSH-2prQaebp3hCdL6EknL306KhBKT6U63B_gvGcVKEaDO6iTmaLzw1L0QoRg3WL0noRqvJss7mmm8ZE3EjBNyTpiZKzc9ARVdG5kHK8ZWMSsIovLM-uRU6zmvtZv1D8jq-Fputlgu56U03xwdWiKtPdJZfqKsAIkW_wNuQxb1WIYwUEtUpHp_UfpddbImmVQXJWpAkbqMVyXwET50bC3FhqFeiVfddAY3CE1-KNNF5ub_eBjowtiNzvpZFLmEr3XVGItMikArwn0nS4BKBWu7sFUKcMErfzBqPiAEni8vpcQiDBd73iL9nltKHAEY814BtnDiClhji9EilU6emhheHbWW51JU_NGWq57dB9jkBv5N4P_EAKhBGlqhRVGfdSwUXUJrcCMtoE3tP1_JLkfd8tSQeCOLyrfZxmvmk3qVlIKnY8ju1KfPHvpsJRiOLi5lJzxw9JVn8Sq227jyLKGA4cMXHwTF2olc1qDnb7xuvn068iF2K82a4ZqYg8Ccb8O0xuXv4vO1h_ncSkVslj_8nhzV8lNQwVPEbnPJM_DNmfEqhyc')

@app.route('/ppt_to_text', methods=['POST'])
def ppt_to_text():
    data = request.json
    ppt_url = data.get('url')

    if not ppt_url:
        return jsonify(error="URL is required"), 400
    
    try:
        # Create a Job with tasks to import, convert, and export the file
        job = cloudconvert.Job.create(payload={
            "tasks": {
                'import-my-file': {
                    'operation': 'import/url',
                    'url': ppt_url
                },
                'convert-my-file': {
                    'operation': 'convert',
                    'input': 'import-my-file',
                    'output_format': 'txt',
                },
                'export-my-file': {
                    'operation': 'export/url',
                    'input': 'convert-my-file'
                }
            }
        })
        
        # Wait for the job to finish
        job = cloudconvert.Job.wait(id=job['id'])
        
        # Check if 'tasks' is a list and also debug print its value.
        tasks = job.get('tasks', [])
        if not isinstance(tasks, list) or not tasks:
            app.logger.error("'tasks' is not in the expected format: %s", tasks)
            return jsonify(error="Conversion failed"), 400
        
        # Extract export task
        export_task = None
        for task in tasks:
            if task.get('name') == 'export-my-file':
                export_task = task
                break
        
        if not export_task or 'result' not in export_task or 'files' not in export_task['result']:
            app.logger.error("Conversion failed: %s", job)
            return jsonify(error="Conversion failed"), 400
        
        # Check if 'files' is a list and also debug print its value.
        files = export_task['result'].get('files', [])
        if not isinstance(files, list) or not files:
            app.logger.error("'files' is not in the expected format: %s", files)
            return jsonify(error="Conversion failed"), 400
        
        txt_url = files[0].get('url')
        if not txt_url:
            app.logger.error("URL not found in 'files': %s", files)
            return jsonify(error="Conversion failed"), 400
        
        # Download and return the converted text file
        txt_response = requests.get(txt_url)
        if txt_response.status_code != 200:
            app.logger.error("Failed to download converted file: %s", txt_url)
            return jsonify(error="Failed to download converted file"), 400
        
        return jsonify({'text': txt_response.text})

    except Exception as e:
        app.logger.error("Unexpected error: %s", str(e))
        return jsonify(error="Unexpected error occurred"), 500


from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse
from docx import Document
import os


@app.route('/extract_wordtext', methods=['POST'])
def extract_wordtext():
    data = request.json
    
    # Ensure the 'url' key exists in the request
    if 'url' not in data:
        return jsonify({'error': 'Missing URL parameter'}), 400
    
    doc_url = data['url']
    if not doc_url:
        return jsonify({'error': 'URL is empty'}), 400
    
    # Parse the url to get the document name
    try:
        a = urlparse(doc_url)
        if not all([a.scheme, a.netloc, a.path]):
            return jsonify({'error': 'Invalid URL'}), 400
        doc_name = os.path.basename(a.path)
    except Exception as e:
        return jsonify({'error': f'Error parsing URL: {str(e)}'}), 400

    # Download the Word document
    try:
        with requests.get(doc_url, stream=True) as r:
            r.raise_for_status()
            with open(doc_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
    except requests.RequestException as e:
        return jsonify({'error': f'Error downloading Word document: {str(e)}'}), 400

    # Open the Word document and extract text
    try:
        doc = Document(doc_name)
        fullText = [para.text for para in doc.paragraphs]
    except Exception as e:
        return jsonify({'error': f'Error reading Word document: {str(e)}'}), 400
    finally:
        # Always cleanup the downloaded Word document file, if it exists
        if os.path.exists(doc_name):
            os.remove(doc_name)

    # Combine the paragraphs and return them
    return jsonify({'text': '\n'.join(fullText)})

