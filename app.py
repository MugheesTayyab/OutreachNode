import os
import uuid
import json
import logging
import threading
from collections import Counter
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from config.settings import BASE_DIR, INPUT_DIR, OUTPUT_DIR, AUDIO_DIR
from tools.excel_tool import read_csv
from tools.email_tool import send_email
from tools.tts_tool import generate_audio
from tools.document_tool import extract_text
from middleware.state_manager import StateManager
from middleware.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'outreachnode-secret-key-12345'
app.config['UPLOAD_FOLDER'] = INPUT_DIR

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

# ── Page Routes ──

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    return redirect(url_for('start_campaign'))

@app.route('/start-campaign')
def start_campaign():
    campaigns = StateManager.list_campaigns()
    templates = StateManager.list_templates()
    saved = StateManager.load_settings()
    return render_template('start_campaign.html', campaigns=campaigns, templates=templates, saved=saved)

@app.route('/campaign-history')
def campaign_history():
    campaigns = StateManager.list_campaigns()
    return render_template('campaign_history.html', campaigns=campaigns)

@app.route('/analytics')
def analytics():
    campaigns = StateManager.list_campaigns()
    total_campaigns = len(campaigns)
    total_prospects = sum(c.get('total_prospects', 0) for c in campaigns)
    completed_campaigns = sum(1 for c in campaigns if c.get('status') == 'completed')
    running_campaigns = sum(1 for c in campaigns if c.get('status') == 'running')
    total_tokens = sum(c.get('total_tokens', 0) for c in campaigns)
    total_cost = sum(c.get('total_cost', 0.0) for c in campaigns)
    total_sent = sum(c.get('completed_prospects', 0) for c in campaigns)

    goals = [c.get('settings', {}).get('goal', 'unknown').capitalize() for c in campaigns]
    most_used_goal = Counter(goals).most_common(1)[0][0] if goals else '—'

    return render_template('analytics.html',
        campaigns=campaigns,
        total_campaigns=total_campaigns,
        total_prospects=total_prospects,
        completed_campaigns=completed_campaigns,
        running_campaigns=running_campaigns,
        most_used_goal=most_used_goal,
        total_tokens=total_tokens,
        total_cost=total_cost,
        total_sent=total_sent
    )

@app.route('/notifications')
def notifications():
    campaigns = StateManager.list_campaigns()
    suppressed = StateManager.list_suppressed()
    notification_list = []
    for camp in campaigns:
        cid = camp.get('campaign_id', '???')
        status = camp.get('status', 'unknown')
        goal = camp.get('settings', {}).get('goal', 'campaign').capitalize()
        count = camp.get('total_prospects', 0)

        if status == 'completed':
            notification_list.append({
                'type': 'completed',
                'title': f'Campaign {cid} Completed',
                'message': f'{goal} campaign with {count} prospects finished successfully. Tokens: {camp.get("total_tokens", 0)}, Cost: ${camp.get("total_cost", 0)}',
                'timestamp': 'Recently'
            })
        elif status == 'running':
            notification_list.append({
                'type': 'started',
                'title': f'Campaign {cid} Running',
                'message': f'{goal} campaign with {count} prospects is currently in progress.',
                'timestamp': 'Now'
            })
        elif status in ('failed', 'cancelled'):
            notification_list.append({
                'type': 'failed',
                'title': f'Campaign {cid} {status.title()}',
                'message': f'{goal} campaign encountered an error or was cancelled.',
                'timestamp': 'Recently'
            })
        else:
            notification_list.append({
                'type': 'info',
                'title': f'Campaign {cid} — {status.title()}',
                'message': f'{goal} campaign with {count} prospects is {status}.',
                'timestamp': 'Recently'
            })

    return render_template('notifications.html', notifications=notification_list, suppressed=suppressed)

@app.route('/settings')
def settings_page():
    saved = StateManager.load_settings()
    return render_template('settings.html', saved=saved)

@app.route('/campaign/<campaign_id>/pipeline')
def pipeline(campaign_id):
    state = StateManager.load_state(campaign_id)
    if not state:
        return redirect(url_for('campaign_history'))
    return render_template('pipeline.html', campaign_id=campaign_id)

@app.route('/campaign/<campaign_id>/results')
def results(campaign_id):
    state = StateManager.load_state(campaign_id)
    if not state:
        return redirect(url_for('campaign_history'))
    return render_template('results.html', campaign=state)

