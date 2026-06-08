from sqlalchemy.dialects.mysql import DOUBLE
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import Integer, String, JSON, ForeignKey, Boolean, TIMESTAMP, Index, Float, UniqueConstraint
from datetime import datetime
from typing import Optional, List
from extensions import app, get_db, utc_tz, os, Base, convert_from_utc

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=True)
    phone: Mapped[str] = mapped_column(String(13), nullable=False)
    gender: Mapped[str] = mapped_column(String(6), nullable=True)
    type: Mapped[str] = mapped_column(String(10), nullable=True) # Mainstream, Credit
    year_id: Mapped[int] = mapped_column(Integer, ForeignKey('years.id', ondelete="CASCADE", name="fk_year_user"),
                                         nullable=True)
    year: Mapped['Year'] = relationship('Year', back_populates='users', cascade='save-update, merge')
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id', ondelete="CASCADE", name="fk_department_user"),
                                               nullable=True)
    department: Mapped['Department'] = relationship('Department', back_populates='users', cascade='save-update, merge')
    faculty_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('faculties.id', ondelete="CASCADE",
                                                                          name="fk_faculty_user"), nullable=True)
    faculty: Mapped[Optional['Faculty']] = relationship('Faculty', back_populates='users', cascade='save-update, merge')
    section: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    is_early_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey('roles.id', name="fk_role_user"), nullable=True)
    role: Mapped['Role'] = relationship('Role', back_populates='users', cascade='save-update, merge')
    manages: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=dict)
    details: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=dict)
    google_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    google_name: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    google_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    google_avatar: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    google_refresh_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ips: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)  # List of IPs used
    # for login
    refresh_token: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    refresh_expire_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz),
                                                 nullable=True)
    modified_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz),
                                                  onupdate=lambda: datetime.now(utc_tz), nullable=True)
    pending_user: Mapped['PendingUser'] = relationship(
        'PendingUser',
        back_populates='user',
        uselist=False,
        cascade='all, delete-orphan'
    )
    materials: Mapped[List['Material']] = relationship(
        'Material',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    grades: Mapped[List['Grade']] = relationship(
        'Grade',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    tasks: Mapped[List['Task']] = relationship(
        'Task',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    announcements: Mapped[List['Announcement']] = relationship(
        'Announcement',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    notifications: Mapped[List['Notification']] = relationship(
        'Notification',
        secondary='user_notifications',
        back_populates='users',
    )
    marks: Mapped[List['Mark']] = relationship(
        'Mark',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    events: Mapped[List['Event']] = relationship(
        'Event',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    roadmaps: Mapped[List['Roadmap']] = relationship(
        'Roadmap',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    questions: Mapped[List['Question']] = relationship(
        'Question',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    answers: Mapped[List['Answer']] = relationship(
        'Answer',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    timetables: Mapped[List['Timetable']] = relationship(
        'Timetable',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    reviews: Mapped[List['Review']] = relationship(
        'Review',
        back_populates='author',
        cascade='all, delete-orphan'
    )
    going_events: Mapped[List['Event']] = relationship(
        'Event',
        back_populates='users',
        cascade='all, delete-orphan'
    )
    logs: Mapped[List['Log']] = relationship(
        'Log',
        back_populates='user',
        cascade='all, delete-orphan'
    )
    subjects: Mapped[List['Subject']] = relationship(
        'Subject',
        secondary='user_subject_links',
        back_populates='users',
    )
    request_limits: Mapped[List['RequestLimit']] = relationship(
        'RequestLimit',
        back_populates='user',
        cascade='all, delete-orphan'
    )
    __table_args__ = (
        Index('idx_user_email', 'email', unique=True),
        Index('idx_user_phone', 'phone', unique=True),
        Index('idx_user_google_id', 'google_id', unique=True),
        Index('idx_user_google_email', 'google_email', unique=True),
        # Composite User Indexes
        Index('idx_user_faculty_name', 'faculty_id', 'name'),
        Index('idx_faculty_department_name', 'faculty_id', 'department_id', 'name'),
        Index('idx_status_faculty_name', 'status', 'faculty_id', 'name'),
        Index('idx_user_refresh_token_refresh_expire_at', 'refresh_token','refresh_expire_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'gender': self.gender,
            'type': self.type,
            'year': self.year.min_to_dict() if self.year else None,
            'department': self.department.min_to_dict() if self.department else None,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'section': self.section,
            'status': self.status,
            'is_early_access': self.is_early_access,
            'role': self.role.min_to_dict() if self.role else None,
            'manages': self.manages,
            'details': self.details,
            'pending_user': self.pending_user.min_to_dict() if self.pending_user else None,
            'google_name': self.google_name,
            'google_email': self.google_email,
            'google_avatar': self.google_avatar,
            'ips': self.ips,
            'notifications_count': len(self.notifications),
            'enrolled_courses_count': len(self.subjects),
            'created_at': convert_from_utc(self.created_at).strftime("%d-%m-%Y %H:%M:%S") if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).strftime("%d-%m-%Y %H:%M:%S") if self.modified_at else None,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'gender': self.gender,
            'type': self.type,
            'section': self.section,
            'status': self.status,
            'is_early_access': self.is_early_access,
            'manages': self.manages,
            'details': self.details,
            'google_name': self.google_name,
            'google_email': self.google_email,
            'google_avatar': self.google_avatar,
            'ips': self.ips,
            'created_at': convert_from_utc(self.created_at).strftime('%d-%m-%Y %H:%M:%S') if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).strftime('%d-%m-%Y %H:%M:%S') if self.modified_at else None,
        }
    def full_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'gender': self.gender,
            'type': self.type,
            'year': self.year.min_to_dict() if self.year else None,
            'department': self.department.min_to_dict() if self.department else None,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'section': self.section,
            'status': self.status,
            'is_early_access': self.is_early_access,
            'role': self.role.min_to_dict() if self.role else None,
            'manages': self.manages,
            'details': self.details,
            'pending_user': self.pending_user.url if self.pending_user else None,
            'google_id': self.google_id,
            'google_name': self.google_name,
            'google_email': self.google_email,
            'google_avatar': self.google_avatar,
            'ips': self.ips,
            'notifications_count': len(self.notifications),
            "subjects": [subject.min_to_dict() for subject in self.subjects] if self.subjects else [],
            'created_at': convert_from_utc(self.created_at).strftime('%d-%m-%Y %H:%M:%S') if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).strftime('%d-%m-%Y %H:%M:%S') if self.modified_at else None,
        }
class PendingUser(Base):
    __tablename__ = 'pending_users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete="CASCADE", name="fk_pending_user_user"),
                                         nullable=False)
    user: Mapped['User'] = relationship('User', back_populates='pending_user')
    url: Mapped[str] = mapped_column(String(100), nullable=False)
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user': self.user.min_to_dict() if self.user else None,
            'url': self.url,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'url': self.url,
        }
class Year(Base):
    __tablename__ = 'years'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    users: Mapped[List['User']] = relationship(
        'User',
        back_populates='year',
        cascade='all, delete-orphan'
    )
    subjects: Mapped[List['Subject']] = relationship(
        'Subject',
        back_populates='year',
        cascade='all, delete-orphan'
    )
    tasks: Mapped[List['Task']] = relationship(
        'Task',
        back_populates='year',
        cascade='all, delete-orphan'
    )
    announcements: Mapped[List['Announcement']] = relationship(
        'Announcement',
        back_populates='year',
        cascade='all, delete-orphan'
    )
    events: Mapped[List['Event']] = relationship(
        'Event',
        back_populates='year',
        cascade='all, delete-orphan'
    )
    roadmaps: Mapped[List['Roadmap']] = relationship(
        'Roadmap',
        back_populates='year',
        cascade='all, delete-orphan'
    )
    questions: Mapped[List['Question']] = relationship(
        'Question',
        back_populates='year',
        cascade='all, delete-orphan'
    )
    timetables: Mapped[List['Timetable']] = relationship(
        'Timetable',
        back_populates='year',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('idx_year', 'year', unique=True),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'year': self.year,
            'details': self.details,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'year': self.year,
            'details': self.details,
        }
class Department(Base):
    __tablename__ = 'departments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=True)  # e.g., "CMP", "CSE", "ECE"
    faculty_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('faculties.id', ondelete="cascade",
                                                                          name="fk_faculty_department"),
                                                     nullable=True)
    faculty: Mapped[Optional['Faculty']] = relationship('Faculty', back_populates='departments', cascade='save-update, merge')
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict) # Contains Sections
    study_type: Mapped[str] = mapped_column(String(12), nullable=True)  # e.g., "Mainstream", "Credit"
    users: Mapped[List['User']] = relationship(
        'User',
        back_populates='department',
        cascade='all, delete-orphan'
    )
    subjects: Mapped[List['Subject']] = relationship(
        'Subject',
        back_populates='department',
        cascade='all, delete-orphan'
    )
    tasks: Mapped[List['Task']] = relationship(
        'Task',
        back_populates='department',
        cascade='all, delete-orphan'
    )
    announcements: Mapped[List['Announcement']] = relationship(
        'Announcement',
        back_populates='department',
        cascade='all, delete-orphan'
    )
    events: Mapped[List['Event']] = relationship(
        'Event',
        back_populates='department',
        cascade='all, delete-orphan'
    )
    roadmaps: Mapped[List['Roadmap']] = relationship(
        'Roadmap',
        back_populates='department',
        cascade='all, delete-orphan'
    )
    questions: Mapped[List['Question']] = relationship(
        'Question',
        back_populates='department',
        cascade='all, delete-orphan'
    )
    timetables: Mapped[List['Timetable']] = relationship(
        'Timetable',
        back_populates='department',
        cascade='all, delete-orphan'
    )
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'details': self.details,
            'study_type': self.study_type,
            'code': self.code,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'details': self.details,
            'study_type': self.study_type,
            'code': self.code,
        }
    __table_args__ = (
        # Composite Indexes
        Index('idx_department_faculty_name', 'faculty_id', 'name'),
        Index('idx_department_study_type_name', 'study_type', 'name'),
        Index('idx_department_faculty_study_type_name', 'faculty_id', 'study_type', 'name', unique=True),
        Index('idx_department_faculty_study_type_code', 'faculty_id', 'study_type', 'code', unique=True),
    )
class Faculty(Base):
    __tablename__ = 'faculties'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    users: Mapped[List['User']] = relationship(
        'User',
        back_populates='faculty',
        cascade='all, delete-orphan'
    )
    departments: Mapped[List['Department']] = relationship(
        'Department',
        back_populates='faculty',
        cascade='all, delete-orphan'
    )
    announcements: Mapped[List['Announcement']] = relationship(
        'Announcement',
        back_populates='faculty',
        cascade='all, delete-orphan'
    )
    events: Mapped[List['Event']] = relationship(
        'Event',
        back_populates='faculty',
        cascade='all, delete-orphan'
    )
    roadmaps: Mapped[List['Roadmap']] = relationship(
        'Roadmap',
        back_populates='faculty',
        cascade='all, delete-orphan'
    )
    questions: Mapped[List['Question']] = relationship(
        'Question',
        back_populates='faculty',
        cascade='all, delete-orphan'
    )
    timetables: Mapped[List['Timetable']] = relationship(
        'Timetable',
        back_populates='faculty',
        cascade='all, delete-orphan'
    )
    tasks: Mapped[List['Task']] = relationship(
        'Task',
        back_populates='faculty',
        cascade='all, delete-orphan'
    )
    subjects: Mapped[List['Subject']] = relationship(
        'Subject',
        back_populates='faculty',
        cascade='all, delete-orphan'
    )
    __table_args__ = (
        Index('idx_faculty_name', 'name', unique=True),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'details': self.details,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'details': self.details,
        }
class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=True, default=4)
    users: Mapped[List['User']] = relationship(
        'User',
        back_populates='role',
    )
    exact_roles: Mapped[List['ExactRole']] = relationship(
        'ExactRole',
        secondary='role_links',
        back_populates='roles',
    )

    __table_args__ = (
        Index('idx_role_name', 'name', unique=True),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'level': self.level,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'level': self.level,
            'permissions': [exact_role.name for exact_role in self.exact_roles],
            'permissions_count': len(self.exact_roles) if self.exact_roles else 0,
            'users_count': len(self.users) if self.users else 0,
        }
    def full_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'level': self.level,
            'permissions': [exact_role.name for exact_role in self.exact_roles] if self.exact_roles else [],
            'permissions_count': len(self.exact_roles) if self.exact_roles else 0,
            'users': [user.min_to_dict() for user in self.users] if self.users else [],
            'users_count': len(self.users) if self.users else 0,
        }
