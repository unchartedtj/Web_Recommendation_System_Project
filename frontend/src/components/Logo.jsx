/**
 * The Strathmore University logo (frontend/src/assets/strathmore-logo.png).
 * size="lg" (about 90px tall: login page, landing page) or "sm" (register page).
 * Importing the image lets Vite add it to the build with a cache-safe file name.
 */
import logoUrl from '../assets/strathmore-logo.png';

export default function Logo({ size = 'lg', className = '' }) {
  return (
    <img src={logoUrl} alt="Strathmore University logo" className={`logo logo--${size} ${className}`} />
  );
}
