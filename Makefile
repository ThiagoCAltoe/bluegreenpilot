.PHONY: check test validate-schemas validate-example

check: test validate-schemas validate-example
	python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"
	node --check examples/node-docker-bluegreen/app/index.js

test:
	python -m unittest discover -s tests

validate-schemas:
	python -m json.tool schemas/config.schema.json > /dev/null
	python -m json.tool schemas/state.schema.json > /dev/null

validate-example:
	python -m bluegreenpilot --project examples/node-docker-bluegreen validate --env homolog --env prod
	python -m bluegreenpilot --project examples/node-docker-bluegreen plan prod --source main
	python -m bluegreenpilot --project examples/no-docker-script validate --env homolog --env prod
	python -m bluegreenpilot --project examples/no-docker-script plan prod --source main
