const decisions = new Map();

function decisionKey(crosswalkId, sourceField, targetPath) {
  return `${crosswalkId}::${sourceField}::${targetPath ?? 'null'}`;
}

function parseCrosswalkId(crosswalkId) {
  const value = String(crosswalkId ?? '');
  const [sourceStandard] = value.split('_to_');
  return sourceStandard || value;
}

function parseTargetStandard(crosswalkId) {
  const value = String(crosswalkId ?? '');
  const [, targetStandard] = value.split('_to_');
  return targetStandard || value;
}

function sanitizeTsvField(value) {
  if (value == null) {
    return '';
  }
  return String(value).replace(/[\t\r\n]/g, ' ');
}

export function getSuggestApiUrl() {
  return import.meta.env.VITE_SUGGEST_API_URL || '/suggest';
}

export async function postSuggestRequest({
  sourceStandard,
  targetStandard,
  sourceField,
  targetSchemaFields,
  context,
}) {
  try {
    const response = await fetch(getSuggestApiUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        source_standard: sourceStandard,
        target_standard: targetStandard,
        source_field: sourceField,
        target_schema_fields: targetSchemaFields,
        context,
      }),
    });

    if (!response.ok) {
      throw new Error(`Suggestion request failed: ${response.status} ${response.statusText}`.trim());
    }

    return await response.json();
  } catch (err) {
    if (err instanceof Error && err.message.startsWith('Suggestion request failed:')) {
      throw err;
    }
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`Suggestion request failed: ${message}`);
  }
}

export function acceptCandidate(crosswalkId, sourceField, candidate) {
  const key = decisionKey(crosswalkId, sourceField, candidate?.target_path);
  decisions.set(key, {
    status: 'accepted',
    candidate,
    crosswalkId,
    sourceField,
    decidedAt: new Date(),
  });
}

export function rejectCandidate(crosswalkId, sourceField, candidate) {
  const key = decisionKey(crosswalkId, sourceField, candidate?.target_path);
  decisions.set(key, {
    status: 'rejected',
    candidate,
    crosswalkId,
    sourceField,
    decidedAt: new Date(),
  });
}

export function getDecision(crosswalkId, sourceField, candidate) {
  return decisions.get(decisionKey(crosswalkId, sourceField, candidate?.target_path));
}

export function getAcceptedCandidates() {
  return [...decisions.values()]
    .filter((entry) => entry.status === 'accepted')
    .map((entry) => ({
      crosswalkId: entry.crosswalkId,
      sourceField: entry.sourceField,
      candidate: entry.candidate,
      decidedAt: entry.decidedAt,
    }));
}

export function getRejectedCandidates() {
  return [...decisions.values()]
    .filter((entry) => entry.status === 'rejected')
    .map((entry) => ({
      crosswalkId: entry.crosswalkId,
      sourceField: entry.sourceField,
      candidate: entry.candidate,
      decidedAt: entry.decidedAt,
    }));
}

export function buildAcceptedTsv() {
  const header = 'source_standard\tsource_field\ttarget_path\tmapping_type\tconfidence\tevidence\tnotes\n';
  const rows = getAcceptedCandidates().map((entry) => {
    const candidate = entry.candidate ?? {};
    return [
      parseCrosswalkId(entry.crosswalkId),
      entry.sourceField,
      candidate.target_path,
      candidate.mapping_type,
      candidate.confidence,
      candidate.evidence,
      candidate.notes,
    ]
      .map(sanitizeTsvField)
      .join('\t');
  });

  return `${header}${rows.map((row) => `${row}\n`).join('')}`;
}

export function downloadAcceptedTsv(filenameOverride) {
  const filename = filenameOverride || 'accepted_candidates.tsv';
  const blob = new Blob([buildAcceptedTsv()], { type: 'text/tab-separated-values;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return filename;
}

export function buildSssomTsv(crosswalkId) {
  const header = 'subject_id\tpredicate_id\tobject_id\tmapping_justification\tconfidence\tsubject_label\tobject_label\tcomment\n';
  const sourceStandard = parseCrosswalkId(crosswalkId);
  const targetStandard = parseTargetStandard(crosswalkId);
  const rows = getAcceptedCandidates()
    .filter((entry) => entry.crosswalkId === crosswalkId)
    .map((entry) => {
      const candidate = entry.candidate ?? {};
      const mappingType = candidate.mapping_type;
      const predicateId =
        mappingType === 'direct'
          ? 'skos:exactMatch'
          : mappingType === 'conditional'
            ? 'skos:closeMatch'
            : mappingType === 'aggregation'
              ? 'skos:relatedMatch'
              : mappingType === 'missing'
                ? 'sssom:noMapping'
                : 'skos:relatedMatch';
      const comment = `${candidate.evidence ?? ''}${candidate.notes ? ` — ${candidate.notes}` : ''}`;
      return [
        `${sourceStandard}:${entry.sourceField}`,
        predicateId,
        candidate.target_path ? `${targetStandard}:${candidate.target_path}` : '',
        'semapv:ManualMappingCuration',
        typeof candidate.confidence === 'number' ? candidate.confidence : '',
        entry.sourceField,
        candidate.target_path ?? '',
        comment,
      ]
        .map(sanitizeTsvField)
        .join('\t');
    });

  return `${header}${rows.map((row) => `${row}\n`).join('')}`;
}

export function downloadSssomTsv(crosswalkId, filenameOverride) {
  const filename = filenameOverride || `sssom_${parseCrosswalkId(crosswalkId)}_to_${parseTargetStandard(crosswalkId)}.tsv`;
  const blob = new Blob([buildSssomTsv(crosswalkId)], { type: 'text/tab-separated-values;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return filename;
}