class RoleLink(Base):
    __tablename__ = 'role_links'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey('roles.id', ondelete="CASCADE", name="fk_role_role_link"),
                                         nullable=False)
    exact_role_id: Mapped[int] = mapped_column(Integer, ForeignKey('exact_roles.id', ondelete="CASCADE", name="fk_exact_role_role_link"),
                                               nullable=False)
    role: Mapped['Role'] = relationship('Role', backref='role_links_associations')
    exact_role: Mapped['ExactRole'] = relationship('ExactRole', backref='role_links_associations')

    __table_args__ = (
        # Composite Indexes
        Index('idx_role_exact_role', 'role_id', 'exact_role_id', unique=True),
        Index('idx_exact_role_role', 'exact_role_id', 'role_id'),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'role_id': self.role_id,
            'exact_role_id': self.exact_role_id,
            'role': self.role.min_to_dict() if self.role else None,
            'exact_role': self.exact_role.min_to_dict() if self.exact_role else None,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'role_id': self.role_id,
            'exact_role_id': self.exact_role_id,
        }
class ExactRole(Base):
    __tablename__ = 'exact_roles'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    roles: Mapped[List['Role']] = relationship(
        'Role',
        secondary='role_links',
        back_populates='exact_roles',
    )

    __table_args__ = (
        Index('idx_exact_role_name', 'name', unique=True),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }
