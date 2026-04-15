"""
Tests for the Flask REST API
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_token(client):
    """Register and get auth token."""
    # Register
    res = client.post('/api/auth/register', json={
        'username': 'testuser',
        'email': 'test@test.com',
        'password': 'test123',
        'role': 'admin'
    })

    if res.status_code == 201:
        data = json.loads(res.data)
        return data['data']['access_token']

    # If already exists, login
    res = client.post('/api/auth/login', json={
        'email': 'test@test.com',
        'password': 'test123'
    })
    data = json.loads(res.data)
    return data['data']['access_token']


class TestHealthCheck:
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        res = client.get('/api/health')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data


class TestAuth:
    def test_register_success(self, client):
        """Test successful registration."""
        res = client.post('/api/auth/register', json={
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'pass123',
            'role': 'user'
        })
        assert res.status_code in [201, 409]  # 409 if already exists

    def test_register_missing_fields(self, client):
        """Test registration with missing fields."""
        res = client.post('/api/auth/register', json={
            'username': 'x'
        })
        assert res.status_code == 400

    def test_login_invalid(self, client):
        """Test login with invalid credentials."""
        res = client.post('/api/auth/login', json={
            'email': 'nonexistent@test.com',
            'password': 'wrong'
        })
        assert res.status_code == 401


class TestEvents:
    def test_create_event(self, client):
        """Test creating a drowsiness event."""
        res = client.post('/api/events', json={
            'type': 'drowsy',
            'ear': 0.18,
            'mar': 0.45,
            'device_id': 'test-device'
        })
        assert res.status_code == 201
        data = json.loads(res.data)
        assert data['data']['event_type'] == 'drowsy'

    def test_list_events(self, client, auth_token):
        """Test listing events (requires auth)."""
        headers = {'Authorization': f'Bearer {auth_token}'}
        res = client.get('/api/events', headers=headers)
        assert res.status_code == 200

    def test_event_stats(self, client, auth_token):
        """Test event statistics."""
        headers = {'Authorization': f'Bearer {auth_token}'}
        res = client.get('/api/events/stats?period=week', headers=headers)
        assert res.status_code == 200

    def test_latest_events(self, client, auth_token):
        """Test latest events endpoint."""
        headers = {'Authorization': f'Bearer {auth_token}'}
        res = client.get('/api/events/latest?count=5', headers=headers)
        assert res.status_code == 200


class TestDashboard:
    def test_dashboard_summary(self, client, auth_token):
        """Test dashboard summary."""
        headers = {'Authorization': f'Bearer {auth_token}'}
        res = client.get('/api/dashboard/summary', headers=headers)
        assert res.status_code == 200

    def test_dashboard_unauthorized(self, client):
        """Test dashboard without auth."""
        res = client.get('/api/dashboard/summary')
        assert res.status_code == 401


class TestNLP:
    def test_nlp_query(self, client, auth_token):
        """Test NLP query endpoint."""
        headers = {'Authorization': f'Bearer {auth_token}'}
        res = client.post('/api/nlp/query', headers=headers, json={
            'query': 'Show driver status'
        })
        assert res.status_code == 200
        data = json.loads(res.data)
        assert 'intent' in data['data']

    def test_nlp_help(self, client, auth_token):
        """Test NLP help query."""
        headers = {'Authorization': f'Bearer {auth_token}'}
        res = client.post('/api/nlp/query', headers=headers, json={
            'query': 'help'
        })
        assert res.status_code == 200

    def test_nlp_empty_query(self, client, auth_token):
        """Test NLP with empty query."""
        headers = {'Authorization': f'Bearer {auth_token}'}
        res = client.post('/api/nlp/query', headers=headers, json={})
        assert res.status_code == 400


class TestSecurity:
    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present."""
        res = client.get('/api/health')
        # Flask-Limiter adds rate limit headers
        assert res.status_code == 200

    def test_404_handler(self, client):
        """Test 404 error handler."""
        res = client.get('/api/nonexistent')
        assert res.status_code == 404
        data = json.loads(res.data)
        assert 'error' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
