import os
import json
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
Bootstrap(app)

# File paths
AGENT_FILE = "agents.json"
LOG_FILE = "server_logs.txt"

# Logging configuration
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# JSON file operations
def load_json(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

# Load data on startup
agents = load_json(AGENT_FILE)

# Endpoint to register an agent
@app.route('/register', methods=['POST'])
def register_agent():
    data = request.json
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({"error": "agent_id is required"}), 400

    if agent_id not in agents:
        agents[agent_id] = {"policies": [], "logs": []}
        save_json(AGENT_FILE, agents)
        logging.info(f"New agent registered: {agent_id}")
        return jsonify({"message": f"Agent {agent_id} registered successfully"}), 200
    return jsonify({"message": f"Agent {agent_id} already exists"}), 200

# Endpoint to get agent policies
@app.route('/get_policy/<agent_id>', methods=['GET'])
def get_policy(agent_id):
    if agent_id not in agents:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify({"policies": agents[agent_id]["policies"]}), 200

# Endpoint to receive logs from agents
@app.route('/logs', methods=['POST'])
def receive_logs():
    data = request.json
    agent_id = data.get('agent_id')
    logs = data.get('logs')
    if not agent_id or not logs:
        return jsonify({"error": "agent_id and logs are required"}), 400

    if agent_id in agents:
        agents[agent_id]["logs"].extend(logs)
        save_json(AGENT_FILE, agents)
        logging.info(f"Logs received from {agent_id}: {logs}")
        return jsonify({"message": "Logs received successfully"}), 200
    else:
        return jsonify({"error": "Agent not registered"}), 404

# Homepage: Agent management
@app.route('/')
def index():
    return render_template('index.html', agents=agents)

# Add a rule for an agent
@app.route('/add_rule/<agent_id>', methods=['GET', 'POST'])
def add_rule(agent_id):
    if agent_id not in agents:
        flash(f"Agent {agent_id} not found", "danger")
        return redirect(url_for('index'))

    form = RuleForm()
    if form.validate_on_submit():
        rule = {
            "name": form.name.data,
            "directory": form.directory.data,
            "action": form.action.data
        }
        agents[agent_id]["policies"].append(rule)
        save_json(AGENT_FILE, agents)
        logging.info(f"Rule added for {agent_id}: {rule}")
        flash("Rule added successfully", "success")
        return redirect(url_for('index'))

    return render_template('add_rule.html', form=form, agent_id=agent_id)

# Delete a rule
@app.route('/delete_rule/<agent_id>/<rule_name>', methods=['POST'])
def delete_rule(agent_id, rule_name):
    if agent_id in agents:
        agents[agent_id]["policies"] = [r for r in agents[agent_id]["policies"] if r["name"] != rule_name]
        save_json(AGENT_FILE, agents)
        logging.info(f"Rule deleted for {agent_id}: {rule_name}")
        flash("Rule deleted successfully", "success")
    return redirect(url_for('index'))

# View logs of a specific agent
@app.route('/view_logs/<agent_id>')
def view_logs(agent_id):
    if agent_id not in agents:
        flash(f"Agent {agent_id} not found", "danger")
        return redirect(url_for('index'))
    logs = agents[agent_id]["logs"]
    return render_template('view_logs.html', agent_id=agent_id, logs=logs)

# View server logs
@app.route('/server_logs')
def server_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            logs = f.readlines()
    else:
        logs = []
    return render_template('server_logs.html', logs=logs)

# Flask-WTF form
class RuleForm(FlaskForm):
    name = StringField('Rule Name', validators=[DataRequired()])
    directory = StringField('Directory', validators=[DataRequired()])
    action = SelectField('Action', choices=[('monitor', 'Monitor'), ('block', 'Block')], validators=[DataRequired()])
    submit = SubmitField('Add Rule')

if __name__ == '__main__':
    logging.info("Server started")
    app.run(host='0.0.0.0', port=5002, debug=True)
