.PHONY: test test/data_system test/data_system/models test/data_system/repositories test/data_system/config test/data_system/clients

# Run all tests
test:
	pytest

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
