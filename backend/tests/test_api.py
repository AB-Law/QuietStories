"""
API integration tests for the FastAPI backend.

Tests the main endpoints and routers using FastAPI TestClient.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestRootEndpoints:
    """Test basic root endpoints"""

    def test_root_endpoint(self):
        """Test the root endpoint returns correct response"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestScenariosAPI:
    """Test scenarios API endpoints"""

    @patch("backend.api.scenarios.db")
    def test_list_scenarios_empty(self, mock_db):
        """Test listing scenarios when none exist"""
        mock_db.list_scenarios.return_value = []

        response = client.get("/scenarios/")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert data["scenarios"] == []

    @patch("backend.api.scenarios.db")
    def test_list_scenarios_with_data(self, mock_db):
        """Test listing scenarios with mock data"""
        mock_scenarios = [
            {"id": "test-1", "name": "Test Scenario 1", "status": "generated"},
            {"id": "test-2", "name": "Test Scenario 2", "status": "compiled"},
        ]
        mock_db.list_scenarios.return_value = mock_scenarios

        response = client.get("/scenarios/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["scenarios"]) == 2
        assert data["scenarios"][0]["name"] == "Test Scenario 1"

    @patch("backend.api.scenarios.db")
    def test_get_scenario_not_found(self, mock_db):
        """Test getting a non-existent scenario"""
        mock_db.get_scenario.return_value = None

        response = client.get("/scenarios/non-existent-id")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @patch("backend.api.scenarios.db")
    def test_get_scenario_success(self, mock_db):
        """Test getting an existing scenario"""
        mock_scenario = {
            "id": "test-id",
            "name": "Test Scenario",
            "spec": {"name": "Test", "actions": []},
            "status": "generated",
        }
        mock_db.get_scenario.return_value = mock_scenario

        response = client.get("/scenarios/test-id")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-id"
        assert data["name"] == "Test Scenario"

    @patch("backend.api.scenarios.ScenarioGenerator")
    @patch("backend.api.scenarios.db")
    def test_generate_scenario_success(self, mock_db, mock_generator_class):
        """Test successful scenario generation"""
        # Mock the generator
        mock_generator = MagicMock()
        mock_scenario_spec = MagicMock()
        mock_scenario_spec.name = "Generated Scenario"
        mock_scenario_spec.spec_version = "1.0"
        mock_scenario_spec.dict.return_value = {
            "name": "Generated Scenario",
            "actions": [],
        }
        # Use AsyncMock for async method
        mock_generator.generate_scenario = AsyncMock(return_value=mock_scenario_spec)
        mock_generator_class.return_value = mock_generator

        # Mock db save
        mock_db.save_scenario.return_value = None

        request_data = {"description": "A test scenario description"}

        response = client.post("/scenarios/generate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Generated Scenario"
        assert data["status"] == "generated"

    @patch("backend.api.scenarios.ScenarioGenerator")
    def test_generate_scenario_failure(self, mock_generator_class):
        """Test scenario generation failure"""
        # Mock generator to raise exception
        mock_generator = MagicMock()
        mock_generator.generate_scenario = AsyncMock(
            side_effect=Exception("Generation failed")
        )
        mock_generator_class.return_value = mock_generator

        request_data = {"description": "A failing description"}

        response = client.post("/scenarios/generate", json=request_data)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Generation failed" in data["detail"]


class TestSessionsAPI:
    """Test sessions API endpoints"""

    def test_sessions_placeholder(self):
        """Placeholder test for sessions API"""
        # TODO: Add actual session tests when endpoints are implemented
        response = client.get("/sessions/")
        # This will likely 404 until sessions router is implemented
        assert response.status_code in [200, 404, 405]  # Allow for unimplemented


class TestPromptsAPI:
    """Test prompts API endpoints"""

    def test_prompts_placeholder(self):
        """Placeholder test for prompts API"""
        # TODO: Add actual prompt tests when endpoints are implemented
        response = client.get("/prompts/")
        # This will likely 404 until prompts router is implemented
        assert response.status_code in [200, 404, 405]  # Allow for unimplemented
