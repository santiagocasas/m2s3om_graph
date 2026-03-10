# Kaigraph Talk Results Snapshot

This note pulls together the current demo-ready results from the frozen pipeline outputs in `exports/pipeline/latest/` and `exports/sssom/`.

## Headline Numbers

- total RDAMSC crosswalks in snapshot: `37`
- ready with authoritative SSSOM: `19` (`51.35%`)
- failed because source artifacts are unreachable: `11` (`29.73%`)
- failed after fetching because no rules were extracted: `7` (`18.92%`)
- total artifact checks: `45`
- artifact fetch success rate: `71.11%`

Source: `exports/pipeline/latest/rdamsc_stats_summary.json`

## Demo-Friendly Wins

- `rdamsc_c38` (CiteDCAT-AP / DataCite profile of DCAT-AP) is now `ready`
- `rdamsc_c38` produced `160` rules
- `rdamsc_c38` was solved by `deterministic_generic`, not LLM fallback
- `rdamsc_c36` (EAD to CIDOC CRM) also succeeded with `deterministic_generic`
- the app can now focus on three stable flows: browse, pipeline, convert

## Useful Breakdown Slides

### Pipeline outcomes

- ready: `19`
- failed_unreachable: `11`
- failed_parse: `7`

### Artifact hosts with most successful fetches

- `www.loc.gov`: `9`
- `www.cidoc-crm.org`: `7`
- `github.com`: `3`
- `www.bgbm.org`: `3`

### Artifact hosts with most failures

- `service.ncddc.noaa.gov`: `4`
- `gcmd.nasa.gov`: `3`
- `schema.datacite.org`: `3`

### Fetched artifact extensions

- `.xsl`: `7`
- `(none)`: `6`
- `.html`: `5`
- `.pdf`: `4`
- `.zip`: `3`

### Text size profile after conversion to markdown/text

- min: `2,770` chars
- median: `27,129` chars
- mean: `59,740.69` chars
- p90: `133,908` chars
- max: `200,000` chars

## Remaining Parse Targets

These are the current `failed_parse / no_rules_extracted` mappings in the frozen snapshot:

- `msc:c28` marc-machine-readable -> mods-metadata-object
- `msc:c29` mods-metadata-object -> marc-machine-readable
- `msc:c34` MIDAS-Heritage -> CIDOC CRM
- `msc:c23` oecd-minimum-data -> abcd-access-biological
- `msc:c19` isa-tab -> mage-tab
- `msc:c18` hispid-herbarium-information -> abcd-access-biological
- `msc:c3` darwin-core -> abcd-access-biological

## Suggested Demo Story

1. Start with the **Crosswalk Browser** to show authoritative SSSOM-backed mappings.
2. Open the **Pipeline** tab to show that the system records success/failure status per mapping.
3. Show `rdamsc_c38` as a concrete recovery story: table-heavy docs, now extracted successfully.
4. Finish in the **Convert** tab by fetching an OAI-PMH record in `oai_dc` and converting it to DataCite.

## Files To Cite In Slides

- `exports/pipeline/latest/rdamsc_stats_summary.json`
- `exports/pipeline/latest/rdamsc_pipeline_status.json`
- `exports/sssom/GENERATED_FROM_PIPELINE.md`
- `exports/sssom/generation_manifest.json`
- `exports/sssom/rdamsc_c38.sssom.tsv`
