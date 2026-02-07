.PHONY: test test/utils test/data_system test/data_system/models test/data_system/repositories test/data_system/config test/data_system/clients test/exchange_connector test/exchange_connector/api test/exchange_connector/connectors test/exchange_connector/services test/exchange_connector/kraken_utils test/integration test/integration/data_system test/integration/exchange_connector test/integration/exchange_connector_data_system

# Run all tests
test:
	pytest

# Run all utils tests
test/utils:
	pytest -m utils

# Run all data_system tests
test/data_system:
	pytest -m data_system

# Run data_system category tests
test/data_system/models:
	pytest -m "data_system and models"

test/data_system/repositories:
	pytest -m "data_system and repositories"

test/data_system/config:
	pytest -m "data_system and config"

test/data_system/clients:
	pytest -m "data_system and clients"

# Run all exchange_connector tests
test/exchange_connector:
	pytest -m exchange_connector

# Run exchange_connector category tests
test/exchange_connector/api:
	pytest -m "exchange_connector and api"

test/exchange_connector/connectors:
	pytest -m "exchange_connector and connectors"

test/exchange_connector/services:
	pytest -m "exchange_connector and services"

test/exchange_connector/kraken_utils:
	pytest -m "exchange_connector and kraken_utils"

# Run integration tests
test/integration:
	pytest -m integration

test/integration/data_system:
	pytest -m data_system_integration

test/integration/exchange_connector:
	pytest -m exchange_connector_integration

test/integration/exchange_connector_data_system:
	pytest -m exchange_connector_data_system_integration
