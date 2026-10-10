import { matchSummary } from '../utils/matchSummary.js';

describe('matchSummary', () => {
  it('describes a strong match with one missing essential skill and an interest match', () => {
    const text = matchSummary({
      breakdown: { grade_score: 0.72 },
      unmet_requirements: [],
      missing_essential_skills: ['React'],
      interest_match: true,
      sector: 'Web & Mobile Development',
    });
    expect(text).toBe("Strong grade match; you're missing 1 essential skill (React); "
      + 'matches your interest in Web & Mobile Development.');
  });

  it('mentions an essential minimum mark that is not met', () => {
    const text = matchSummary({
      breakdown: { grade_score: 0.3 },
      unmet_requirements: [{ unit: 'Object Oriented Programming', importance: 'essential',
        required: 60, your_mark: 52 }],
      missing_essential_skills: [],
      interest_match: false,
    });
    expect(text).toContain('Weak grade match');
    expect(text).toContain('below the minimum mark in Object Oriented Programming (52 vs 60)');
    expect(text).toContain('you have all the essential skills');
  });
});
