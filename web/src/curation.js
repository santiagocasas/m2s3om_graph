const decisions = new Map();

function decisionKey(crosswalkId, sourceField, targetPath) {
  return `${crosswalkId}::${sourceField}::${targetPath ?? 'null'}`;
}

function parseCrosswalkId(crosswalkId) {
  const value = String(crosswalkId ?? '');
  const [sourceStandard] = value.split('_to_');
  return sourceStandard || value;
}

export function getSuggestApiUrl() {
  return import.meta.env.VITE_SUGGEST_API_URL || 'http://localhost:8000/suggest';
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
