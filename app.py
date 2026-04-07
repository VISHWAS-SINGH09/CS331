"""
VeriSupport - Flask Web Application

A professional web application with HTML/CSS/JavaScript frontend
and Flask backend for the VeriSupport platform.

Features:
- Customer Portal (dispute submission)
- Agent Dashboard (dispute review)
- RESTful API endpoints
- Real-time updates

Usage:
    python app.py

Author: VeriSupport Team
Assignment: 6 - CS 331 Software Engineering Lab
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import io
import base64

# Add Assignment 5 to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Assignment 5"))

try:
    from forensic_analysis_service import ForensicAnalysisService
    from decision_engine_service import DecisionEngineService
    HAS_SERVICES = True
except ImportError:
    HAS_SERVICES = False

app = Flask(__name__)
CORS(app)

# Initialize services
if HAS_SERVICES:
    forensic_service = ForensicAnalysisService()
    decision_service = DecisionEngineService()

# In-memory storage (replace with database in production)
disputes = []
dispute_counter = 1


# ═══════════════════════════════════════════════════════════════════
# ROUTES - Customer Portal
# ═══════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Customer Portal - Home Page"""
    return render_template('customer_portal.html')


@app.route('/customer')
def customer_portal():
    """Customer Portal - Main Page"""
    return render_template('customer_portal.html')


@app.route('/my-disputes')
def my_disputes():
    """Customer Portal - My Disputes Page"""
    return render_template('my_disputes.html')


# ═══════════════════════════════════════════════════════════════════
# ROUTES - Agent Dashboard
# ═══════════════════════════════════════════════════════════════════

@app.route('/agent')
def agent_dashboard():
    """Agent Dashboard - Main Page"""
    return render_template('agent_dashboard.html')


@app.route('/agent/review/<dispute_id>')
def agent_review(dispute_id):
    """Agent Dashboard - Review Dispute Page"""
    return render_template('agent_review.html', dispute_id=dispute_id)


# ═══════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'services': {
            'forensic': HAS_SERVICES,
            'decision': HAS_SERVICES
        },
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/dispute/submit', methods=['POST'])
def submit_dispute():
    """Submit a new dispute"""
    global dispute_counter
    
    try:
        # Get form data
        order_id = request.form.get('order_id')
        amount = float(request.form.get('amount', 0))
        description = request.form.get('description', '')
        
        # Get image file
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({'error': 'No image provided'}), 400
        
        image_data = image_file.read()
        
        # Generate dispute ID
        dispute_id = f"DISP-{datetime.now().strftime('%Y%m%d')}-{dispute_counter:04d}"
        dispute_counter += 1
        
        if not HAS_SERVICES:
            # Mock response if services not available
            result = {
                'dispute_id': dispute_id,
                'order_id': order_id,
                'amount': amount,
                'trust_score': 0.75,
                'decision': 'manual_review',
                'metadata_score': 0.0,
                'ela_score': 0.72,
                'ai_score': 0.85,
                'timestamp': datetime.now().isoformat(),
                'status': 'processed'
            }
        else:
            # Process with actual services
            forensic_result = forensic_service.analyze(image_data, dispute_id)
            
            decision_result = decision_service.process_scores(
                dispute_id=dispute_id,
                metadata_score=forensic_result['metadata_score'],
                ela_score=forensic_result['ela_score'],
                ai_score=0.85,  # Mock AI score
                order_amount=amount
            )
            
            result = {
                'dispute_id': dispute_id,
                'order_id': order_id,
                'amount': amount,
                'description': description,
                'trust_score': decision_result['trust_score'],
                'decision': decision_result['decision'],
                'metadata_score': forensic_result['metadata_score'],
                'ela_score': forensic_result['ela_score'],
                'ai_score': 0.85,
                'confidence': decision_result['confidence'],
                'action_taken': decision_result['action_taken'],
                'timestamp': datetime.now().isoformat(),
                'status': 'processed'
            }
        
        # Store dispute
        disputes.append(result)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/disputes', methods=['GET'])
def get_disputes():
    """Get all disputes"""
    status_filter = request.args.get('status', 'all')
    
    if status_filter == 'all':
        return jsonify(disputes)
    else:
        filtered = [d for d in disputes if d.get('status') == status_filter]
        return jsonify(filtered)


@app.route('/api/dispute/<dispute_id>', methods=['GET'])
def get_dispute(dispute_id):
    """Get a specific dispute"""
    dispute = next((d for d in disputes if d['dispute_id'] == dispute_id), None)
    
    if dispute:
        return jsonify(dispute)
    else:
        return jsonify({'error': 'Dispute not found'}), 404


@app.route('/api/dispute/<dispute_id>/approve', methods=['POST'])
def approve_dispute(dispute_id):
    """Approve a dispute"""
    dispute = next((d for d in disputes if d['dispute_id'] == dispute_id), None)
    
    if dispute:
        dispute['status'] = 'approved'
        dispute['approved_at'] = datetime.now().isoformat()
        return jsonify({'success': True, 'dispute': dispute})
    else:
        return jsonify({'error': 'Dispute not found'}), 404


@app.route('/api/dispute/<dispute_id>/reject', methods=['POST'])
def reject_dispute(dispute_id):
    """Reject a dispute"""
    dispute = next((d for d in disputes if d['dispute_id'] == dispute_id), None)
    
    if dispute:
        dispute['status'] = 'rejected'
        dispute['rejected_at'] = datetime.now().isoformat()
        return jsonify({'success': True, 'dispute': dispute})
    else:
        return jsonify({'error': 'Dispute not found'}), 404


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    total = len(disputes)
    
    if total == 0:
        return jsonify({
            'total': 0,
            'pending': 0,
            'approved': 0,
            'rejected': 0,
            'avg_trust_score': 0,
            'auto_refund': 0,
            'manual_review': 0,
            'fraud_alert': 0
        })
    
    pending = len([d for d in disputes if d.get('status') == 'processed'])
    approved = len([d for d in disputes if d.get('status') == 'approved'])
    rejected = len([d for d in disputes if d.get('status') == 'rejected'])
    
    avg_trust = sum(d.get('trust_score', 0) for d in disputes) / total
    
    auto_refund = len([d for d in disputes if d.get('decision') == 'auto_refund'])
    manual_review = len([d for d in disputes if d.get('decision') == 'manual_review'])
    fraud_alert = len([d for d in disputes if d.get('decision') == 'fraud_alert'])
    
    return jsonify({
        'total': total,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'avg_trust_score': round(avg_trust, 4),
        'auto_refund': auto_refund,
        'manual_review': manual_review,
        'fraud_alert': fraud_alert
    })


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  VeriSupport Web Application")
    print("  Assignment 6 - CS 331 Software Engineering Lab")
    print("="*60)
    print("\n  Starting server...")
    print("\n  Access URLs:")
    print("   Customer Portal: http://localhost:5000")
    print("   Agent Dashboard: http://localhost:5000/agent")
    print("   API Health:      http://localhost:5000/api/health")
    print("\n  Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
