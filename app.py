import os
import uuid
import logging
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from config.settings import BASE_DIR, INPUT_DIR, OUTPUT_DIR, AUDIO_DIR
from tools.excel_tool import read_csv
from tools.email_tool import send_email
from tools.tts_tool import generate_audio
from tools.document_tool import extract_text
from middleware.state_manager import StateManager
from middleware.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'outreachnode-secret-key-12345'
app.config['UPLOAD_FOLDER'] = INPUT_DIR

# Keep track of active campaigns running in threads
active_threads = {}

def run_campaign_background(campaign_id: str):
    try:
        orchestrator = Orchestrator()
        orchestrator.run_campaign(campaign_id)
    except Exception as e:
        logger.error(f"Error running campaign in background: {str(e)}")
        state = StateManager.load_state(campaign_id)
        if state:
            state["status"] = "failed"
            from middleware.orchestrator import is_api_key_or_rate_limit_error
            if is_api_key_or_rate_limit_error(e):
                state["error_type"] = "api_key_limit_reached"
                state["error_message"] = f"API Key or Rate Limit reached: {str(e)}"
            else:
                state["error_type"] = "general_error"
                state["error_message"] = str(e)
            StateManager.save_state(campaign_id, state)

@app.route('/')
def dashboard():
    campaigns = StateManager.list_campaigns()
    return render_template('dashboard.html', campaigns=campaigns)

@app.route('/campaign/<campaign_id>/pipeline')
def pipeline(campaign_id):
    state = StateManager.load_state(campaign_id)
    if not state:
        return redirect(url_for('dashboard'))
    return render_template('pipeline.html', campaign_id=campaign_id)

@app.route('/campaign/<campaign_id>/results')
def results(campaign_id):
    state = StateManager.load_state(campaign_id)
    if not state:
        return redirect(url_for('dashboard'))
    return render_template('results.html', campaign=state)

@app.route('/api/upload-prompt-doc', methods=['POST'])
def api_upload_prompt_doc():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    allowed_exts = ('.pdf', '.docx', '.txt')
    if not file.filename.lower().endswith(allowed_exts):
        return jsonify({"error": "Invalid format. Allowed: PDF, DOCX, TXT"}), 400

    filename = secure_filename(f"promptdoc_{uuid.uuid4()}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        text = extract_text(filepath)
        if not text.strip():
            return jsonify({"error": "No readable text found in document"}), 400
        max_chars = 15000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[...content truncated to fit context window]"
        return jsonify({
            "filename": file.filename,
            "content": text,
            "length": len(text)
        })
    except Exception as e:
        logger.error(f"Failed to parse prompt document: {str(e)}")
        return jsonify({"error": f"Failed to read document: {str(e)}"}), 500


@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    allowed_exts = ('.csv', '.xlsx', '.xls')
    if file and file.filename.lower().endswith(allowed_exts):
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            from tools.excel_tool import get_csv_preview
            headers, preview_data = get_csv_preview(filepath)
            prospects = read_csv(filepath)
            # Return first 5 for preview
            return jsonify({
                "filepath": filepath,
                "count": len(prospects),
                "headers": headers,
                "preview": preview_data
            })
        except Exception as e:
            return jsonify({"error": f"Failed to parse file: {str(e)}"}), 500
            
    return jsonify({"error": "Invalid file format. CSV and Excel allowed"}), 400

@app.route('/api/start', methods=['POST'])
def api_start():
    data = request.json or {}
    filepath = data.get("filepath")
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Valid campaign source file required"}), 400
        
    # Generate campaign ID
    campaign_id = str(uuid.uuid4())[:8]
    
    # Load prospects
    prospects = read_csv(filepath)
    
    # Construct settings
    settings = {
        "sender_name": data.get("sender_name", "Mughees Tayyab"),
        "sender_role": data.get("sender_role", "Founder"),
        "sender_company": data.get("sender_company") or "Outreach Node",
        "tone": data.get("tone", "friendly"),
        "goal": data.get("goal", "partnership"),
        "custom_prompt": data.get("custom_prompt", ""),
        "auto_generate_audio": data.get("auto_generate_audio", False),
        "prompt_doc_content": data.get("prompt_doc_content", ""),
        "prompt_doc_filename": data.get("prompt_doc_filename", "")
    }
    
    # Initialize state
    StateManager.init_campaign(campaign_id, prospects, settings)
    
    # Start campaign thread
    thread = threading.Thread(target=run_campaign_background, args=(campaign_id,))
    thread.daemon = True
    thread.start()
    active_threads[campaign_id] = thread
    
    return jsonify({
        "campaign_id": campaign_id,
        "redirect_url": url_for('pipeline', campaign_id=campaign_id)
    })

@app.route('/api/status/<campaign_id>', methods=['GET'])
def api_status(campaign_id):
    state = StateManager.load_state(campaign_id)
    if not state:
        return jsonify({"error": "Campaign not found"}), 404
    return jsonify(state)

@app.route('/api/send-email', methods=['POST'])
def api_send_email():
    data = request.json or {}
    to_email = data.get("email")
    subject = data.get("subject")
    body = data.get("body")
    campaign_id = data.get("campaign_id")
    prospect_id = data.get("prospect_id")
    
    if not all([to_email, subject, body]):
        return jsonify({"error": "Missing email, subject, or body"}), 400
        
    success, error = send_email(to_email, subject, body)
    
    # Update state if campaign parameters are provided
    if success and campaign_id and prospect_id is not None:
        StateManager.update_prospect(campaign_id, int(prospect_id), {
            "email_sent": True,
            "status": "sent"
        })
        
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"error": error or "Failed to send email"}), 500

@app.route('/api/generate-audio', methods=['POST'])
def api_generate_audio():
    data = request.json or {}
    text = data.get("text")
    campaign_id = data.get("campaign_id")
    prospect_id = data.get("prospect_id")
    
    if not text:
        return jsonify({"error": "Text content required"}), 400
        
    filename = f"audio_{campaign_id}_{prospect_id}.mp3"
    audio_full_path = os.path.join(AUDIO_DIR, filename)
    generate_audio(text, audio_full_path)
    
    audio_url = f"/static/audio/{filename}"
    if campaign_id and prospect_id is not None:
        StateManager.update_prospect(campaign_id, int(prospect_id), {
            "audio_path": audio_url
        })
        
    return jsonify({"audio_url": audio_url})

@app.route('/api/download/<campaign_id>', methods=['GET'])
def api_download(campaign_id):
    filename = f"campaign_{campaign_id}.xlsx"
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        return "Excel file not found. Campaign may still be running.", 404
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