class UserSubjectLink(Base):
    __tablename__ = 'user_subject_links'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete="CASCADE", name="fk_user_user_subject_link"),
                                         nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey('subjects.id', ondelete="CASCADE", name="fk_subject_user_subject_link"),
                                            nullable=False)
    user: Mapped['User'] = relationship('User', backref='user_subject_links_associations')
    subject: Mapped['Subject'] = relationship('Subject', backref='user_subject_links_associations')
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subject_id': self.subject_id,
            'user': self.user.min_to_dict() if self.user else None,
            'subject': self.subject.min_to_dict() if self.subject else None,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subject_id': self.subject_id,
        }
class Subject(Base):
    __tablename__ = 'subjects'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(15), nullable=True)  # e.g., "CS101", "MATH202"
    year_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('years.id', ondelete="CASCADE",
                                                                       name="fk_year_subject"), nullable=True)
    year: Mapped[Optional['Year']] = relationship('Year', back_populates='subjects', cascade='save-update, merge')
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id', ondelete="CASCADE", name="fk_department_subject"),
                                               nullable=True)
    department: Mapped['Department'] = relationship('Department', back_populates='subjects')
    faculty_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('faculties.id', ondelete="CASCADE", name="fk_faculty_subject"),
                                                        nullable=True)
    faculty: Mapped[Optional['Faculty']] = relationship('Faculty', back_populates='subjects', cascade='save-update, merge')
    details: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=dict)
    is_old: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    year_rank: Mapped[int] = mapped_column(Integer, nullable=True)
    term: Mapped[int] = mapped_column(Integer, nullable=True)
    credits: Mapped[int] = mapped_column(Integer, nullable=True)
    tasks: Mapped[List['Task']] = relationship(
        'Task',
        back_populates='subject',
        cascade='all, delete-orphan'
    )
    announcements: Mapped[List['Announcement']] = relationship(
        'Announcement',
        back_populates='subject',
        cascade='all, delete-orphan'
    )
    materials: Mapped[List['Material']] = relationship(
        'Material',
        back_populates='subject',
        cascade="all, delete-orphan"
    )
    grades: Mapped[List['Grade']] = relationship(
        'Grade',
        back_populates='subject',
        cascade="all, delete-orphan"
    )
    marks: Mapped[List['Mark']] = relationship(
        'Mark',
        back_populates='subject',
        cascade='all, delete-orphan'
    )
    questions: Mapped[List['Question']] = relationship(
        'Question',
        back_populates='subject',
        cascade='all, delete-orphan'
    )
    users: Mapped[List['User']] = relationship(
        'User',
        secondary='user_subject_links',
        back_populates='subjects',
    )
    roadmap_courses: Mapped[List['RoadmapCourse']] = relationship(
        'RoadmapCourse',
        back_populates='subject',
        cascade='all, delete-orphan'
    )
    def user_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'department': self.department.min_to_dict() if self.department else None,
            'year': self.year.min_to_dict() if self.year else None,
            'details': self.details,
            'credits': self.credits,
            'is_old': self.is_old,
            'year_rank': self.year_rank,
            'term': self.term,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'details': self.details,
            'credits': self.credits,
            'is_old': self.is_old,
            'year_rank': self.year_rank,
            'term': self.term,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'year': self.year.min_to_dict() if self.year else None,
            'department': self.department.min_to_dict() if self.department else None,
            'details': self.details,
            'credits': self.credits,
            'is_old': self.is_old,
            'year_rank': self.year_rank,
            'term': self.term,
            "users_count": len(self.users) if self.users else 0,
            "users": [user.min_to_dict() for user in self.users] if self.users else [],
        }
    def full_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'year': self.year.min_to_dict() if self.year else None,
            'department': self.department.min_to_dict() if self.department else None,
            'details': self.details,
            'credits': self.credits,
            'is_old': self.is_old,
            'year_rank': self.year_rank,
            'term': self.term,
        }
    __table_args__ = (
        # Composite Indexes
        Index('idx_subject_faculty_department_year_code', 'faculty_id', 'department_id', 'year_id', 'code',
              unique=True),
        Index('idx_subject_faculty_department_year_name', 'faculty_id', 'department_id', 'year_id', 'code'),
        Index('idx_subject_year_department_is_old_name', 'year_id', 'department_id', 'is_old', 'name'),
    )
