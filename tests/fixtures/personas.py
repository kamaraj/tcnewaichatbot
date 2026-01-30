"""
Synthetic Personas for Testing
Different user roles with varying behaviors and query patterns
"""
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum
import random
from faker import Faker

fake = Faker()

class PersonaRole(Enum):
    """User roles with different access levels and behaviors"""
    EXECUTIVE = "executive"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    SUPPORT_AGENT = "support_agent"
    DEVELOPER = "developer"
    AUDITOR = "auditor"
    NEW_USER = "new_user"
    POWER_USER = "power_user"

@dataclass
class Persona:
    """Represents a synthetic test user"""
    id: str
    name: str
    email: str
    role: PersonaRole
    department: str
    query_style: str  # concise, detailed, technical, casual
    typical_queries: List[str]
    expected_behaviors: Dict[str, Any]

class PersonaFactory:
    """Factory for creating synthetic test personas"""
    
    QUERY_TEMPLATES = {
        PersonaRole.EXECUTIVE: [
            "What is the executive summary of {}?",
            "Give me the key metrics from {}",
            "What are the main risks mentioned in {}?",
            "Summarize the financial highlights",
            "What is our competitive position?",
        ],
        PersonaRole.ANALYST: [
            "What are the detailed statistics in {}?",
            "Show me the trend analysis for {}",
            "What correlations exist between {} and {}?",
            "Provide a breakdown of {} by category",
            "What is the year-over-year comparison?",
        ],
        PersonaRole.RESEARCHER: [
            "What methodology was used in {}?",
            "What are the citations for {}?",
            "Explain the theoretical framework",
            "What are the limitations of this study?",
            "How does this compare to previous research?",
        ],
        PersonaRole.SUPPORT_AGENT: [
            "How do I resolve issue {}?",
            "What is the troubleshooting guide for {}?",
            "What are the FAQ answers for {}?",
            "How should I respond to a customer asking about {}?",
            "What is the standard procedure for {}?",
        ],
        PersonaRole.DEVELOPER: [
            "What is the API specification for {}?",
            "Show me the code examples for {}",
            "What are the technical requirements?",
            "Explain the architecture of {}",
            "What are the integration steps?",
        ],
        PersonaRole.AUDITOR: [
            "What are the compliance requirements in {}?",
            "Show me the audit trail for {}",
            "What are the risk controls mentioned?",
            "List all regulatory references",
            "What are the policy violations?",
        ],
        PersonaRole.NEW_USER: [
            "What is this document about?",
            "Can you help me understand {}?",
            "What should I know about {}?",
            "Explain {} in simple terms",
            "Where can I find information about {}?",
        ],
        PersonaRole.POWER_USER: [
            "Cross-reference {} with {} and provide insights",
            "Aggregate all mentions of {} across documents",
            "What are the contradictions between documents?",
            "Generate a comprehensive report on {}",
            "Compare and contrast {} from multiple sources",
        ],
    }
    
    DEPARTMENTS = [
        "Finance", "Engineering", "Legal", "Marketing", 
        "Operations", "HR", "Sales", "Research", "Compliance"
    ]
    
    @classmethod
    def create_persona(cls, role: PersonaRole) -> Persona:
        """Create a single persona with the specified role"""
        
        query_styles = {
            PersonaRole.EXECUTIVE: "concise",
            PersonaRole.ANALYST: "detailed",
            PersonaRole.RESEARCHER: "technical",
            PersonaRole.SUPPORT_AGENT: "casual",
            PersonaRole.DEVELOPER: "technical",
            PersonaRole.AUDITOR: "detailed",
            PersonaRole.NEW_USER: "casual",
            PersonaRole.POWER_USER: "detailed",
        }
        
        expected_behaviors = {
            PersonaRole.EXECUTIVE: {
                "max_response_time_ms": 3000,
                "expects_summary": True,
                "tolerance_for_uncertainty": "low",
            },
            PersonaRole.ANALYST: {
                "max_response_time_ms": 10000,
                "expects_details": True,
                "requires_sources": True,
            },
            PersonaRole.RESEARCHER: {
                "max_response_time_ms": 15000,
                "expects_citations": True,
                "requires_methodology": True,
            },
            PersonaRole.SUPPORT_AGENT: {
                "max_response_time_ms": 5000,
                "expects_actionable": True,
                "simple_language": True,
            },
            PersonaRole.DEVELOPER: {
                "max_response_time_ms": 10000,
                "expects_code": True,
                "requires_technical_accuracy": True,
            },
            PersonaRole.AUDITOR: {
                "max_response_time_ms": 10000,
                "expects_compliance": True,
                "requires_references": True,
            },
            PersonaRole.NEW_USER: {
                "max_response_time_ms": 5000,
                "expects_simple": True,
                "requires_guidance": True,
            },
            PersonaRole.POWER_USER: {
                "max_response_time_ms": 20000,
                "expects_comprehensive": True,
                "handles_complexity": True,
            },
        }
        
        return Persona(
            id=fake.uuid4(),
            name=fake.name(),
            email=fake.email(),
            role=role,
            department=random.choice(cls.DEPARTMENTS),
            query_style=query_styles.get(role, "casual"),
            typical_queries=cls.QUERY_TEMPLATES.get(role, []),
            expected_behaviors=expected_behaviors.get(role, {}),
        )
    
    @classmethod
    def create_all_personas(cls) -> List[Persona]:
        """Create one persona for each role"""
        return [cls.create_persona(role) for role in PersonaRole]
    
    @classmethod
    def create_test_suite(cls, personas_per_role: int = 3) -> List[Persona]:
        """Create a comprehensive test suite with multiple personas per role"""
        personas = []
        for role in PersonaRole:
            for _ in range(personas_per_role):
                personas.append(cls.create_persona(role))
        return personas

