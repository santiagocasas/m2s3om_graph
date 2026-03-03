.PHONY: pipeline-run pipeline-run-force pipeline-freeze pipeline-run-freeze pipeline-run-freeze-force pipeline-stats pipeline-stats-stdout

UV ?= uv
PYTHON ?= python
PIPELINE_STATUS_FILE ?= .local/rdamsc_pipeline_status.json
PIPELINE_EXPORT_DIR ?= exports/pipeline/latest
SSSOM_DIR ?= exports/sssom
PIPELINE_LOG_FILE ?= .local/bootstrap_rdamsc.log

pipeline-run:
	$(UV) run $(PYTHON) scripts/rdamsc_pipeline_stats.py run

pipeline-run-force:
	$(UV) run $(PYTHON) scripts/rdamsc_pipeline_stats.py run --force

pipeline-freeze:
	$(UV) run --with matplotlib $(PYTHON) scripts/rdamsc_pipeline_stats.py freeze --status-file $(PIPELINE_STATUS_FILE) --output-dir $(PIPELINE_EXPORT_DIR) --sssom-dir $(SSSOM_DIR) --pipeline-log $(PIPELINE_LOG_FILE) --plots

pipeline-run-freeze:
	$(UV) run $(PYTHON) scripts/rdamsc_pipeline_stats.py run && $(MAKE) pipeline-freeze

pipeline-run-freeze-force:
	$(UV) run $(PYTHON) scripts/rdamsc_pipeline_stats.py run --force && $(MAKE) pipeline-freeze

pipeline-stats:
	$(UV) run --with matplotlib $(PYTHON) scripts/rdamsc_pipeline_stats.py stats --status-file $(PIPELINE_STATUS_FILE) --json-out $(PIPELINE_EXPORT_DIR)/rdamsc_stats_summary.json --crosswalk-csv-out $(PIPELINE_EXPORT_DIR)/rdamsc_crosswalks.csv --artifact-csv-out $(PIPELINE_EXPORT_DIR)/rdamsc_artifacts.csv --plots-dir $(PIPELINE_EXPORT_DIR)/plots

pipeline-stats-stdout:
	$(UV) run --with matplotlib $(PYTHON) scripts/rdamsc_pipeline_stats.py stats --status-file $(PIPELINE_STATUS_FILE) --print-json
