#!/usr/bin/env python3
"""
Flask web application for visualizing YC Companies and Team Members
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import os

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)  # Enable CORS for all routes

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('yc_companies.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Main table view page"""
    return render_template('index.html')

@app.route('/api/companies')
def get_companies():
    """Get all companies"""
    conn = get_db_connection()
    
    # Get query parameters
    search = request.args.get('search', '')
    limit = request.args.get('limit', type=int)
    
    query = '''
        SELECT id, name, batch, location, industry, website, yc_url, is_hiring
        FROM companies 
        WHERE yc_url LIKE "%/companies/%" 
        AND yc_url NOT LIKE "%?%" 
        AND yc_url NOT LIKE "%industry=%" 
        AND yc_url NOT LIKE "%batch=%"
    '''
    
    params = []
    if search:
        query += ' AND name LIKE ?'
        params.append(f'%{search}%')
    
    query += ' ORDER BY name'
    
    if limit:
        query += f' LIMIT {limit}'
    
    cursor = conn.execute(query, params)
    companies = [dict(row) for row in cursor.fetchall()]
    
    # Clean company names
    for company in companies:
        if company['name']:
            company['name'] = company['name'].split('\n')[0]
    
    conn.close()
    return jsonify(companies)

@app.route('/api/companies/<int:company_id>')
def get_company(company_id):
    """Get single company details"""
    conn = get_db_connection()
    company = conn.execute(
        'SELECT * FROM companies WHERE id = ?', (company_id,)
    ).fetchone()
    
    if company:
        # Get founders for this company
        founders = conn.execute(
            'SELECT * FROM founders WHERE company_id = ?', (company_id,)
        ).fetchall()
        
        result = dict(company)
        result['founders'] = [dict(founder) for founder in founders]
        conn.close()
        return jsonify(result)
    
    conn.close()
    return jsonify({'error': 'Company not found'}), 404

def _get_founders_data():
    """Helper function to get founders data"""
    conn = get_db_connection()
    
    search = request.args.get('search', '')
    company_filter = request.args.get('company', '')
    
    query = '''
        SELECT f.*, c.name as company_display_name
        FROM founders f
        LEFT JOIN companies c ON f.company_id = c.id
        WHERE 1=1
    '''
    
    params = []
    if search:
        query += ' AND f.name LIKE ?'
        params.append(f'%{search}%')
    
    if company_filter:
        query += ' AND f.company_name LIKE ?'
        params.append(f'%{company_filter}%')
    
    query += ' ORDER BY f.company_name, f.name'
    
    cursor = conn.execute(query, params)
    founders = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return founders

@app.route('/api/members')
def get_members():
    """Get all team members (deprecated - use /api/founders)"""
    founders = _get_founders_data()
    return jsonify(founders)

@app.route('/api/founders')
def get_founders():
    """Get all founders"""
    founders = _get_founders_data()
    return jsonify(founders)

@app.route('/api/stats')
def get_stats():
    """Get statistics"""
    conn = get_db_connection()
    
    # Total companies
    total_companies = conn.execute(
        'SELECT COUNT(*) FROM companies WHERE yc_url LIKE "%/companies/%" AND yc_url NOT LIKE "%?%"'
    ).fetchone()[0]
    
    # Companies with founders
    companies_with_founders = conn.execute(
        'SELECT COUNT(DISTINCT company_name) FROM founders'
    ).fetchone()[0]
    
    # Total founders
    total_founders = conn.execute('SELECT COUNT(*) FROM founders').fetchone()[0]
    
    # Companies by batch
    batch_stats = conn.execute('''
        SELECT batch, COUNT(*) as count 
        FROM companies 
        WHERE batch IS NOT NULL AND batch != ''
        GROUP BY batch
        ORDER BY count DESC
    ''').fetchall()
    
    # Top companies by founder count
    top_companies = conn.execute('''
        SELECT company_name, COUNT(*) as founder_count
        FROM founders
        GROUP BY company_name
        ORDER BY founder_count DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'total_companies': total_companies,
        'companies_with_founders': companies_with_founders,
        'total_founders': total_founders,
        'batch_stats': [dict(row) for row in batch_stats],
        'top_companies': [dict(row) for row in top_companies]
    })

@app.route('/companies')
def companies_page():
    """Companies listing page"""
    return render_template('companies.html')

@app.route('/members')
def members_page():
    """Team members listing page"""
    return render_template('members.html')

@app.after_request
def after_request(response):
    """Add headers to prevent caching issues"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Changed from 5000