@dataclass
class TestScenario:
    """A test scenario with persona-specific context"""
    scenario_id: str
    name: str
    description: str
    persona: Persona
    query: str
    expected_confidence: str  # high, medium, low
    expected_sources: bool
    max_latency_ms: int
    tags: List[str]

class ScenarioGenerator:
    """Generate test scenarios for different personas"""
    
    DOCUMENT_TOPICS = [
        "quarterly report", "technical specification", "user manual",
        "compliance policy", "research paper", "API documentation",
        "troubleshooting guide", "onboarding guide", "audit report"
    ]
    
    @classmethod
    def generate_scenarios(cls, personas: List[Persona], scenarios_per_persona: int = 5) -> List[TestScenario]:
        """Generate test scenarios for each persona"""
        scenarios = []
        
        for persona in personas:
            for i in range(scenarios_per_persona):
                topic = random.choice(cls.DOCUMENT_TOPICS)
                query_template = random.choice(persona.typical_queries)
                # Safe format - replace all {} with the topic
                query = query_template.replace("{}", topic)
                
                scenario = TestScenario(
                    scenario_id=f"{persona.role.value}_{i}_{fake.uuid4()[:8]}",
                    name=f"{persona.role.value}_scenario_{i}",
                    description=f"Testing {persona.role.value} query: {query[:50]}...",
                    persona=persona,
                    query=query,
                    expected_confidence="high" if persona.role in [PersonaRole.ANALYST, PersonaRole.AUDITOR] else "medium",
                    expected_sources=persona.expected_behaviors.get("requires_sources", False),
                    max_latency_ms=persona.expected_behaviors.get("max_response_time_ms", 10000),
                    tags=[persona.role.value, persona.department.lower(), persona.query_style]
                )
                scenarios.append(scenario)
        
        return scenarios

# Pre-built test data
ALL_PERSONAS = PersonaFactory.create_all_personas()
FULL_TEST_SUITE = PersonaFactory.create_test_suite(personas_per_role=2)
ALL_SCENARIOS = ScenarioGenerator.generate_scenarios(ALL_PERSONAS, scenarios_per_persona=3)