class Material(Base):
    __tablename__ = 'materials'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    url: Mapped[str] = mapped_column(String(200), nullable=True)
    subject_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('subjects.id', ondelete="CASCADE",
                                                                          name="fk_subject_material"), nullable=True)
    subject: Mapped[Optional['Subject']] = relationship('Subject', back_populates='materials',
                                                        cascade='save-update, merge')
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_material", ondelete="SET NULL"),
                                           nullable=False)
    author: Mapped['User'] = relationship('User', back_populates='materials')
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('materials.id', ondelete="CASCADE", name="fk_parent_material"),
                                                     nullable=True)
    parent: Mapped[Optional['Material']] = relationship('Material', remote_side=[id], backref=backref('children',
                                                                                               cascade='all, delete-orphan'))
    details: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=dict)
    modified_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(utc_tz),
        onupdate=lambda: datetime.now(utc_tz)
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(utc_tz)
    )
    __table_args__ = (
        # Composite Indexes
        Index('idx_material_subject_parent', 'subject_id', 'parent_id'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'parent_id': self.parent_id,
            'details': self.details,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def user_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'subject': self.subject.min_to_dict() if self.subject else None,
            'parent_id': self.parent_id,
            'details': self.details,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'subject': self.subject.min_to_dict() if self.subject else None,
            'author': self.author.min_to_dict() if self.author else None,
            'parent_id': self.parent_id,
            'parent': self.parent.min_to_dict() if self.parent else None,
            'details': self.details,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }

class Grade(Base):
    __tablename__ = 'grades'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    url: Mapped[str] = mapped_column(String(200), nullable=True)
    subject_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('subjects.id', ondelete="CASCADE",
                                                                          name="fk_subject_grade"), nullable=True)
    subject: Mapped[Optional['Subject']] = relationship('Subject', back_populates='grades',
                                                        cascade='save-update, merge')
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_grade", ondelete="SET NULL"),
                                           nullable=False)
    author: Mapped['User'] = relationship('User', back_populates='grades')
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('grades.id', ondelete="CASCADE", name="fk_parent_grade"),
                                                     nullable=True)
    parent: Mapped[Optional['Grade']] = relationship('Grade', remote_side=[id], backref=backref('children',
                                                                                               cascade='all, delete-orphan'))
    details: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=dict)
    modified_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(utc_tz),
        onupdate=lambda: datetime.now(utc_tz)
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(utc_tz)
    )
    __table_args__ = (
        # Composite Indexes
        Index('idx_grade_subject_parent', 'subject_id', 'parent_id'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'parent_id': self.parent_id,
            'details': self.details,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def user_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'subject': self.subject.min_to_dict() if self.subject else None,
            'parent_id': self.parent_id,
            'details': self.details,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'subject': self.subject.min_to_dict() if self.subject else None,
            'author': self.author.min_to_dict() if self.author else None,
            'parent_id': self.parent_id,
            'parent': self.parent.min_to_dict() if self.parent else None,
            'details': self.details,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }

class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=True)
    urls: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)
    links: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)
    url: Mapped[str] = mapped_column(String(100), nullable=True)
    type: Mapped[str] = mapped_column(String(10), nullable=True) # e.g., "Exam", "Assignment", "Project", "Task"
    year_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('years.id', ondelete="CASCADE",
                                                                       name="fk_year_task"), nullable=True)
    year: Mapped[Optional['Year']] = relationship('Year', back_populates='tasks', cascade='save-update, merge')
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id', ondelete="CASCADE", name="fk_department_task"),
                                               nullable=False)
    department: Mapped['Department'] = relationship('Department', back_populates='tasks')
    faculty_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('faculties.id', ondelete="CASCADE",
                                                                          name="fk_faculty_task"), nullable=True)
    faculty: Mapped[Optional['Faculty']] = relationship('Faculty', back_populates='tasks', cascade='save-update, merge')
    details: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=dict)
    deadline: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False) # for datetime up to minutes
    due_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True) # for day only
    modified_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(utc_tz),
        onupdate=lambda: datetime.now(utc_tz)
    )
    subject_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('subjects.id', ondelete="CASCADE", name="fk_subject_task"),
                                                    nullable=True)
    subject: Mapped['Subject'] = relationship('Subject', back_populates='tasks')
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_task", ondelete="SET NULL"),
                                           nullable=False)
    author: Mapped['User'] = relationship('User', back_populates='tasks')
    __table_args__ = (
        # Composite Indexes
        Index('idx_task_type_faculty_department_year_subject_due_date_name', 'type', 'faculty_id', 'department_id', 'year_id', 'subject_id','due_date','name'),
        Index('idx_task_type_faculty_department_year_name', 'type', 'faculty_id', 'department_id', 'year_id', 'name'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'urls': self.urls,
            'url': self.url,
            'links': self.links,
            'type': self.type,
            'details': self.details,
            'deadline': convert_from_utc(self.deadline).strftime("%d-%m-%Y %H:%M:%S") if self.deadline else None,
            'due_date': convert_from_utc(self.due_date).strftime("%d-%m-%Y") if self.due_date else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
        }
    def user_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'urls': self.urls,
            'url': self.url,
            'links': self.links,
            'type': self.type,
            'details': self.details,
            'deadline': convert_from_utc(self.deadline).strftime("%d-%m-%Y %H:%M:%S") if self.deadline else None,
            'due_date': convert_from_utc(self.due_date).strftime("%d-%m-%Y") if self.due_date else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'subject': self.subject.min_to_dict() if self.subject else None,
            'author': self.author.min_to_dict() if self.author else None,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'urls': self.urls,
            'url': self.url,
            'links': self.links,
            'type': self.type,
            'department': self.department.min_to_dict() if self.department else None,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'year': self.year.min_to_dict() if self.year else None,
            'details': self.details,
            'deadline': convert_from_utc(self.deadline).strftime("%d-%m-%Y %H:%M:%S") if self.deadline else None,
            'due_date': convert_from_utc(self.due_date).strftime("%d-%m-%Y") if self.due_date else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'subject': self.subject.min_to_dict() if self.subject else None,
            'author': self.author.min_to_dict() if self.author else None,
        }
