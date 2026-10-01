"""Custom Flask CLI commands (run them in a terminal, from the backend folder).

    flask create-admin      prompts for email, name and password
    flask seed-data         loads the unit catalog, demo partners and demo opportunities

`click` is the library Flask uses to build terminal commands: @click.option defines
an input, and prompt=... makes the command ask for it if you didn't type it.
"""
import click
from flask import Flask

from app.auth.services import create_user_with_profile
from app.auth.validators import validate_email, validate_password
from app.errors import ApiError


def register_cli(app: Flask):
    """Attach our commands to the app (called from create_app)."""

    @app.cli.command("create-admin")
    @click.option("--email", prompt="Admin email", help="Login email for the admin.")
    @click.option("--name", prompt="Admin name", help="Display name for the admin.")
    # hide_input: the password isn't shown while typing; confirmation_prompt: type it twice.
    @click.option("--password", prompt="Password", hide_input=True,
                  confirmation_prompt=True, help="At least 8 chars with a letter and a number.")
    def create_admin(email, name, password):
        """Create a system administrator (admins cannot self-register via the API)."""
        email = email.strip().lower()   # remove spaces and store emails in lowercase
        name = name.strip()
        # Reuse the same rules as sign-up. Each validator returns an error message or None;
        # the list keeps only the real messages.
        problems = [m for m in (validate_email(email), validate_password(password)) if m]
        if not name:
            problems.append("Name is required")
        if problems:
            # ClickException prints the message in red and stops the command.
            raise click.ClickException("; ".join(problems))

        try:
            # Same function the register endpoint uses: creates the users row + the
            # system_admins row together in one transaction.
            user = create_user_with_profile(
                {"email": email, "password": password, "role": "system_admin", "name": name}
            )
        except ApiError as err:           # e.g. "Email already in use"
            raise click.ClickException(err.message)
        click.secho(f"System admin created: {user.email} (user_id={user.user_id})", fg="green")

    @app.cli.command("seed-data")
    def seed_data():
        """Seed units, demo partners and opportunities (safe to run more than once)."""
        # Imported here (not at the top) so these modules only load when the command runs.
        from app.seed.catalog import DEMO_PASSWORD
        from app.seed.seeder import seed_all

        summary = seed_all()   # does all the work and returns counts for the printout below
        click.secho("Seed complete.", fg="green")
        click.echo(f"  Academic units:      {summary['units']}")
        click.echo(f"  Opportunities:       {summary['opportunities']} "
                   f"({summary['requirements']} requirements)")
        # Only mention clean-up if something was actually cleaned up.
        if summary["removed_opportunities"] or summary["deleted_units"] or summary["deactivated_units"]:
            click.echo(f"  Cleaned up old data: {summary['removed_opportunities']} demo opportunities "
                       f"removed, {summary['deleted_units']} units deleted, "
                       f"{summary['deactivated_units']} units deactivated (still referenced)")
        click.echo(f"  Model fitted on:     {summary['model_opportunities']} open opportunities, "
                   f"{summary['model_units']} units")
        click.echo("  Demo partner logins (password: " + DEMO_PASSWORD + "):")
        for email in summary["partners"]:
            click.echo(f"    - {email}")
