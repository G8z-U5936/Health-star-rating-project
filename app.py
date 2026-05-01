from flask import Flask, render_template, request, url_for, Response, redirect, session, jsonify
import os
import json
import uuid

from main import analyze_product_with_status

app = Flask(__name__)
app.secret_key = 'healthify-secret-key-change-in-production'

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Store results temporarily (in production, use Redis or database)
analysis_results = {}


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files.get("image")

    if not file or file.filename == "":
        return "No image uploaded"

    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Save image
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)
    
    # Store job info
    analysis_results[job_id] = {
        "filepath": filepath,
        "filename": file.filename,
        "status": "pending",
        "result": None
    }
    
    # Redirect to loading page
    return redirect(url_for('loading', job_id=job_id))


@app.route('/loading/<job_id>')
def loading(job_id):
    if job_id not in analysis_results:
        return "Job not found", 404
    
    job = analysis_results[job_id]
    return render_template(
        "loading.html",
        job_id=job_id,
        image=url_for('static', filename=f'uploads/{job["filename"]}')
    )


@app.route('/stream/<job_id>')
def stream(job_id):
    if job_id not in analysis_results:
        return "Job not found", 404
    
    job = analysis_results[job_id]
    filepath = job["filepath"]
    
    # Pre-compute redirect URL before entering generator (avoids app context issues)
    result_url = f"/result/{job_id}"
    
    def generate():
        try:
            for status, data in analyze_product_with_status(filepath):
                if status == "complete":
                    analysis_results[job_id]["result"] = data
                    analysis_results[job_id]["status"] = "complete"
                    yield f"data: {json.dumps({'status': 'complete', 'redirect': result_url})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'progress', 'step': status, 'message': data})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/result/<job_id>')
def result(job_id):
    if job_id not in analysis_results:
        return "Job not found", 404
    
    job = analysis_results[job_id]
    if job["status"] != "complete" or not job["result"]:
        return redirect(url_for('loading', job_id=job_id))
    
    result_data = job["result"]
    return render_template(
        "result.html",
        image=url_for('static', filename=f'uploads/{job["filename"]}'),
        stars=result_data["stars"],
        product_name=result_data["product_name"],
        nutrition=result_data["nutrition"]
    )


if __name__ == "__main__":
    app.run(debug=True, threaded=True)