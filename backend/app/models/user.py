"""User accounts and the three role-specific profile tables.

Every person has exactly one `users` row (credentials + role) and exactly one
matching row in students / industry_partners / system_admins:

    users (email, password_hash, role)
      ├── students           (admission_no, names, course, year)      if role = student
      ├── industry_partners  (organization, contact person, phone)    if role = industry_partner
      └── system_admins      (name)                                   if role = system_admin

Login only needs the `users` table; the profile table holds the role-specific details.
(See the top of placement.py for how to read db.Column / db.relationship.)
"""
import enum

# werkzeug (part of Flask) provides secure password hashing.
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class UserRole(str, enum.Enum):
    """The three kinds of user. Inheriting from str lets a role compare equal to its text."""
    STUDENT = "student"
    INDUSTRY_PARTNER = "industry_partner"
    SYSTEM_ADMIN = "system_admin"


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)   # unique: one account per email
    # We NEVER store the real password, only a one-way hash of it (see set_password).
    password_hash = db.Column(db.String(255), nullable=False)
    # values_callable stores the lowercase values ('student') rather than the enum names.
    role = db.Column(
        db.Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    # One-to-one links to the role profile (uselist=False). Only one is populated per user.
    # e.g. user.student is the Student row for a student, and None for a partner.
    student = db.relationship("Student", back_populates="user", uselist=False,
                              cascade="all, delete-orphan")
    industry_partner = db.relationship("IndustryPartner", back_populates="user", uselist=False,
                                       cascade="all, delete-orphan")
    system_admin = db.relationship("SystemAdmin", back_populates="user", uselist=False,
                                   cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash the password and store the hash.

        A hash is one-way: you can't turn it back into the password. It also includes a
        random "salt", so two users with the same password get different hashes.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """At login: hash the typed password the same way and compare with the stored hash."""
        return check_password_hash(self.password_hash, password)

    # @property lets you write user.profile (no brackets), like reading a normal attribute.
    @property
    def profile(self):
        """Return whichever role profile belongs to this user."""
        return {
            UserRole.STUDENT: self.student,
            UserRole.INDUSTRY_PARTNER: self.industry_partner,
            UserRole.SYSTEM_ADMIN: self.system_admin,
        }.get(self.role)

    @property
    def display_name(self) -> str:
        """Friendly name shown in the UI ("Welcome, <name>")."""
        p = self.profile
        if self.role == UserRole.STUDENT and p:
            return f"{p.first_name} {p.last_name}"
        if self.role == UserRole.INDUSTRY_PARTNER and p:
            return p.organization_name
        if self.role == UserRole.SYSTEM_ADMIN and p:
            return p.name
        return self.email   # fallback if the profile row is somehow missing

    def __repr__(self):
        # How the object prints when debugging, e.g. <User 3 jane@x.com (student)>
        return f"<User {self.user_id} {self.email} ({self.role.value})>"


class Student(db.Model):
    __tablename__ = "students"
    __table_args__ = (
        db.CheckConstraint("year_of_study BETWEEN 1 AND 4", name="ck_students_year_of_study"),
    )

    student_id = db.Column(db.Integer, primary_key=True)
    # unique=True on user_id is what makes this ONE-to-one with users.
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"),
                        unique=True, nullable=False)
    # Stored as a string (keeps leading zeros); validated as digits-only at the API.
    admission_no = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    course = db.Column(db.String(150), nullable=False)
    year_of_study = db.Column(db.SmallInteger, nullable=False)

    user = db.relationship("User", back_populates="student")
    grade_profiles = db.relationship("GradeProfile", back_populates="student",
                                     cascade="all, delete-orphan")
    recommendations = db.relationship("Recommendation", back_populates="student",
                                      cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="student",
                                   cascade="all, delete-orphan")
    placement_records = db.relationship("PlacementRecord", back_populates="student")


class IndustryPartner(db.Model):
    __tablename__ = "industry_partners"

    partner_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"),
                        unique=True, nullable=False)
    organization_name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)

    user = db.relationship("User", back_populates="industry_partner")
    # partner.opportunities = every opportunity this partner has posted.
    opportunities = db.relationship("InternshipOpportunity", back_populates="partner",
                                    cascade="all, delete-orphan")


class SystemAdmin(db.Model):
    __tablename__ = "system_admins"

    admin_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"),
                        unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)

    user = db.relationship("User", back_populates="system_admin")