class Announcement(Base):
    __tablename__ = 'announcements'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(String(1000), nullable=True)
    date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True) # for datetime up to minutes
    urls: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)
    links: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)
    year_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('years.id', ondelete="CASCADE",
                                                                       name="fk_year_announcement"), nullable=True)
    year: Mapped[Optional['Year']] = relationship('Year', back_populates='announcements', cascade='save-update, merge')
    faculty_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('faculties.id', ondelete="CASCADE",
                                                                          name="fk_faculty_announcement"), nullable=True)
    faculty: Mapped[Optional['Faculty']] = relationship('Faculty', back_populates='announcements', cascade='save-update, merge')
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id', ondelete="CASCADE", name="fk_department_announcement"),
                                               nullable=True)
    department: Mapped['Department'] = relationship('Department', back_populates='announcements')
    details: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz))
    modified_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(utc_tz),
        onupdate=lambda: datetime.now(utc_tz)
    )
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_announcement", ondelete="SET NULL"),
                                           nullable=False)
    author: Mapped['User'] = relationship('User', back_populates='announcements')
    subject_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('subjects.id', ondelete="CASCADE", name="fk_subject_announcement"),
                                                    nullable=True)
    subject: Mapped['Subject'] = relationship('Subject', back_populates='announcements')

    def min_to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'date': convert_from_utc(self.date).isoformat() if self.date else None,
            'urls': self.urls,
            'links': self.links,
            'details': self.details,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
        }
    def user_to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'date': convert_from_utc(self.date).isoformat() if self.date else None,
            'urls': self.urls,
            'links': self.links,
            'details': self.details,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'author': self.author.min_to_dict() if self.author else None,
            'subject': self.subject.min_to_dict() if self.subject else None,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'date': convert_from_utc(self.date).isoformat() if self.date else None,
            'urls': self.urls,
            'links': self.links,
            'department': self.department.min_to_dict() if self.department else None,
            'year': self.year.min_to_dict() if self.year else None,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'details': self.details,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'author': self.author.min_to_dict() if self.author else None,
            'subject': self.subject.min_to_dict() if self.subject else None,
        }
    __table_args__ = (
        # Composite Indexes
        Index('idx_announcement_faculty_department_year_subject',
                 'faculty_id', 'department_id', 'year_id', 'subject_id'
        ),
    )
class Mark(Base):
    __tablename__ = 'marks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    url: Mapped[str] = mapped_column(String(100), nullable=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey('subjects.id', ondelete="CASCADE", name="fk_subject_mark"),
                                            nullable=True)
    subject: Mapped['Subject'] = relationship('Subject', back_populates='marks')
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_mark", ondelete="SET NULL"),
                                           nullable=True)
    author: Mapped['User'] = relationship('User', back_populates='marks', cascade='save-update, merge')
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    __table_args__ = (
        Index('idx_mark_subject', 'subject_id'),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'subject': self.subject.min_to_dict() if self.subject else None,
            'details': self.details,
            'author': self.author.min_to_dict() if self.author else None,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'details': self.details,
        }
class Token(Base):
    __tablename__ = 'tokens'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    expire_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    type: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 for google, 1 for User Signup Token, 2 for Stored
    # State Token
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (
        Index('idx_token', 'token', unique=True),
        Index('idx_token_expire_at', 'token', 'expire_at'),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'is_valid': self.is_valid,
            'expire_at': convert_from_utc(self.expire_at).strftime("%d-%m-%Y %H:%M:%S") if self.expire_at else None,
            'type': self.type,
            'details': self.details,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'is_valid': self.is_valid,
            'expire_at': convert_from_utc(self.expire_at).strftime("%d-%m-%Y %H:%M:%S") if self.expire_at else None,
            'type': self.type,
            'details': self.details,
        }
class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=True)  # e.g., 'task', 'announcement', 'event'
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz))
    users: Mapped[List['User']] = relationship('User', secondary='user_notifications', back_populates='notifications')
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'type': self.type,
            'parent_id': self.parent_id,
            'url': self.url,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'type': self.type,
            'parent_id': self.parent_id,
            'url': self.url,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def user_to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'type': self.type,
            'parent_id': self.parent_id,
            'url': self.url,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