# ── API: Campaign ──

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
        return jsonify({"filename": file.filename, "content": text, "length": len(text)})
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
            return jsonify({"filepath": filepath, "count": len(prospects), "headers": headers, "preview": preview_data})
        except Exception as e:
            return jsonify({"error": f"Failed to parse file: {str(e)}"}), 500
    return jsonify({"error": "Invalid file format. CSV and Excel allowed"}), 400

@app.route('/api/start', methods=['POST'])
def api_start():
    data = request.json or {}
    filepath = data.get("filepath")
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Valid campaign source file required"}), 400

    campaign_id = str(uuid.uuid4())[:8]
    prospects = read_csv(filepath)

    settings = {
        "sender_name": data.get("sender_name", "Mughees Tayyab"),
        "sender_role": data.get("sender_role", "Founder"),
        "sender_company": data.get("sender_company") or "Outreach Node",
        "tone": data.get("tone", "friendly"),
        "goal": data.get("goal", "partnership"),
        "custom_prompt": data.get("custom_prompt", ""),
        "auto_generate_audio": data.get("auto_generate_audio", False),
        "prompt_doc_content": data.get("prompt_doc_content", ""),
        "prompt_doc_filename": data.get("prompt_doc_filename", ""),
        "tags": data.get("tags", ""),
        "ab_test": data.get("ab_test", False),
        "generate_followups": data.get("generate_followups", False),
        "followup_delay_1": data.get("followup_delay_1", 3),
        "followup_delay_2": data.get("followup_delay_2", 7),
        "followup_delay_3": data.get("followup_delay_3", 14)
    }

    StateManager.init_campaign(campaign_id, prospects, settings)

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

    success, error = send_email(to_email, subject, body, campaign_id=campaign_id)

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
        StateManager.update_prospect(campaign_id, int(prospect_id), {"audio_path": audio_url})
    return jsonify({"audio_url": audio_url})

@app.route('/api/download/<campaign_id>', methods=['GET'])
def api_download(campaign_id):
    filename = f"campaign_{campaign_id}.xlsx"
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        return "Excel file not found. Campaign may still be running.", 404
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

# ── API: Unsubscribe ──

@app.route('/unsubscribe', methods=['GET', 'POST'])
def unsubscribe():
    if request.method == 'POST':
        email = request.form.get("email", "")
        if email:
            StateManager.add_suppressed(email)
            return render_template('unsubscribe.html', message="You have been unsubscribed successfully.")
        return render_template('unsubscribe.html', message="Invalid email address.")
    email = request.args.get("email", "")
    return render_template('unsubscribe.html', email=email, message=None)

@app.route('/api/suppressed', methods=['GET'])
def api_suppressed():
    return jsonify({"emails": StateManager.list_suppressed()})

# ── API: Campaign Pause / Resume / Cancel ──

@app.route('/api/pause-campaign/<campaign_id>', methods=['POST'])
def api_pause_campaign(campaign_id):
    state = StateManager.load_state(campaign_id)
    if not state:
        return jsonify({"error": "Campaign not found"}), 404
    if state.get("status") != "running":
        return jsonify({"error": "Campaign is not running"}), 400
    state["status"] = "paused"
    StateManager.save_state(campaign_id, state)
    return jsonify({"success": True, "status": "paused"})

@app.route('/api/resume-campaign/<campaign_id>', methods=['POST'])
def api_resume_campaign(campaign_id):
    state = StateManager.load_state(campaign_id)
    if not state:
        return jsonify({"error": "Campaign not found"}), 404
    if state.get("status") != "paused":
        return jsonify({"error": "Campaign is not paused"}), 400
    state["status"] = "running"
    StateManager.save_state(campaign_id, state)
    return jsonify({"success": True, "status": "running"})

@app.route('/api/cancel-campaign/<campaign_id>', methods=['POST'])
def api_cancel_campaign(campaign_id):
    state = StateManager.load_state(campaign_id)
    if not state:
        return jsonify({"error": "Campaign not found"}), 404
    StateManager.set_campaign_cancel_requested(campaign_id)
    return jsonify({"success": True, "status": "cancelling"})

# ── API: Templates ──

@app.route('/api/templates', methods=['GET'])
def api_list_templates():
    return jsonify({"templates": StateManager.list_templates()})

@app.route('/api/templates', methods=['POST'])
def api_save_template():
    data = request.json or {}
    name = data.get("name", "Unnamed Template")
    config = data.get("config", {})
    tid = StateManager.save_template(name, config)
    return jsonify({"success": True, "template_id": tid})

@app.route('/api/templates/<template_id>', methods=['GET'])
def api_get_template(template_id):
    tmpl = StateManager.load_template(template_id)
    if not tmpl:
        return jsonify({"error": "Template not found"}), 404
    return jsonify(tmpl)

