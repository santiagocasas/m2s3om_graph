def crosswalk_surreal_schema() -> str:
    return """
DEFINE TABLE OVERWRITE standard SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE name ON standard TYPE string;
DEFINE FIELD OVERWRITE namespace ON standard TYPE option<string>;
DEFINE FIELD OVERWRITE version ON standard TYPE option<string>;
DEFINE FIELD OVERWRITE urls ON standard TYPE object;
DEFINE FIELD OVERWRITE external_ids ON standard TYPE object;
DEFINE INDEX OVERWRITE idx_standard_name_version ON standard FIELDS name, version UNIQUE;

DEFINE TABLE OVERWRITE element SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE standard_id ON element TYPE string;
DEFINE FIELD OVERWRITE path ON element TYPE string;
DEFINE FIELD OVERWRITE label ON element TYPE string;
DEFINE FIELD OVERWRITE full_iri ON element TYPE option<string>;
DEFINE FIELD OVERWRITE notes ON element TYPE option<string>;
DEFINE FIELD OVERWRITE parent_element_id ON element TYPE option<string>;
DEFINE INDEX OVERWRITE idx_element_standard_path ON element FIELDS standard_id, path UNIQUE;

DEFINE TABLE OVERWRITE crosswalk SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE name ON crosswalk TYPE string;
DEFINE FIELD OVERWRITE source_standard_id ON crosswalk TYPE string;
DEFINE FIELD OVERWRITE target_standard_id ON crosswalk TYPE string;
DEFINE FIELD OVERWRITE version ON crosswalk TYPE option<string>;
DEFINE FIELD OVERWRITE doi ON crosswalk TYPE option<string>;
DEFINE FIELD OVERWRITE msc_id ON crosswalk TYPE option<string>;
DEFINE FIELD OVERWRITE doc_uri ON crosswalk TYPE option<string>;
DEFINE FIELD OVERWRITE created_at ON crosswalk TYPE string;
DEFINE INDEX OVERWRITE idx_crosswalk_signature ON crosswalk FIELDS source_standard_id, target_standard_id, version UNIQUE;

DEFINE TABLE OVERWRITE mapping_rule SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE crosswalk_id ON mapping_rule TYPE string;
DEFINE FIELD OVERWRITE source_element_id ON mapping_rule TYPE option<string>;
DEFINE FIELD OVERWRITE source_paths ON mapping_rule TYPE array<string>;
DEFINE FIELD OVERWRITE target_element_id ON mapping_rule TYPE option<string>;
DEFINE FIELD OVERWRITE target_paths ON mapping_rule TYPE array<string>;
DEFINE FIELD OVERWRITE mapping_type ON mapping_rule TYPE string;
DEFINE FIELD OVERWRITE confidence ON mapping_rule TYPE float;
DEFINE FIELD OVERWRITE semantic_loss ON mapping_rule TYPE bool;
DEFINE FIELD OVERWRITE ambiguity ON mapping_rule TYPE bool;
DEFINE FIELD OVERWRITE transform ON mapping_rule TYPE object;
DEFINE FIELD OVERWRITE notes ON mapping_rule TYPE option<string>;
DEFINE INDEX OVERWRITE idx_mapping_rule_crosswalk ON mapping_rule FIELDS crosswalk_id;
DEFINE INDEX OVERWRITE idx_mapping_rule_type ON mapping_rule FIELDS mapping_type;

DEFINE TABLE OVERWRITE evidence SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE mapping_rule_id ON evidence TYPE string;
DEFINE FIELD OVERWRITE source ON evidence TYPE string;
DEFINE FIELD OVERWRITE doc_uri ON evidence TYPE string;
DEFINE FIELD OVERWRITE page_number ON evidence TYPE int;
DEFINE FIELD OVERWRITE row_id ON evidence TYPE string;
DEFINE FIELD OVERWRITE snippet ON evidence TYPE string;
DEFINE FIELD OVERWRITE bbox ON evidence TYPE option<object>;
DEFINE FIELD OVERWRITE chunk_id ON evidence TYPE option<string>;
DEFINE INDEX OVERWRITE idx_evidence_rule ON evidence FIELDS mapping_rule_id;
DEFINE INDEX OVERWRITE idx_evidence_page_row ON evidence FIELDS page_number, row_id;

DEFINE TABLE OVERWRITE artifact_document SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE crosswalk_id ON artifact_document TYPE string;
DEFINE FIELD OVERWRITE source_url ON artifact_document TYPE string;
DEFINE FIELD OVERWRITE resolved_url ON artifact_document TYPE string;
DEFINE FIELD OVERWRITE content_type ON artifact_document TYPE string;
DEFINE FIELD OVERWRITE extension ON artifact_document TYPE string;
DEFINE FIELD OVERWRITE markdown ON artifact_document TYPE string;
DEFINE FIELD OVERWRITE status ON artifact_document TYPE string;
DEFINE FIELD OVERWRITE fetched_at ON artifact_document TYPE string;
DEFINE INDEX OVERWRITE idx_artifact_doc_crosswalk_url ON artifact_document FIELDS crosswalk_id, resolved_url UNIQUE;

DEFINE TABLE OVERWRITE artifact_chunk SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE document_id ON artifact_chunk TYPE string;
DEFINE FIELD OVERWRITE crosswalk_id ON artifact_chunk TYPE string;
DEFINE FIELD OVERWRITE ordinal ON artifact_chunk TYPE int;
DEFINE FIELD OVERWRITE text ON artifact_chunk TYPE string;
DEFINE INDEX OVERWRITE idx_artifact_chunk_doc_ord ON artifact_chunk FIELDS document_id, ordinal UNIQUE;
DEFINE INDEX OVERWRITE idx_artifact_chunk_crosswalk ON artifact_chunk FIELDS crosswalk_id;

DEFINE TABLE OVERWRITE ir_record SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE source_record_id ON ir_record TYPE string;
DEFINE FIELD OVERWRITE source_format ON ir_record TYPE string;
DEFINE FIELD OVERWRITE payload ON ir_record TYPE object;
DEFINE FIELD OVERWRITE created_at ON ir_record TYPE string;
DEFINE INDEX OVERWRITE idx_ir_record_source ON ir_record FIELDS source_record_id, source_format UNIQUE;

DEFINE TABLE OVERWRITE benchmark_run SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE crosswalk_id ON benchmark_run TYPE string;
DEFINE FIELD OVERWRITE endpoint ON benchmark_run TYPE string;
DEFINE FIELD OVERWRITE direction ON benchmark_run TYPE string;
DEFINE FIELD OVERWRITE n_records ON benchmark_run TYPE int;
DEFINE FIELD OVERWRITE summary_metrics ON benchmark_run TYPE object;
DEFINE FIELD OVERWRITE created_at ON benchmark_run TYPE string;

DEFINE TABLE OVERWRITE comparison_result SCHEMAFULL PERMISSIONS FULL;
DEFINE FIELD OVERWRITE benchmark_run_id ON comparison_result TYPE string;
DEFINE FIELD OVERWRITE source_record_id ON comparison_result TYPE string;
DEFINE FIELD OVERWRITE crosswalk_id ON comparison_result TYPE string;
DEFINE FIELD OVERWRITE direction ON comparison_result TYPE string;
DEFINE FIELD OVERWRITE metrics ON comparison_result TYPE object;
DEFINE FIELD OVERWRITE missing_fields ON comparison_result TYPE array<string>;
DEFINE FIELD OVERWRITE mismatched_fields ON comparison_result TYPE array<string>;
DEFINE FIELD OVERWRITE semantic_loss_rate ON comparison_result TYPE float;
DEFINE FIELD OVERWRITE diff_payload ON comparison_result TYPE object;
DEFINE FIELD OVERWRITE created_at ON comparison_result TYPE string;
DEFINE INDEX OVERWRITE idx_comparison_run ON comparison_result FIELDS benchmark_run_id;
DEFINE INDEX OVERWRITE idx_comparison_record ON comparison_result FIELDS source_record_id;

DEFINE TABLE OVERWRITE standard_has_element TYPE RELATION IN standard OUT element PERMISSIONS FULL;
DEFINE TABLE OVERWRITE crosswalk_maps_from TYPE RELATION IN crosswalk OUT standard PERMISSIONS FULL;
DEFINE TABLE OVERWRITE crosswalk_maps_to TYPE RELATION IN crosswalk OUT standard PERMISSIONS FULL;
DEFINE TABLE OVERWRITE crosswalk_has_rule TYPE RELATION IN crosswalk OUT mapping_rule PERMISSIONS FULL;
DEFINE TABLE OVERWRITE rule_has_evidence TYPE RELATION IN mapping_rule OUT evidence PERMISSIONS FULL;
DEFINE TABLE OVERWRITE crosswalk_has_artifact TYPE RELATION IN crosswalk OUT artifact_document PERMISSIONS FULL;
DEFINE TABLE OVERWRITE artifact_has_chunk TYPE RELATION IN artifact_document OUT artifact_chunk PERMISSIONS FULL;
DEFINE TABLE OVERWRITE element_parent_of TYPE RELATION IN element OUT element PERMISSIONS FULL;
DEFINE TABLE OVERWRITE benchmark_has_result TYPE RELATION IN benchmark_run OUT comparison_result PERMISSIONS FULL;
""".strip()
