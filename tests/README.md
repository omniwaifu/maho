# Maho Integration Tests

This directory contains integration tests for the Maho Agent API to ensure core functionality works end-to-end using **pytest with anyio backend**.

## What the Integration Test Does

The `test_integration.py` performs a comprehensive smoke test using pytest:

1. **Server Startup** - Starts the FastAPI server in a subprocess (session fixture)
2. **Health Check** - Verifies the health endpoint responds correctly
3. **Settings** - Tests settings retrieval functionality  
4. **Static Assets** - Verifies our content-type fixes (favicon, CSS, JS)
5. **Connection Test** - Tests the fixed `test_connection` endpoint format
6. **Agent Chat** - Sends a question to the agent and waits for response

## Running the Tests

### Prerequisites
```bash
# Install test dependencies (using uv)
uv sync --dev

# Make sure you have your environment configured
cp example.env .env
# Edit .env with your API keys
```

### Run the Tests
```bash
# Run all integration tests
pytest tests/test_integration.py -v

# Run specific test
pytest tests/test_integration.py::TestMahoIntegration::test_agent_chat_functionality -v

# Run with more detailed output
pytest tests/test_integration.py -v -s
```

### Expected Output
```
====================== test session starts =======================
tests/test_integration.py::TestMahoIntegration::test_health_check PASSED
tests/test_integration.py::TestMahoIntegration::test_settings_get PASSED  
tests/test_integration.py::TestMahoIntegration::test_static_asset_content_types PASSED
tests/test_integration.py::TestMahoIntegration::test_connection_endpoint_format PASSED
tests/test_integration.py::TestMahoIntegration::test_agent_chat_functionality PASSED

======================= 5 passed in 15.23s =======================
```

## Why pytest + anyio?

- **🔄 Aligns with Migration**: Uses anyio/trio backend matching your async migration
- **🧪 Proper Testing**: pytest fixtures, proper assertions, better error reporting  
- **⚡ Async Native**: Uses `httpx.AsyncClient` and `anyio.sleep` throughout
- **🔧 Maintainable**: Standard pytest structure, easy to extend
- **📊 Better Output**: Clear test results, detailed failure reporting

## What This Tests

This integration test specifically validates:

- **API Changes**: Ensures our OpenAPI spec improvements didn't break functionality
- **Content Types**: Verifies static assets return proper MIME types (not `application/json`)
- **Response Formats**: Confirms `test_connection` now returns `{"success": true}` format
- **Core Agent Flow**: Tests the complete message → response cycle using async/await
- **Server Stability**: Ensures the server starts, runs, and stops cleanly

## Test Structure

- **Session Fixture**: Server starts once per test session, shared across tests
- **Async Tests**: All tests are async using anyio backend  
- **HTTP Client**: Uses httpx.AsyncClient for all requests
- **Proper Cleanup**: Server automatically stopped after tests complete

## Customization

You can modify the tests by:

- Adding new test methods to `TestMahoIntegration`
- Changing the test question in `test_agent_chat_functionality()`
- Adjusting timeouts for slower systems
- Adding authentication tests with fixtures
- Testing different anyio backends (trio/asyncio)

This is a proper pytest integration test that validates core functionality while aligning with your anyio migration! 