const SOURCE_LABELS = {
  simulation: 'Simulation',
  telemetry: 'Telemetry',
  hybrid: 'Hybrid',
  cache: 'Cache',
};

const CONFIDENCE_LABELS = {
  estimated: 'Estimated',
  measured: 'Measured',
  hybrid: 'Hybrid',
};

const toFiniteNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const resolveSourceKey = (input) => {
  if (typeof input === 'string') {
    return input.toLowerCase();
  }
  if (!input || typeof input !== 'object') {
    return 'simulation';
  }
  const fromResult = input.data_source || input.requested_data_source;
  return typeof fromResult === 'string' ? fromResult.toLowerCase() : 'simulation';
};

export const getSourceLabel = (input) => {
  const sourceKey = resolveSourceKey(input);
  return SOURCE_LABELS[sourceKey] || SOURCE_LABELS.simulation;
};

export const getConfidenceKey = (input) => {
  if (typeof input === 'string') {
    const sourceKey = input.toLowerCase();
    if (sourceKey === 'telemetry') return 'measured';
    if (sourceKey === 'hybrid') return 'hybrid';
    return 'estimated';
  }

  const confidenceRaw = String(input?.confidence || '').toLowerCase();
  if (confidenceRaw.includes('measure')) return 'measured';
  if (confidenceRaw.includes('hybrid')) return 'hybrid';
  if (confidenceRaw.includes('estimate')) return 'estimated';

  const sourceKey = resolveSourceKey(input);
  if (sourceKey === 'telemetry') return 'measured';
  if (sourceKey === 'hybrid') return 'hybrid';
  return 'estimated';
};

export const getConfidenceLabel = (input) => CONFIDENCE_LABELS[getConfidenceKey(input)] || 'Estimated';

export const formatRatioPercent = (value, digits = 1) => {
  const parsed = toFiniteNumber(value);
  if (parsed == null) {
    return 'n/a';
  }
  return `${(parsed * 100).toFixed(digits)}%`;
};

export const formatPercentValue = (value, digits = 1) => {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return 'n/a';
    if (trimmed.endsWith('%')) return trimmed;
    const parsed = toFiniteNumber(trimmed);
    if (parsed == null) return trimmed;
    const percent = parsed <= 1 ? parsed * 100 : parsed;
    return `${percent.toFixed(digits)}%`;
  }

  const parsed = toFiniteNumber(value);
  if (parsed == null) {
    return 'n/a';
  }
  const percent = parsed <= 1 ? parsed * 100 : parsed;
  return `${percent.toFixed(digits)}%`;
};

export const toPercentNumber = (value) => {
  if (typeof value === 'string') {
    const trimmed = value.trim().replace('%', '');
    const parsed = toFiniteNumber(trimmed);
    if (parsed == null) return null;
    return parsed <= 1 ? parsed * 100 : parsed;
  }
  const parsed = toFiniteNumber(value);
  if (parsed == null) return null;
  return parsed <= 1 ? parsed * 100 : parsed;
};

export const formatDateTime = (value) => {
  if (!value) {
    return 'n/a';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString();
};

export const getTotalUniquePaths = (result) => {
  if (!result) return 0;
  return Number(result.total_unique_paths ?? result.top_paths?.length ?? 0);
};

export const getMarlHistoryRows = (result) => {
  if (!result) return [];
  if (Array.isArray(result.history) && result.history.length > 0) {
    return result.history;
  }
  const rounds = Number(result.rounds || 0);
  return Array.from({ length: rounds }, (_, idx) => ({
    round: idx + 1,
    red_win_rate: Number(result.red_win_rate || 0),
    blue_win_rate: Number(result.blue_win_rate || 0),
    status: 'Completed',
  }));
};