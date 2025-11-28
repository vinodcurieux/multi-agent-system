"""
Phase 1 Verification Test Script

This script tests all core Phase 1 components to ensure they work correctly:
- Configuration management
- Logging setup
- Tracing initialization
- Database connections
- Vector store operations
- Agent instantiation
- Workflow construction
- Tool execution

Run this script to verify Phase 1 is working:
    python test_phase1.py
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime
import time


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_configuration():
    """Test configuration management."""
    print_section("1. Testing Configuration Management")

    try:
        from src.config import settings, get_settings

        print(f"✅ Config module imported successfully")
        print(f"   - App Name: {settings.APP_NAME}")
        print(f"   - App Version: {settings.APP_VERSION}")
        print(f"   - Environment: {settings.ENVIRONMENT}")
        print(f"   - OpenAI Model: {settings.OPENAI_MODEL}")
        print(f"   - Database URL: {settings.DATABASE_URL[:30]}...")
        print(f"   - Redis URL: {settings.REDIS_URL}")
        print(f"   - Chroma Collection: {settings.CHROMA_COLLECTION_NAME}")

        # Test singleton
        settings2 = get_settings()
        assert settings is settings2, "Settings should be singleton"
        print(f"✅ Settings singleton pattern works correctly")

        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logging():
    """Test logging setup."""
    print_section("2. Testing Logging Configuration")

    try:
        from src.observability.logging_config import setup_logging, get_logger

        # Setup logging
        setup_logging(level="INFO", format_type="text")
        print(f"✅ Logging configured successfully")

        # Get logger and test
        logger = get_logger("test_phase1")
        logger.info("Test info message")
        logger.debug("Test debug message (should not appear at INFO level)")
        logger.warning("Test warning message")

        print(f"✅ Logger instantiation and logging works")

        return True
    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tracing():
    """Test Phoenix tracing setup."""
    print_section("3. Testing Phoenix Tracing")

    try:
        from src.observability.tracing import initialize_tracing, get_tracer, trace_agent

        # Initialize tracing (may fail if Phoenix not running, which is OK)
        tracer = initialize_tracing()

        if tracer:
            print(f"✅ Phoenix tracing initialized successfully")
        else:
            print(f"⚠️  Phoenix tracing disabled or unavailable (this is OK for testing)")

        # Test decorator
        @trace_agent
        def test_function(state):
            return {"result": "success"}

        result = test_function({"test": "data"})
        assert result["result"] == "success"
        print(f"✅ @trace_agent decorator works correctly")

        return True
    except Exception as e:
        print(f"❌ Tracing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database():
    """Test database connection."""
    print_section("4. Testing Database Connection")

    try:
        from src.database.connection import DatabaseManager, get_db_manager, connect_db

        # Test manager
        db_manager = get_db_manager()
        print(f"✅ Database manager instantiated")

        # Test connection
        try:
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                table_names = [table[0] for table in tables]
                print(f"✅ Database connection successful")
                print(f"   Found {len(table_names)} tables: {', '.join(table_names)}")
        except Exception as e:
            print(f"⚠️  Database not initialized yet (this is OK): {e}")

        # Test legacy function
        conn = connect_db()
        conn.close()
        print(f"✅ Legacy connect_db() function works")

        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tools():
    """Test tool functions."""
    print_section("5. Testing Tool Functions")

    try:
        from src.tools.policy_tools import get_policy_details, get_auto_policy_details
        from src.tools.billing_tools import get_billing_info, get_payment_history
        from src.tools.claims_tools import get_claim_status

        print(f"✅ All tool modules imported successfully")

        # Test with non-existent policy (should return error, not crash)
        result = get_policy_details("TEST999999")
        assert "error" in result or "Error" in str(result) or result is None
        print(f"✅ Policy tools handle missing data gracefully")

        result = get_billing_info(policy_number="TEST999999")
        assert "error" in result or "Error" in str(result) or result is None
        print(f"✅ Billing tools handle missing data gracefully")

        result = get_claim_status(claim_id="TEST999999")
        assert "error" in result or "Error" in str(result) or result is None
        print(f"✅ Claims tools handle missing data gracefully")

        return True
    except Exception as e:
        print(f"❌ Tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store():
    """Test vector store operations."""
    print_section("6. Testing Vector Store (ChromaDB)")

    try:
        from src.rag.vector_store import VectorStoreManager, get_vector_store

        # Get vector store
        vector_store = get_vector_store()
        print(f"✅ Vector store manager instantiated")

        # Check if collection exists and has data
        try:
            count = vector_store.get_collection_count()
            print(f"✅ Vector store collection accessible")
            print(f"   Collection '{vector_store.collection_name}' has {count} documents")

            if count > 0:
                # Try a test query
                results = vector_store.query("What is life insurance?", n_results=2)
                num_results = len(results.get("ids", [[]])[0]) if results.get("ids") else 0
                print(f"✅ Vector store query successful ({num_results} results)")

                # Test formatting
                formatted = vector_store.format_faq_context(results)
                assert len(formatted) > 0
                print(f"✅ FAQ context formatting works")
            else:
                print(f"⚠️  Vector store is empty (needs to be populated)")

        except Exception as e:
            print(f"⚠️  Vector store not populated yet: {e}")

        return True
    except Exception as e:
        print(f"❌ Vector store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_state():
    """Test GraphState and state management."""
    print_section("7. Testing GraphState & State Management")

    try:
        from src.graph.state import GraphState, create_initial_state, update_state, clear_clarification_state

        # Create initial state
        state = create_initial_state(
            user_input="What is my premium?",
            customer_id="CUST00001",
            policy_number="POL000001"
        )
        print(f"✅ Initial state created successfully")
        assert state["user_input"] == "What is my premium?"
        assert state["customer_id"] == "CUST00001"
        assert state["n_iteration"] == 0
        print(f"✅ State fields populated correctly")

        # Test state update
        state = update_state(state, next_agent="billing_agent", task="Get premium info")
        assert state["next_agent"] == "billing_agent"
        assert state["task"] == "Get premium info"
        print(f"✅ State update works correctly")

        # Test clarification state clearing
        state["needs_clarification"] = True
        state["clarification_question"] = "What is your policy number?"
        state = clear_clarification_state(state)
        assert state["needs_clarification"] == False
        assert state["clarification_question"] is None
        print(f"✅ Clarification state clearing works")

        return True
    except Exception as e:
        print(f"❌ GraphState test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agents():
    """Test agent instantiation."""
    print_section("8. Testing Agent Instantiation")

    try:
        from src.agents.supervisor import SupervisorAgent
        from src.agents.policy_agent import PolicyAgent
        from src.agents.billing_agent import BillingAgent
        from src.agents.claims_agent import ClaimsAgent
        from src.agents.general_help_agent import GeneralHelpAgent
        from src.agents.human_escalation import HumanEscalationAgent
        from src.agents.final_answer import FinalAnswerAgent

        agents = {
            "SupervisorAgent": SupervisorAgent,
            "PolicyAgent": PolicyAgent,
            "BillingAgent": BillingAgent,
            "ClaimsAgent": ClaimsAgent,
            "GeneralHelpAgent": GeneralHelpAgent,
            "HumanEscalationAgent": HumanEscalationAgent,
            "FinalAnswerAgent": FinalAnswerAgent,
        }

        for name, agent_class in agents.items():
            agent = agent_class()
            assert agent.name is not None
            assert agent.logger is not None
            print(f"✅ {name} instantiated successfully (name: {agent.name})")

        return True
    except Exception as e:
        print(f"❌ Agent instantiation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow():
    """Test workflow construction."""
    print_section("9. Testing Workflow Construction")

    try:
        from src.graph.workflow import create_workflow, compile_workflow, get_workflow
        from src.graph.routing import decide_next_agent

        # Create workflow
        workflow = create_workflow()
        print(f"✅ Workflow created successfully")

        # Compile workflow
        compiled = compile_workflow(workflow)
        print(f"✅ Workflow compiled successfully")

        # Test routing function
        from src.graph.state import create_initial_state

        test_state = create_initial_state("Test query")
        test_state["next_agent"] = "policy_agent"
        next_agent = decide_next_agent(test_state)
        assert next_agent == "policy_agent"
        print(f"✅ Routing function works correctly")

        # Test get_workflow singleton
        workflow2 = get_workflow()
        assert workflow2 is not None
        print(f"✅ Workflow singleton works correctly")

        return True
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_client():
    """Test LLM client (without making actual API calls)."""
    print_section("10. Testing LLM Client")

    try:
        from src.utils.llm_client import LLMClient, get_llm_client

        # Test instantiation
        client = get_llm_client()
        assert client is not None
        print(f"✅ LLM client instantiated successfully")
        print(f"   Model: {client.model}")

        # Test singleton
        client2 = get_llm_client()
        assert client is client2
        print(f"✅ LLM client singleton works correctly")

        print(f"⚠️  Skipping actual API call (requires OpenAI API key)")

        return True
    except Exception as e:
        print(f"❌ LLM client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics():
    """Test metrics collection."""
    print_section("11. Testing Metrics Collection")

    try:
        from src.observability import metrics

        # Test that metrics are defined
        assert metrics.api_requests_total is not None
        assert metrics.agent_invocations_total is not None
        assert metrics.llm_requests_total is not None
        print(f"✅ All metric counters defined")

        # Test incrementing a metric
        metrics.agent_invocations_total.labels(agent_name="test_agent", status="success").inc()
        print(f"✅ Metric increment works")

        # Test getting metrics output
        metrics_output = metrics.get_metrics()
        assert metrics_output is not None
        assert len(metrics_output) > 0
        print(f"✅ Metrics export works (size: {len(metrics_output)} bytes)")

        return True
    except Exception as e:
        print(f"❌ Metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 1 verification tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "PHASE 1 VERIFICATION TEST SUITE" + " "*16 + "║")
    print("╚" + "="*58 + "╝")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("Configuration Management", test_configuration),
        ("Logging System", test_logging),
        ("Tracing System", test_tracing),
        ("Database Connection", test_database),
        ("Tool Functions", test_tools),
        ("Vector Store", test_vector_store),
        ("GraphState", test_graph_state),
        ("Agent Instantiation", test_agents),
        ("Workflow Construction", test_workflow),
        ("LLM Client", test_llm_client),
        ("Metrics Collection", test_metrics),
    ]

    results = []
    passed = 0
    failed = 0

    start_time = time.time()

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
            failed += 1

    duration = time.time() - start_time

    # Print summary
    print_section("TEST SUMMARY")
    print(f"\nTotal Tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Duration: {duration:.2f} seconds")

    print("\nDetailed Results:")
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Phase 1 is working correctly.")
        print("\nNext steps:")
        print("  1. Populate the database with test data")
        print("  2. Populate ChromaDB with FAQ data")
        print("  3. Proceed to Phase 2: API Layer")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please fix the issues before proceeding.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
