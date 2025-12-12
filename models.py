from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

# Connection table for many to many relationships between users and roles
user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True)
)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(150), nullable=True)
    last_name = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(255), nullable=True)

    profile_image = db.Column(db.String(255), nullable=True)

    username = db.Column(db.String(150), unique=True, nullable=False)
    hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Many to many, user has multiple roles: "user", "author", "admin", "superadmin"
    roles = db.relationship("Role", secondary=user_roles, backref="users") 

    def has_role(self, role_name):
        return any(r.name == role_name for r in self.roles)

    # Convenience property for displaying full name
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    thumbnail_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", backref="blog_posts")

    # Optional link to a dialogue thread
    dialogue_thread_id = db.Column(
        db.Integer,
        db.ForeignKey("dialogue_threads.id"),
        nullable=True
    )
    dialogue_thread = db.relationship(
        "DialogueThread",
        backref="blog_post",
        uselist=False
    )


class DialogueThread(db.Model):
    __tablename__ = "dialogue_threads"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    thumbnail_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Total score of up/downvotes on the thread itself
    score = db.Column(db.Integer, default=0, nullable=False)

    author = db.relationship("User", backref="dialogue_threads")
    comments = db.relationship("DialogueComment", backref="thread", cascade="all, delete-orphan", lazy="dynamic",)


class DialogueComment(db.Model):
    __tablename__ = "dialogue_comments"

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Score for sorting / displaying
    score = db.Column(db.Integer, default=0, nullable=False)

    # Links comment to thread
    thread_id = db.Column(db.Integer, db.ForeignKey("dialogue_threads.id"), nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", backref="dialogue_comments")

    # Parent/children for nested structure
    parent_id = db.Column(db.Integer, db.ForeignKey("dialogue_comments.id"), nullable=True)
    parent = db.relationship("DialogueComment", remote_side=[id], backref="children")


class DialogueCommentVote(db.Model):
    __tablename__ = "dialogue_comment_votes"

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="comment_votes")

    # Link to user and comment
    comment_id = db.Column(db.Integer, db.ForeignKey("dialogue_comments.id"), nullable=False)
    comment = db.relationship("DialogueComment", backref=db.backref("votes", cascade="all, delete-orphan"))

    # Ensure a user can only vote once per comment
    __table_args__ = (db.UniqueConstraint("user_id", "comment_id", name="uq_user_comment_vote"),)


class DialogueThreadVote(db.Model):
    __tablename__ = "dialogue_thread_votes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    thread_id = db.Column(db.Integer, db.ForeignKey("dialogue_threads.id"), nullable=False)
    value = db.Column(db.Integer, nullable=False) 

    # Link to user and thread
    user = db.relationship("User", backref="thread_votes")
    thread = db.relationship("DialogueThread", backref="votes")


class OpinionPoll(db.Model):
    __tablename__ = "opinion_polls"

    id = db.Column(db.Integer, primary_key=True)

    question = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    thumbnail_image = db.Column(db.String(255), nullable=True)

    # Link to dialogue thread
    dialogue_thread_id = db.Column(db.Integer, db.ForeignKey("dialogue_threads.id"))

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    expires_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(days=3),
    )

    yes_count = db.Column(db.Integer, nullable=False, default=0)
    no_count = db.Column(db.Integer, nullable=False, default=0)

    score = db.Column(db.Integer, nullable=False, default=0)

    author = db.relationship("User", backref="opinion_polls")
    dialogue_thread = db.relationship(
        "DialogueThread",
        backref="opinion_poll",
        uselist=False,
    )

    votes = db.relationship(
        "OpinionVote",
        backref="poll",
        cascade="all, delete-orphan",
    )

    @property
    def total_votes(self):
        """Return total number of votes."""
        return (self.yes_count or 0) + (self.no_count or 0)

    @property
    def is_expired(self):
        """Return True if the poll can no longer be voted on."""
        return datetime.utcnow() > (self.expires_at or self.created_at)


class OpinionVote(db.Model):
    __tablename__ = "opinion_votes"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey("opinion_polls.id"), nullable=False)

    value = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref="opinion_votes")