class UserNotification(Base):
    __tablename__ = 'user_notifications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete="CASCADE",
                                                             name="fk_user_notification"), nullable=False)
    user: Mapped['User'] = relationship('User', backref='user_notifications_associations')

    notification_id: Mapped[int] = mapped_column(Integer, ForeignKey('notifications.id', ondelete="CASCADE",
                                                                     name="fk_notification_user_notification"),
                                                 nullable=False)
    notification: Mapped['Notification'] = relationship('Notification', backref='user_notifications_associations')
    seen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    __table_args__ = (
        Index('idx_user_notification_user_seen', 'user_id', 'seen'),
        Index('idx_user_notification_notification_seen', 'notification_id', 'seen'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'notification_id': self.notification_id,
            'seen': self.seen,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'notification_id': self.notification_id,
            'notification': self.notification.min_to_dict() if self.notification else None,
            'user': self.user.min_to_dict() if self.user else None,
            'seen': self.seen,
        }
class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    urls: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)
    start_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    end_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    location: Mapped[str] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz))
    modified_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(utc_tz),
        onupdate=lambda: datetime.now(utc_tz)
    )
    faculty_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('faculties.id', ondelete="CASCADE", name="fk_faculty_event"), nullable=True)
    faculty: Mapped[Optional['Faculty']] = relationship('Faculty', back_populates='events', cascade='save-update, merge')
    department_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('departments.id', ondelete="CASCADE", name="fk_department_event"), nullable=True)
    department: Mapped[Optional['Department']] = relationship('Department', back_populates='events', cascade='save-update, merge')
    year_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('years.id', ondelete="CASCADE", name="fk_year_event"), nullable=True)
    year: Mapped[Optional['Year']] = relationship('Year', back_populates='events', cascade='save-update, merge')
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_event", ondelete="SET NULL"),
                                           nullable=False)
    author: Mapped['User'] = relationship('User', back_populates='events')
    users: Mapped[List['User']] = relationship(
        'User',
        secondary='event_users',
        back_populates='going_events',
    )
    __table_args__ = (
        # Composite Indexes
        Index('idx_event_faculty_department_name', 'faculty_id', 'department_id', 'name'),
        Index('idx_event_faculty_department_year_name', 'faculty_id', 'department_id', 'year_id', 'name'),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'urls': self.urls,
            'start_time': convert_from_utc(self.start_time).strftime("%d-%m-%Y %H:%M:%S") if self.start_time else None,
            'end_time': convert_from_utc(self.end_time).strftime("%d-%m-%Y %H:%M:%S") if self.end_time else None,
            'location': self.location,
            'details': self.details,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'department': self.department.min_to_dict() if self.department else None,
            'year': self.year.min_to_dict() if self.year else None,
            'author': self.author.min_to_dict() if self.author else None,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'urls': self.urls,
            'start_time': convert_from_utc(self.start_time).strftime("%d-%m-%Y %H:%M:%S") if self.start_time else None,
            'end_time': convert_from_utc(self.end_time).strftime("%d-%m-%Y %H:%M:%S") if self.end_time else None,
            'location': self.location,
            'details': self.details,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
        }
class EventUser(Base):
    __tablename__ = 'event_users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete="CASCADE", name="fk_user_event_user"), nullable=False)
    user: Mapped['User'] = relationship('User', backref='event_users_associations')
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey('events.id', ondelete="CASCADE", name="fk_event_event_user"), nullable=False)
    event: Mapped['Event'] = relationship('Event', backref='event_users_associations')
    __table_args__ = (
        Index('idx_event_user_user', 'user_id'),
        Index('idx_event_user_event', 'event_id'),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_id': self.event_id,
            'user': self.user.min_to_dict() if self.user else None,
            'event': self.event.min_to_dict() if self.event else None,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_id': self.event_id,
        }
class Roadmap(Base):
    __tablename__ = 'roadmaps'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=True)
    urls: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)
    details: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz))
    modified_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(utc_tz),
        onupdate=lambda: datetime.now(utc_tz)
    )
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_roadmap", ondelete="SET NULL"),
                                           nullable=False)
    author: Mapped['User'] = relationship('User', back_populates='roadmaps')
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id', ondelete="CASCADE", name="fk_department_roadmap"),
                                               nullable=True)
    department: Mapped['Department'] = relationship('Department', back_populates='roadmaps')
    faculty_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('faculties.id', ondelete="CASCADE", name="fk_faculty_roadmap"), nullable=True)
    faculty: Mapped[Optional['Faculty']] = relationship('Faculty', back_populates='roadmaps', cascade='save-update, merge')
    year_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('years.id', ondelete="CASCADE", name="fk_year_roadmap"), nullable=True)
    year: Mapped[Optional['Year']] = relationship('Year', back_populates='roadmaps', cascade='save-update, merge')
    status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True) # True if the roadmap is accepted
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    type: Mapped[int] = mapped_column(Integer, nullable=True)  # e.g., 'advice', 'roadmap', 'coursemap'
    rating: Mapped[Integer] = mapped_column(Integer, default=0, nullable=True)
    courses: Mapped[List['RoadmapCourse']] = relationship(
        'RoadmapCourse',
        back_populates='roadmap',
        cascade='all, delete-orphan'
    )
    __table_args__ = (
        Index('idx_roadmap_author', 'author_id'),
        # Composite Indexes
        Index('idx_roadmap_status_faculty_department_name', 'status', 'faculty_id', 'department_id', 'name'),
        Index('idx_roadmap_status_faculty_department_year_name', 'status', 'faculty_id', 'department_id', 'year_id',
                     'name'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'urls': self.urls,
            'details': self.details,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'status': self.status,
            'description': self.description,
            'type': self.type,
            'rating': self.rating,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'urls': self.urls,
            'details': self.details,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'author': self.author.min_to_dict() if self.author else None,
            'department': self.department.min_to_dict() if self.department else None,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'year': self.year.min_to_dict() if self.year else None,
            'status': self.status,
            'description': self.description,
            'type': self.type,
            'rating': self.rating,
        }
    def full_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'urls': self.urls,
            'details': self.details,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'author': self.author.min_to_dict() if self.author else None,
            'department': self.department.min_to_dict() if self.department else None,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'year': self.year.min_to_dict() if self.year else None,
            'status': self.status,
            'description': self.description,
            'type': self.type,
            'rating': self.rating,
        }
