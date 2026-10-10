/**
 * A skill as a chip, in one of four states (each with an icon AND text, not just colour):
 *   have               ✓ Java
 *   missing-essential  ✗ React · essential
 *   missing-desirable  ○ PHP · nice to have
 *   neutral            Java          (when we don't know the student's skills)
 */
const LOOK = {
  have: { icon: '✓', note: '', describe: 'you have this skill' },
  'missing-essential': { icon: '✗', note: 'essential', describe: 'missing, essential' },
  'missing-desirable': { icon: '○', note: 'nice to have', describe: 'missing, desirable' },
  neutral: { icon: '', note: '', describe: '' },
};

export default function SkillChip({ name, state = 'neutral', essential = false }) {
  const look = LOOK[state] ?? LOOK.neutral;
  const label = look.describe ? `${name}: ${look.describe}` : name;
  return (
    <span className={`skill-chip skill-chip--${state} ${essential ? 'skill-chip--essential' : ''}`}
      aria-label={label} title={label}>
      {look.icon && <span aria-hidden="true">{look.icon} </span>}
      {name}
      {look.note && <span className="skill-chip__note" aria-hidden="true"> · {look.note}</span>}
    </span>
  );
}

/** Pick the state from an API skill row ({importance, i_have}). */
export function skillState(skill) {
  if (skill.i_have === undefined) return 'neutral';
  if (skill.i_have) return 'have';
  return skill.importance === 'essential' ? 'missing-essential' : 'missing-desirable';
}
