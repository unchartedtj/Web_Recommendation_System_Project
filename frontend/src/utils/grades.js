/**
 * Strathmore's grading scale, used to show a letter next to each mark as it's typed.
 *   A 70+   B 60–69   C 50–59   D 40–49   E below 40
 * Returns '' when the box is empty or not a valid mark.
 */
export function letterGrade(mark) {
  if (mark === '' || mark === null || mark === undefined) return '';
  const value = Number(mark);
  if (Number.isNaN(value) || value < 0 || value > 100) return '';
  if (value >= 70) return 'A';
  if (value >= 60) return 'B';
  if (value >= 50) return 'C';
  if (value >= 40) return 'D';
  return 'E';
}
