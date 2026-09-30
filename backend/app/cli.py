"""Custom Flask CLI commands.

    flask create-admin      prompts for email, name and password
    flask seed-data         loads the unit catalog, demo partners and demo opportunities
"""
import click
from flask import Flask

from app.auth.services import create_user_with_profile
from app.auth.validators import validate_email, validate_password
from app.errors import ApiError


def register_cli(app: Flask):
    @app.cli.command("create-admin")
    @click.option("--email", prompt="Admin email", help="Login email for the admin.")
    @click.option("--name", prompt="Admin name", help="Display name for the admin.")
    @click.option("--password", prompt="Password", hide_input=True,
                  confirmation_prompt=True, help="At least 8 chars with a letter and a number.")
    def create_admin(email, name, password):
        """Create a system administrator (admins cannot self-register via the API)."""
        email = email.strip().lower()
        name = name.strip()
        problems = [m for m in (validate_email(email), validate_password(password)) if m]
        if not name:
            problems.append("Name is required")
        if problems:
            raise click.ClickException("; ".join(problems))

        try:
            user = create_user_with_profile(
                {"email": email, "password": password, "role": "system_admin", "name": name}
            )
        except ApiError as err:
            raise click.ClickException(err.message)
        click.secho(f"System admin created: {user.email} (user_id={user.user_id})", fg="green")

    @app.cli.command("seed-data")
    def seed_data():
        """Seed units, demo partners and opportunities (safe to run more than once)."""
        from app.seed.catalog import DEMO_PASSWORD
        from app.seed.seeder import seed_all

        summary = seed_all()
        click.secho("Seed complete.", fg="green")
        click.echo(f"  Academic units:      {summary['units']}")
        click.echo(f"  Opportunities:       {summary['opportunities']} "
                   f"({summary['requirements']} requirements)")
        if summary["removed_opportunities"] or summary["deleted_units"] or summary["deactivated_units"]:
            click.echo(f"  Cleaned up old data: {summary['removed_opportunities']} demo opportunities "
                       f"removed, {summary['deleted_units']} units deleted, "
                       f"{summary['deactivated_units']} units deactivated (still referenced)")
        click.echo(f"  Model fitted on:     {summary['model_opportunities']} open opportunities, "
                   f"{summary['model_units']} units")
        click.echo("  Demo partner logins (password: " + DEMO_PASSWORD + "):")
        for email in summary["partners"]:
            click.echo(f"    - {email}")