class RoadmapCourse(Base):
    __tablename__ = 'roadmap_courses'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(Integer, ForeignKey('roadmaps.id', ondelete="CASCADE",
                                                                name="fk_roadmap_roadmap_course"), nullable=True)
    roadmap: Mapped['Roadmap'] = relationship('Roadmap', backref='roadmap_courses_associations')
    rank: Mapped[int] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(60), nullable=True)  # Name of the course
    content: Mapped[str] = mapped_column(String(200), nullable=True)  # Description of the course
    url: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    urls: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Year of the course
    term: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Term of the course
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    subject_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('subjects.id', ondelete="CASCADE",
                                                                          name="fk_subject_roadmap_course"), nullable=True)
    subject: Mapped[Optional['Subject']] = relationship('Subject', back_populates='roadmap_courses', cascade='save-update, merge')
    __table_args__ = (
        Index('idx_roadmap_course_roadmap', 'roadmap_id'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'rank': self.rank,
            'url': self.url,
            'urls': self.urls,
            'details': self.details,
            'year': self.year,
            'term': self.term,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'roadmap': self.roadmap.min_to_dict() if self.roadmap else None,
            'course': self.subject.min_to_dict() if self.subject else None,
            'rank': self.rank,
            'url': self.url,
            'urls': self.urls,
            'details': self.details,
            'year': self.year,
            'term': self.term,
        }
class Question(Base):
    __tablename__ = 'questions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(String(500), nullable=True)
    urls: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)
    subject_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('subjects.id', ondelete="CASCADE",
                                                                          name="fk_subject_question"), nullable=True)
    subject: Mapped[Optional['Subject']] = relationship('Subject', back_populates='questions', cascade='save-update, merge')
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_question", ondelete="SET NULL"),
                                           nullable=False)
    author: Mapped['User'] = relationship('User', back_populates='questions')
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    faculty_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('faculties.id', ondelete="CASCADE", name="fk_faculty_question"), nullable=True)
    faculty: Mapped[Optional['Faculty']] = relationship('Faculty', back_populates='questions', cascade='save-update, merge')
    department_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('departments.id', ondelete="CASCADE", name="fk_department_question"), nullable=True)
    department: Mapped[Optional['Department']] = relationship('Department', back_populates='questions', cascade='save-update, merge')
    year_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('years.id', ondelete="CASCADE", name="fk_year_question"), nullable=True)
    year: Mapped[Optional['Year']] = relationship('Year', back_populates='questions', cascade='save-update, merge')
    status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True) # True if the question is accepted
    rating: Mapped[Integer] = mapped_column(Integer, default=0, nullable=True) # Rating of the question
    __table_args__ = (
        Index('idx_question_author', 'author_id'),
        # Composite Indexes
        Index('idx_question_status_faculty_department_year_subject_title', 'status', 'faculty_id', 'department_id',
            'year_id',
                     'subject_id', 'title'),
        Index('idx_question_status_faculty_department_subject_title', 'status', 'faculty_id', 'department_id',
        'subject_id',
                     'title'),
        Index('idx_question_status_faculty_department_title', 'status', 'faculty_id', 'department_id', 'title'),
    )
    answers: Mapped[List['Answer']] = relationship(
        'Answer',
        back_populates='question',
        cascade='all, delete-orphan'
    )
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'urls': self.urls,
            'subject': self.subject.min_to_dict() if self.subject else None,
            'author': self.author.min_to_dict() if self.author else None,
            'details': self.details,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'department': self.department.min_to_dict() if self.department else None,
            'year': self.year.min_to_dict() if self.year else None,
            'status': self.status,
            'rating': self.rating,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'urls': self.urls,
            'details': self.details,
            'status': self.status,
            'rating': self.rating,
        }
class Answer(Base):
    __tablename__ = 'answers'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(String(500), nullable=True)
    urls: Mapped[List[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=True, default=list)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey('questions.id', ondelete="CASCADE", name="fk_question_answer"),
                                             nullable=False)
    question: Mapped['Question'] = relationship('Question', back_populates='answers', cascade='save-update, merge')
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_answer", ondelete="SET NULL"),
                                           nullable=False)
    author: Mapped['User'] = relationship('User', back_populates='answers')
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    __table_args__ = (
        Index('idx_answer_question', 'question_id'),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'urls': self.urls,
            'question': self.question.min_to_dict() if self.question else None,
            'author': self.author.min_to_dict() if self.author else None,
            'details': self.details,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'urls': self.urls,
            'details': self.details,
        }
class Timetable(Base):
    __tablename__ = 'time_tables'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    type: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 for days, 1 for plan
    days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # Number of days in the timetable 1-7
    time_specific: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)  # True if time specific ELse Duration
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz))
    modified_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(utc_tz),
        onupdate=lambda: datetime.now(utc_tz)
    )
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_time_table", ondelete="CASCADE"),
                                           nullable=True)
    author: Mapped['User'] = relationship('User', back_populates='timetables')
    year_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('years.id', ondelete="CASCADE", name="fk_year_time_table"), nullable=True)
    year: Mapped[Optional['Year']] = relationship('Year', back_populates='timetables', cascade='save-update, merge')
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id', ondelete="CASCADE", name="fk_department_time_table"),
                                                  nullable=True)
    department: Mapped['Department'] = relationship('Department', back_populates='timetables')
    faculty_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('faculties.id', ondelete="CASCADE", name="fk_faculty_time_table"), nullable=True)
    faculty: Mapped[Optional['Faculty']] = relationship('Faculty', back_populates='timetables', cascade='save-update, merge')
    public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)  # True if the timetable is public
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)  # True if the timetable is approved
    requested_table_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('time_tables.id',
                                                                                  ondelete="CASCADE",
                                                                                  name="fk_requested_table_time_table"), nullable=True)
    requested_table: Mapped[Optional['Timetable']] = relationship('Timetable', remote_side=[id], backref=backref(
        'requested_tables', cascade='all, delete-orphan'))
    forks: Mapped[int] = mapped_column(Integer, default=0, nullable=True)  # Number of forks of the timetable
    rating: Mapped[int] = mapped_column(Integer, default=0, nullable=True)  # Rating of the timetable
    table_tasks: Mapped[List['TableTask']] = relationship(
        'TableTask',
        back_populates='timetable',
        cascade='all, delete-orphan'
    )
    __table_args__ = (
        Index('idx_timetable_author', 'author_id'),
        # Composite Indexes
        Index('idx_timetable_approved_faculty_department_year_name', 'approved', 'faculty_id', 'department_id', 'year_id', 'name'),
        Index('idx_timetable_approved_faculty_department_name', 'approved', 'faculty_id', 'department_id', 'name'),
    )
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'days': self.days,
            'time_specific': self.time_specific,
            'details': self.details,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'author': self.author.min_to_dict() if self.author else None,
            'year': self.year.min_to_dict() if self.year else None,
            'department': self.department.min_to_dict() if self.department else None,
            'faculty': self.faculty.min_to_dict() if self.faculty else None,
            'public': self.public,
            'approved': self.approved,
            'requested_table': self.requested_table.min_to_dict() if self.requested_table else None,
            'forks': self.forks,
            'rating': self.rating,
        }
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'days': self.days,
            'time_specific': self.time_specific,
            'details': self.details,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
            'modified_at': convert_from_utc(self.modified_at).isoformat() if self.modified_at else None,
            'public': self.public,
            'approved': self.approved,
            'forks': self.forks,
            'rating': self.rating,
        }
