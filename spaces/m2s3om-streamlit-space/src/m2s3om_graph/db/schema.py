def surreal_schema() -> str:
    return """
DEFINE TABLE OVERWRITE standard SCHEMAFULL;
DEFINE FIELD OVERWRITE name ON standard TYPE string;
DEFINE FIELD OVERWRITE version ON standard TYPE option<string>;
DEFINE FIELD OVERWRITE source_url ON standard TYPE option<string>;
DEFINE FIELD OVERWRITE description ON standard TYPE option<string>;

DEFINE TABLE OVERWRITE element SCHEMAFULL;
DEFINE FIELD OVERWRITE standard_id ON element TYPE record<standard>;
DEFINE FIELD OVERWRITE path ON element TYPE string;
DEFINE FIELD OVERWRITE label ON element TYPE string;
DEFINE FIELD OVERWRITE scope_note ON element TYPE option<string>;
DEFINE FIELD OVERWRITE constraints ON element TYPE array<object>;

DEFINE TABLE OVERWRITE definition SCHEMAFULL;
DEFINE FIELD OVERWRITE element_id ON definition TYPE record<element>;
DEFINE FIELD OVERWRITE text ON definition TYPE string;

DEFINE TABLE OVERWRITE example SCHEMAFULL;
DEFINE FIELD OVERWRITE element_id ON example TYPE record<element>;
DEFINE FIELD OVERWRITE text ON example TYPE string;

DEFINE TABLE OVERWRITE chunk SCHEMALESS;
DEFINE FIELD OVERWRITE standard_id ON chunk TYPE record<standard>;
DEFINE FIELD OVERWRITE element_id ON chunk TYPE option<record<element>>;
DEFINE FIELD OVERWRITE content ON chunk TYPE string;
DEFINE FIELD OVERWRITE source_url ON chunk TYPE option<string>;
DEFINE FIELD OVERWRITE anchor ON chunk TYPE option<string>;

DEFINE TABLE OVERWRITE crosswalk SCHEMAFULL;
DEFINE FIELD OVERWRITE source_standard_id ON crosswalk TYPE record<standard>;
DEFINE FIELD OVERWRITE target_standard_id ON crosswalk TYPE record<standard>;
DEFINE FIELD OVERWRITE created_at ON crosswalk TYPE string;
DEFINE FIELD OVERWRITE agent_version ON crosswalk TYPE string;

DEFINE TABLE OVERWRITE mapping SCHEMAFULL;
DEFINE FIELD OVERWRITE crosswalk_id ON mapping TYPE record<crosswalk>;
DEFINE FIELD OVERWRITE source_element_id ON mapping TYPE record<element>;
DEFINE FIELD OVERWRITE target_element_id ON mapping TYPE record<element>;
DEFINE FIELD OVERWRITE confidence ON mapping TYPE float;
DEFINE FIELD OVERWRITE justification ON mapping TYPE string;
DEFINE FIELD OVERWRITE transformation_hint ON mapping TYPE string;
DEFINE FIELD OVERWRITE ambiguity_flag ON mapping TYPE bool;
DEFINE FIELD OVERWRITE semantic_loss_flag ON mapping TYPE bool;
DEFINE FIELD OVERWRITE citations ON mapping TYPE array<object>;
DEFINE FIELD OVERWRITE status ON mapping TYPE string;

DEFINE TABLE OVERWRITE standard_has_element TYPE RELATION IN standard OUT element;
DEFINE TABLE OVERWRITE element_has_definition TYPE RELATION IN element OUT definition;
DEFINE TABLE OVERWRITE element_has_example TYPE RELATION IN element OUT example;
DEFINE TABLE OVERWRITE element_related_to_element TYPE RELATION IN element OUT element;
""".strip()
