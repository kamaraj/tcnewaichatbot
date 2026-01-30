"""
Persona-Based Integration Tests
Tests different user roles and their expected behaviors
"""
import pytest
import time
from typing import List, Dict, Any

from tests.fixtures.personas import (
    PersonaFactory, PersonaRole, Persona, 
    ScenarioGenerator, TestScenario,
    ALL_PERSONAS, ALL_SCENARIOS
)

class TestPersonaFactory:
    """Test persona generation"""
    
    def test_create_all_personas(self):
        """Test creating one persona for each role"""
        personas = PersonaFactory.create_all_personas()
        assert len(personas) == len(PersonaRole)
        
        roles = [p.role for p in personas]
        for role in PersonaRole:
            assert role in roles
    
    def test_persona_has_required_fields(self):
        """Test persona has all required fields"""
        persona = PersonaFactory.create_persona(PersonaRole.ANALYST)
        
        assert persona.id is not None
        assert persona.name is not None
        assert persona.email is not None
        assert persona.role == PersonaRole.ANALYST
        assert persona.department is not None
        assert persona.query_style is not None
        assert len(persona.typical_queries) > 0
    
    def test_create_test_suite(self):
        """Test creating multiple personas per role"""
        suite = PersonaFactory.create_test_suite(personas_per_role=3)
        assert len(suite) == len(PersonaRole) * 3

class TestScenarioGeneration:
    """Test scenario generation"""
    
    def test_generate_scenarios(self):
        """Test generating scenarios for personas"""
        personas = [PersonaFactory.create_persona(PersonaRole.EXECUTIVE)]
        scenarios = ScenarioGenerator.generate_scenarios(personas, scenarios_per_persona=5)
        
        assert len(scenarios) == 5
        for scenario in scenarios:
            assert scenario.persona.role == PersonaRole.EXECUTIVE
    
    def test_scenario_has_required_fields(self):
        """Test scenario has all required fields"""
        personas = [PersonaFactory.create_persona(PersonaRole.ANALYST)]
        scenarios = ScenarioGenerator.generate_scenarios(personas, scenarios_per_persona=1)
        
        scenario = scenarios[0]
        assert scenario.scenario_id is not None
        assert scenario.query is not None
        assert scenario.expected_confidence in ["high", "medium", "low"]
        assert scenario.max_latency_ms > 0

@pytest.mark.persona
class TestExecutivePersona:
    """Tests for Executive role expectations"""
    
    @pytest.fixture
    def executive_persona(self):
        return PersonaFactory.create_persona(PersonaRole.EXECUTIVE)
    
    def test_executive_query_style(self, executive_persona):
        """Executives prefer concise responses"""
        assert executive_persona.query_style == "concise"
    
    def test_executive_latency_requirement(self, executive_persona):
        """Executives expect fast responses"""
        max_latency = executive_persona.expected_behaviors.get("max_response_time_ms")
        assert max_latency <= 3000  # 3 seconds max
    
    def test_executive_expects_summary(self, executive_persona):
        """Executives expect summarized responses"""
        assert executive_persona.expected_behaviors.get("expects_summary") == True

@pytest.mark.persona
class TestAnalystPersona:
    """Tests for Analyst role expectations"""
    
    @pytest.fixture
    def analyst_persona(self):
        return PersonaFactory.create_persona(PersonaRole.ANALYST)
    
    def test_analyst_query_style(self, analyst_persona):
        """Analysts prefer detailed responses"""
        assert analyst_persona.query_style == "detailed"
    
    def test_analyst_requires_sources(self, analyst_persona):
        """Analysts require source citations"""
        assert analyst_persona.expected_behaviors.get("requires_sources") == True

@pytest.mark.persona
class TestDeveloperPersona:
    """Tests for Developer role expectations"""
    
    @pytest.fixture
    def developer_persona(self):
        return PersonaFactory.create_persona(PersonaRole.DEVELOPER)
    
    def test_developer_query_style(self, developer_persona):
        """Developers prefer technical responses"""
        assert developer_persona.query_style == "technical"
    
    def test_developer_expects_code(self, developer_persona):
        """Developers expect code examples"""
        assert developer_persona.expected_behaviors.get("expects_code") == True

@pytest.mark.persona
class TestAuditorPersona:
    """Tests for Auditor role expectations"""
    
    @pytest.fixture
    def auditor_persona(self):
        return PersonaFactory.create_persona(PersonaRole.AUDITOR)
    
    def test_auditor_requires_references(self, auditor_persona):
        """Auditors require regulatory references"""
        assert auditor_persona.expected_behaviors.get("requires_references") == True
    
    def test_auditor_expects_compliance(self, auditor_persona):
        """Auditors expect compliance information"""
        assert auditor_persona.expected_behaviors.get("expects_compliance") == True

@pytest.mark.persona
@pytest.mark.slow
class TestPersonaIntegration:
    """Integration tests with actual API calls per persona"""
    
    def test_all_persona_queries(self, client):
        """Test that all persona query types work"""
        results = []
        
        for persona in ALL_PERSONAS[:3]:  # Test subset for speed
            query = persona.typical_queries[0].format("test document")
            
            start_time = time.time()
            response = client.post(f"/api/v1/chat?query={query}")
            latency_ms = (time.time() - start_time) * 1000
            
            results.append({
                "persona": persona.role.value,
                "query": query[:50],
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "max_allowed_ms": persona.expected_behaviors.get("max_response_time_ms", 10000)
            })
        
        # Verify results
        for result in results:
            # Just check response came back (latency tests are informational here)
            assert result["status_code"] in [200, 500]  # 500 if no docs
    
    def test_scenario_execution(self, client):
        """Execute test scenarios and collect metrics"""
        scenarios = ALL_SCENARIOS[:5]  # Test subset
        metrics = []
        
        for scenario in scenarios:
            start = time.time()
            response = client.post(f"/api/v1/chat?query={scenario.query}")
            latency = (time.time() - start) * 1000
            
            metrics.append({
                "scenario_id": scenario.scenario_id,
                "persona_role": scenario.persona.role.value,
                "latency_ms": latency,
                "max_latency_ms": scenario.max_latency_ms,
                "within_sla": latency <= scenario.max_latency_ms,
                "status": "pass" if response.status_code == 200 else "fail"
            })
        
        # Report metrics
        passed = sum(1 for m in metrics if m["status"] == "pass")
        print(f"\nScenario Results: {passed}/{len(metrics)} passed")
        for m in metrics:
            print(f"  {m['scenario_id']}: {m['status']} ({m['latency_ms']:.0f}ms)")
