/**
 * One internship in the Browse grid. The whole card is a link to the details page.
 * Shows title, company, sector, location, duration, slots, "Closes in X days" (highlighted
 * when under 7 days), up to 4 required skills, and the student's match % + badge
 * (only when their profile is complete, i.e. when the API sent match_percent).
 */
import { Link } from 'react-router-dom';
import { closesIn } from '../../utils/deadline.js';
import SkillChip from '../ui/SkillChip.jsx';
import StatusBadge from '../ui/StatusBadge.jsx';

const MAX_CHIPS = 4;

export default function OpportunityCard({ opp, from }) {
  const deadline = closesIn(opp.application_deadline);
  const extraSkills = (opp.skills?.length ?? 0) - MAX_CHIPS;
  const hasMatch = opp.match_percent !== undefined;

  return (
    <Link className="opp-card" to={`/student/opportunities/${opp.opportunity_id}`} state={{ from }}>
      <div className="opp-card__top">
        <h3 className="opp-card__title">{opp.title}</h3>
        {hasMatch && (
          <span className="opp-card__match" aria-label={`Your match ${Math.round(opp.match_percent)} percent`}>
            {Math.round(opp.match_percent)}%
          </span>
        )}
      </div>
      <p className="muted small">{opp.organization_name} · {opp.sector}</p>
      <ul className="opp-card__facts">
        <li><span aria-hidden="true">📍</span> {opp.location}</li>
        <li><span aria-hidden="true">⏱</span> {opp.duration_months} months</li>
        <li><span aria-hidden="true">👥</span> {opp.slots} {opp.slots === 1 ? 'slot' : 'slots'}</li>
        <li className={deadline.urgent ? 'deadline--urgent' : ''}>
          <span aria-hidden="true">📅</span> {deadline.label}
        </li>
      </ul>
      <div className="chips">
        {(opp.skills ?? []).slice(0, MAX_CHIPS).map((s) => (
          <SkillChip key={s.skill_id} name={s.name} essential={s.importance === 'essential'} />
        ))}
        {extraSkills > 0 && <span className="muted small">+{extraSkills} more</span>}
      </div>
      {hasMatch && <div className="opp-card__badge"><StatusBadge eligible={opp.meets_requirements} /></div>}
    </Link>
  );
}