@app.route('/api/templates/<template_id>', methods=['DELETE'])
def api_delete_template(template_id):
    StateManager.delete_template(template_id)
    return jsonify({"success": True})

# ── API: Export / Import Campaign ──

@app.route('/api/export-campaign/<campaign_id>', methods=['GET'])
def api_export_campaign(campaign_id):
    state = StateManager.load_state(campaign_id)
    if not state:
        return jsonify({"error": "Campaign not found"}), 404
    export_data = {
        "settings": state.get("settings"),
        "total_tokens": state.get("total_tokens", 0),
        "total_cost": state.get("total_cost", 0),
        "tags": state.get("tags", ""),
        "campaign_id": campaign_id
    }
    return jsonify(export_data)

@app.route('/api/import-campaign', methods=['POST'])
def api_import_campaign():
    data = request.json or {}
    settings = data.get("settings", {})
    if not settings:
        return jsonify({"error": "No campaign settings in import data"}), 400
    new_id = str(uuid.uuid4())[:8]
    state = {
        "campaign_id": new_id,
        "status": "imported",
        "settings": settings,
        "research_plan": {},
        "orchestrator_duration": 0,
        "current_stage": "imported",
        "total_tokens": data.get("total_tokens", 0),
        "total_cost": data.get("total_cost", 0),
        "tags": data.get("tags", ""),
        "prospects": []
    }
    StateManager.save_state(new_id, state)
    return jsonify({"success": True, "campaign_id": new_id})

# ── API: Settings ──

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    return jsonify(StateManager.load_settings())

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    data = request.json or {}
    current = StateManager.load_settings()
    current.update(data)
    StateManager.save_settings(current)
    return jsonify({"success": True})

@app.route('/api/save-prospect', methods=['POST'])
def api_save_prospect():
    data = request.json or {}
    campaign_id = data.get("campaign_id")
    prospect_id = data.get("prospect_id")
    subject = data.get("subject")
    body = data.get("body")
    follow_ups = data.get("follow_ups")

    if not campaign_id or prospect_id is None:
        return jsonify({"error": "Missing campaign_id or prospect_id"}), 400

    updates = {}
    if subject is not None:
        updates["email_subject"] = subject
    if body is not None:
        updates["email_body"] = body
    if follow_ups is not None:
        updates["follow_ups"] = follow_ups

    StateManager.update_prospect(campaign_id, int(prospect_id), updates)
    return jsonify({"success": True})

@app.route('/api/deliverability-check', methods=['POST'])
def api_deliverability_check():
    data = request.json or {}
    subject = data.get("subject", "")
    body = data.get("body", "")
    sender_email = data.get("sender_email")
    
    if not sender_email:
        settings = StateManager.load_settings()
        sender_email = settings.get("smtp_user", "")

    from tools.deliverability import analyze_email
    report = analyze_email(subject, body, sender_email)
    return jsonify(report)

# ── API: Campaign Delete ──

@app.route('/api/delete-campaign/<campaign_id>', methods=['DELETE'])
def api_delete_campaign(campaign_id):
    StateManager.delete_campaign(campaign_id)
    return jsonify({"success": True})

# ── API: Campaign Stats (for analytics enrichment) ──

@app.route('/api/campaigns-stats', methods=['GET'])
def api_campaigns_stats():
    campaigns = StateManager.list_campaigns()
    all_scores = []
    for c in campaigns:
        state = StateManager.load_state(c["campaign_id"])
        if state:
            scores = [p.get("proofread_score", 0) for p in state.get("prospects", []) if p.get("proofread_score", 0) > 0]
            all_scores.extend(scores)
    avg_proofread = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    return jsonify({
        "avg_proofread_score": avg_proofread,
        "total_tokens": sum(c.get("total_tokens", 0) for c in campaigns),
        "total_cost": round(sum(c.get("total_cost", 0.0) for c in campaigns), 4)
    })

# ── API: Clear All Campaigns ──

@app.route('/api/clear-all', methods=['DELETE'])
def api_clear_all():
    StateManager.clear_all_campaigns()
    return jsonify({"success": True})

# ── API: CSV Template Download ──

@app.route('/api/csv-template', methods=['GET'])
def api_csv_template():
    import io
    from flask import Response
    csv_content = "name,email,company,title,linkedin_url\nJohn Doe,john@example.com,Acme Corp,CEO,https://linkedin.com/in/johndoe\nJane Smith,jane@example.com,TechStart,CTO,https://linkedin.com/in/janesmith\n"
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=outreach-node-template.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
