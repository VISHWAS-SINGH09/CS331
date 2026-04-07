"""
Flask Application with Business Logic Layer Integration
Demonstrates how BLL modules integrate with the presentation layer (UI).
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent))

from bll_dispute_management import DisputeManagementBLL
from bll_forensic_analysis import ForensicAnalysisBLL
from bll_decision_engine import DecisionEngineBLL
from bll_user_management import UserManagementBLL
from bll_notification import NotificationBLL

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize BLL modules
dispute_bll = DisputeManagementBLL()
forensic_bll = ForensicAnalysisBLL()
decision_bll = DecisionEngineBLL()
user_bll = UserManagementBLL()
notification_bll = NotificationBLL()


# Simple HTML template for testing
HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>VeriSupport - BLL Demo</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .section {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .endpoint {
            background: #f8f9fa;
            padding: 10px;
            margin: 10px 0;
            border-left: 4px solid #007bff;
        }
        .method {
            display: inline-block;
            padding: 2px 8px;
            background: #007bff;
            color: white;
            border-radius: 3px;
            font-size: 12px;
            margin-right: 10px;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <h1>VeriSupport - Business Logic Layer Demo</h1>
    
    <div class="section">
        <h2>Available API Endpoints</h2>
        
        <div class="endpoint">
            <span class="method">POST</span>
            <code>/api/dispute/submit</code>
            <p>Submit a new dispute with image evidence</p>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span>
            <code>/api/forensic/analyze</code>
            <p>Analyze image for manipulation</p>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span>
            <code>/api/decision/calculate</code>
            <p>Calculate trust score and decision</p>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span>
            <code>/api/user/register</code>
            <p>Register a new user</p>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span>
            <code>/api/user/login</code>
            <p>Authenticate user</p>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span>
            <code>/api/user/profile/:user_id</code>
            <p>Get user profile</p>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span>
            <code>/api/notification/send</code>
            <p>Send notification to user</p>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span>
            <code>/api/notification/history/:user_id</code>
            <p>Get notification history</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Business Logic Layer Features</h2>
        <ul>
            <li>Input validation and business rules</li>
            <li>Data transformation between layers</li>
            <li>Business logic orchestration</li>
            <li>Error handling and validation</li>
            <li>Integration between modules</li>
        </ul>
    </div>
</body>
</html>
"""


@app.route('/')
def home():
    """Home page with API documentation"""
    return render_template_string(HOME_TEMPLATE)


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'bll_modules': {
            'dispute_management': 'operational',
            'forensic_analysis': 'operational',
            'decision_engine': 'operational',
            'user_management': 'operational',
            'notification': 'operational'
        }
    })


# Dispute Management Endpoints

@app.route('/api/dispute/submit', methods=['POST'])
def submit_dispute():
    """
    Submit a dispute
    Demonstrates: Dispute Management BLL integration
    """
    try:
        data = request.get_json()
        
        # BLL handles validation and processing
        result = dispute_bll.process_dispute(data)
        
        if not result.get('success'):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/dispute/validate', methods=['POST'])
def validate_dispute():
    """
    Validate dispute data
    Demonstrates: Input validation in BLL
    """
    try:
        data = request.get_json()
        
        # BLL validates input
        validation = dispute_bll.validate_dispute_submission(data)
        
        return jsonify(validation), 200
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [str(e)]
        }), 500


@app.route('/api/dispute/status/<dispute_id>', methods=['GET'])
def get_dispute_status(dispute_id):
    """
    Get dispute status
    Demonstrates: Data retrieval through BLL
    """
    try:
        result = dispute_bll.get_dispute_status(dispute_id)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Forensic Analysis Endpoints

@app.route('/api/forensic/analyze', methods=['POST'])
def analyze_image():
    """
    Analyze image for manipulation
    Demonstrates: Forensic Analysis BLL integration
    """
    try:
        # Get image data from request
        if 'image' in request.files:
            image_data = request.files['image'].read()
        else:
            data = request.get_json()
            image_data = data.get('image_data', b'')
        
        reference_id = request.form.get('reference_id', 'TEST-001')
        
        # BLL handles validation and analysis
        result = forensic_bll.analyze_image(image_data, reference_id)
        
        if not result.get('success'):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Decision Engine Endpoints

@app.route('/api/decision/calculate', methods=['POST'])
def calculate_decision():
    """
    Calculate trust score and decision
    Demonstrates: Decision Engine BLL integration
    """
    try:
        data = request.get_json()
        
        # BLL handles validation and calculation
        result = decision_bll.calculate_decision(
            metadata_score=float(data.get('metadata_score', 0)),
            ela_score=float(data.get('ela_score', 0)),
            ai_score=float(data.get('ai_score', 0.75)),
            order_amount=float(data.get('order_amount', 0)),
            user_history=data.get('user_history')
        )
        
        if not result.get('success'):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/decision/statistics', methods=['GET'])
def get_decision_statistics():
    """
    Get decision statistics
    Demonstrates: Business analytics through BLL
    """
    try:
        result = decision_bll.get_decision_statistics()
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# User Management Endpoints

@app.route('/api/user/register', methods=['POST'])
def register_user():
    """
    Register a new user
    Demonstrates: User Management BLL integration
    """
    try:
        data = request.get_json()
        
        # BLL handles validation and registration
        result = user_bll.register_user(data)
        
        if not result.get('success'):
            return jsonify(result), 400
        
        return jsonify(result), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/login', methods=['POST'])
def login_user():
    """
    Authenticate user
    Demonstrates: Authentication through BLL
    """
    try:
        data = request.get_json()
        
        # BLL handles authentication
        result = user_bll.authenticate_user(
            username=data.get('username', ''),
            password=data.get('password', '')
        )
        
        if not result.get('success'):
            return jsonify(result), 401
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/profile/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    """
    Get user profile
    Demonstrates: Data retrieval and transformation through BLL
    """
    try:
        result = user_bll.get_user_profile(user_id)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/profile/<user_id>', methods=['PUT'])
def update_user_profile(user_id):
    """
    Update user profile
    Demonstrates: Data validation and update through BLL
    """
    try:
        data = request.get_json()
        
        # BLL handles validation and update
        result = user_bll.update_user_profile(user_id, data)
        
        if not result.get('success'):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Notification Endpoints

@app.route('/api/notification/send', methods=['POST'])
def send_notification():
    """
    Send notification
    Demonstrates: Notification BLL integration
    """
    try:
        data = request.get_json()
        
        # BLL handles notification logic
        result = notification_bll.send_dispute_notification(
            user_id=data.get('user_id', ''),
            dispute_id=data.get('dispute_id', ''),
            notification_type=data.get('type', 'email'),
            dispute_status=data.get('status', 'Pending')
        )
        
        if not result.get('success'):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/notification/history/<user_id>', methods=['GET'])
def get_notification_history(user_id):
    """
    Get notification history
    Demonstrates: Data retrieval through BLL
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        result = notification_bll.get_notification_history(user_id, limit)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/notification/preferences/<user_id>', methods=['PUT'])
def update_notification_preferences(user_id):
    """
    Update notification preferences
    Demonstrates: Preference management through BLL
    """
    try:
        data = request.get_json()
        
        # BLL handles validation and update
        result = notification_bll.update_notification_preferences(user_id, data)
        
        if not result.get('success'):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("Starting VeriSupport BLL Demo Application")
    print("-" * 50)
    print("Server running on: http://localhost:5000")
    print("API Documentation: http://localhost:5000")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
