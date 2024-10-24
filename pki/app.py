from flask import Flask, request, render_template, flash, redirect, url_for
from werkzeug.utils import secure_filename
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from time import time
import os
import random

app = Flask(__name__)
app.secret_key = 'super secret key'  # Needed for flashing messages

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the upload folder exists

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

private_key, public_key = load_keys()

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/process', methods=['POST'])
def process_file():
    if 'pdf_file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    pdf_file = request.files['pdf_file']
    num_loops = request.form.get('num_loops', '1')

    if pdf_file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if not num_loops.isdigit() or int(num_loops) < 1 or int(num_loops) > 1000:
        flash('Number of loops must be between 1 and 1000')
        return redirect(request.url)

    if pdf_file and allowed_file(pdf_file.filename):
        filename = secure_filename(pdf_file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_file.save(pdf_path)

        total_time_start = time()

        with open(pdf_path, 'rb') as f:
            original_pdf_data = f.read()

        verification_status = "Verification successful!"
        for i in range(int(num_loops)):
            # Append a random number to the PDF data
            random_number = random.randint(0, 10000)
            pdf_data = original_pdf_data + str(random_number).encode()

            signature = private_key.sign(
                pdf_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            try:
                public_key.verify(
                    signature,
                    pdf_data,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            except Exception as e:
                verification_status = f"Verification failed: {str(e)}"
                break

        total_time_end = time()
        total_elapsed_time = total_time_end - total_time_start

        return (f"{verification_status}\n"
                f"Total time for all cycles: {total_elapsed_time:.4f} seconds.")

    else:
        flash('Allowed file types are PDF only.')
        return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True)
