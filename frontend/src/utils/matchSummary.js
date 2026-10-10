/**
 * A one-line, plain-English explanation of a match, built only from the data, e.g.
 *   "Strong grade match; you're missing 1 essential skill (React); matches your interest
 *    in Web & Mobile Development."
 *
 * `match` needs: breakdown.grade_score, unmet_requirements, missing_essential_skills,
 * interest_match, and optionally sector (the opportunity's sector name).
 */

// Grade-score thresholds (cosine similarity, 0 to 1) for the wording.
const STRONG = 0.6;
const MODERATE = 0.4;

function plural(n, word) {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

export function matchSummary(match) {
  const parts = [];
  const grade = match.breakdown?.grade_score ?? 0;

  if (grade >= STRONG) parts.push('Strong grade match');
  else if (grade >= MODERATE) parts.push('Moderate grade match');
  else parts.push('Weak grade match');

  // Essential minimum marks the student doesn't reach (these make them "Below minimum").
  const unmet = (match.unmet_requirements ?? []).filter((u) => u.importance === 'essential');
  if (unmet.length) {
    const list = unmet.map((u) => `${u.unit} (${u.your_mark} vs ${u.required})`).join(', ');
    parts.push(`below the minimum mark in ${list}`);
  }

  const missing = match.missing_essential_skills ?? [];
  if (missing.length) {
    parts.push(`you're missing ${plural(missing.length, 'essential skill')} (${missing.join(', ')})`);
  } else {
    parts.push('you have all the essential skills');
  }

  if (match.interest_match) {
    parts.push(match.sector ? `matches your interest in ${match.sector}` : 'matches your career interests');
  }

  return `${parts.join('; ')}.`;
}