class TableTask(Base):
    __tablename__ = 'table_tasks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    timetable_id: Mapped[int] = mapped_column(Integer, ForeignKey('time_tables.id', ondelete="CASCADE", name="fk_time_table_table_task"),
                                              nullable=True)
    timetable: Mapped['Timetable'] = relationship('Timetable', back_populates='table_tasks', cascade='save-update, merge')
    day: Mapped[int] = mapped_column(Integer, nullable=True)  # Day of the task 1-7
    rank: Mapped[int] = mapped_column(Integer, nullable=True)  # Rank of the task in the day of the timetable
    start_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)  # Start time of the task
    end_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)  # End time of the task
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Duration of the task in minutes
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)  # True if the task is done
    late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)  # True if the task is late
    __table_args__ = (
        Index('idx_table_task_timetable', 'timetable_id'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'day': self.day,
            'rank': self.rank,
            'start_time': convert_from_utc(self.start_time).strftime("%d-%m-%Y %H:%M:%S") if self.start_time else None,
            'end_time': convert_from_utc(self.end_time).strftime("%d-%m-%Y %H:%M:%S") if self.end_time else None,
            'duration': self.duration,
            'details': self.details,
            'done': self.done,
            'late': self.late,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'timetable': self.timetable.min_to_dict() if self.timetable else None,
            'day': self.day,
            'rank': self.rank,
            'start_time': convert_from_utc(self.start_time).strftime("%d-%m-%Y %H:%M:%S") if self.start_time else None,
            'end_time': convert_from_utc(self.end_time).strftime("%d-%m-%Y %H:%M:%S") if self.end_time else None,
            'duration': self.duration,
            'details': self.details,
            'done': self.done,
            'late': self.late,
        }
class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz))
    __table_args__ = (
        Index('idx_message_created_at', 'created_at'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'content': self.content,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'content': self.content,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
class Review(Base):
    __tablename__ = 'reviews'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(String(500), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=True)  # Rating from 1 to 5
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_review", ondelete="CASCADE"),
                                           nullable=False)
    author: Mapped['User'] = relationship('User', back_populates='reviews')
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz))
    __table_args__ = (
        # Composite Indexes
        Index('idx_review_created_at_author', 'created_at', 'author_id'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'rating': self.rating,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'rating': self.rating,
            'author': self.author.min_to_dict() if self.author else None,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
class RequestLimit(Base):
    __tablename__ = 'request_limits'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=True)  # IPv6 support
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_request_limit", ondelete="SET NULL"),
                                                   nullable=True)
    route: Mapped[str] = mapped_column(String(100), nullable=True)  # API endpoint or route
    status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)  # True if the request is passed
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz))
    user: Mapped[Optional['User']] = relationship('User', back_populates='request_limits')
    __table_args__ = (
        Index('idx_request_limit_ip_created_at', 'ip', 'created_at'),  # Index on IP and created_at
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'route': self.route,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'route': self.route,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
class Log(Base):
    __tablename__ = 'logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=True)  # IPv6 support
    level: Mapped[str] = mapped_column(String(20), nullable=True)  # e.g., 'info', 'error', 'warning'
    action: Mapped[str] = mapped_column(String(30), nullable=True)  # Action performed
    entity: Mapped[str] = mapped_column(String(30), nullable=True)  # Entity involved in the action
    route: Mapped[str] = mapped_column(String(100), nullable=True)  # API endpoint or route
    response_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # HTTP response code
    message: Mapped[str] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id', name="fk_user_log", ondelete="SET NULL"),
                                                   nullable=True)
    user: Mapped[Optional['User']] = relationship('User', back_populates='logs')
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: datetime.now(utc_tz))
    __table_args__ = (
        Index('idx_log_level', 'level'),
        Index('idx_log_created_at_level', 'created_at', 'level'),
        Index('idx_log_ip_created_at_level', 'ip', 'created_at', 'level'),
        Index('idx_log_created_at_type_action_entity_user_id_message_route', 'created_at', 'level', 'action', 'entity', 'user_id', 'message', 'route'),
    )
    def min_to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'level': self.level,
            'action': self.action,
            'entity': self.entity,
            'response_code': self.response_code,
            'message': self.message,
            'details': self.details,
            'route': self.route,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def many_to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'level': self.level,
            'action': self.action,
            'entity': self.entity,
            'response_code': self.response_code,
            'message': self.message,
            'details': self.details,
            'user': self.user.min_to_dict() if self.user else None,
            'route': self.route,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }
    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'level': self.level,
            'action': self.action,
            'entity': self.entity,
            'response_code': self.response_code,
            'message': self.message,
            'details': self.details,
            'user': self.user.to_dict() if self.user else None,
            'route': self.route,
            'created_at': convert_from_utc(self.created_at).isoformat() if self.created_at else None,
        }

