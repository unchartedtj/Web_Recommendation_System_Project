"""Kenya's 47 counties: the options for an internship's location (alphabetical).

Kept in ONE place: the partner form's dropdown loads this list from GET /api/counties, and
the opportunity validator only accepts these values.
"""
KENYAN_COUNTIES = sorted([
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa", "Homa Bay",
    "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi", "Kirinyaga", "Kisii",
    "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera",
    "Marsabit", "Meru", "Migori", "Mombasa", "Murang'a", "Nairobi", "Nakuru", "Nandi", "Narok",
    "Nyamira", "Nyandarua", "Nyeri", "Samburu", "Siaya", "Taita-Taveta", "Tana River",
    "Tharaka-Nithi", "Trans-Nzoia", "Turkana", "Uasin Gishu", "Vihiga", "Wajir", "West Pokot",
])

# Lower-case name → official spelling, so "nairobi" or "NAIROBI" is saved as "Nairobi".
_BY_LOWER = {c.lower(): c for c in KENYAN_COUNTIES}


def canonical_county(value: str) -> str | None:
    """The official spelling of a county name, or None if it isn't one of the 47."""
    return _BY_LOWER.get(value.strip().lower()) if isinstance(value, str) else None
