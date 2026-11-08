/**
 * Which Apply area to show on the internship details page.
 * Input is the GET /api/opportunities/:id response. Returns one of:
 *   'applied'     – the student has applied here (any status, including accepted)
 *   'placed'      – the student already has a confirmed placement elsewhere
 *   'closed'      – the internship is closed or past its deadline
 *   'incomplete'  – the profile must be completed first
 *   'unverified'  – the WBL office hasn't accepted the student's marks yet (transcript)
 *   'can_apply'   – show the Apply button
 */
import { daysUntil } from './deadline.js';

export function applyState({ opportunity, profile_complete, my_application, has_placement, marks_verified },
  today = new Date()) {
  if (my_application) return 'applied';
  if (has_placement) return 'placed';
  const pastDeadline = (daysUntil(opportunity?.application_deadline, today) ?? 0) < 0;
  if (!opportunity || opportunity.status !== 'open' || pastDeadline) return 'closed';
  if (!profile_complete) return 'incomplete';
  if (marks_verified === false) return 'unverified';
  return 'can_apply';
}
