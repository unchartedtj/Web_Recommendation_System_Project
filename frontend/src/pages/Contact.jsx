/**
 * Contact us (/contact): how students and industry partners reach the WBL office.
 */
import RoleLayout from '../components/RoleLayout.jsx';

export const CONTACT = {
  email: 'admin.wbl@strathmore.edu',
  phone: '0712345678',
};

export default function Contact() {
  return (
    <RoleLayout title="Contact us">
      <p className="muted">
        Questions about placements, your account or an internship posting? Get in touch with the
        WBL office.
      </p>
      <div className="panel contact-details">
        <dl>
          <dt>Email</dt>
          <dd><a href={`mailto:${CONTACT.email}`}>{CONTACT.email}</a></dd>
          <dt>Phone</dt>
          <dd><a href={`tel:${CONTACT.phone}`}>{CONTACT.phone}</a></dd>
          <dt>Office hours</dt>
          <dd>Monday to Friday, 8:00 am – 5:00 pm</dd>
        </dl>
      </div>
    </RoleLayout>
  );
}
