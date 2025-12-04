import os

from flask import Flask, flash, redirect, render_template, request, session, url_for, abort
from flask_session import Session
from helpers import apology, login_required, blogger_required, moderator_required
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import requests
from sqlalchemy import func, or_
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo


from models import * 

app = Flask(__name__)



# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False 
db.init_app(app)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)


# UPLOAD FOLDERS
#--------------------------------------------------------------------------------------------------------------
PROFILE_UPLOAD_FOLDER = os.path.join(app.static_folder, "profile_pics")
os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)

BLOG_THUMB_UPLOAD_FOLDER = os.path.join(app.static_folder, "blog_thumbs")
os.makedirs(BLOG_THUMB_UPLOAD_FOLDER, exist_ok=True)

DIALOGUE_THUMB_UPLOAD_FOLDER = os.path.join(app.static_folder, "dialogue_thumbs")
os.makedirs(DIALOGUE_THUMB_UPLOAD_FOLDER, exist_ok=True)


# NL DATETIME
#--------------------------------------------------------------------------------------------------------------
@app.template_filter("nl_datetime")
def nl_datetime(value, fmt="%d-%m-%Y %H:%M"):
    """Format a datetime to Dutch timezone and format"""

    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(ZoneInfo("Europe/Amsterdam")).strftime(fmt)


# MAKE USER AVALABLE IN ALL TEMPLATES
#--------------------------------------------------------------------------------------------------------------
@app.context_processor
def inject_user():
    """Make user available in all templates"""

    user_id = session.get("user_id")
    user = User.query.get(user_id) if user_id else None
    return {"user": user}


# ROOT ROUTE
#--------------------------------------------------------------------------------------------------------------
@app.route("/")
def root():
    """Redirect to home or index depending on login status"""

    if session.get("user_id"):
        return redirect("/index")
    return redirect("/home")


# REGISTER
#--------------------------------------------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Get values from inputfields
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirmation = request.form.get("confirmation", "").strip()

        # Query database for username and
        username = f"{first_name} {last_name}".strip()

        existing = User.query.filter_by(username=username).first()

        # Ensure first and last name were submitted
        if not first_name:
            return apology("must provide first name", 400)
        if not last_name:
            return apology("must provide last name", 400)
        
        # Ensure email was submitted
        if not email:
            return apology("must provide email", 400)
        
        # Ensure both password and confirmation fields are filled
        if not password and not confirmation:
            return apology("must provide password and confirm", 400)
        if not password:
            return apology("must provide password", 400)
        if not confirmation:
            return apology("must confirm password", 400)
        
        # Ensure password matches confirmation and Ensure unique username
        if password != confirmation and existing:
            return apology("username taken & passwords do not match", 400)
        if password != confirmation:
            return apology("passwords do not match", 400)
        if existing:
            return apology("username taken", 409)

        # Create user in table users
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username,
            hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()

        # Assign "user" role to new user
        role_user = Role.query.filter_by(name="user").first()
        if role_user:
            user.roles.append(role_user)
            db.session.commit()

        # Clear session and log in new user
        session.clear()
        session["user_id"] = user.id
        flash(f'{username} Registered!')
        return redirect("/index")

    return render_template("register.html")


# LOGIN
#--------------------------------------------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Define username and password 
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Query database for username
        user = User.query.filter_by(username=username).first()

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 400)

        # Ensure password was submitted
        if not password:
            return apology("must provide password", 400)

        # Ensure username exists and password is correct
        if user is None or not check_password_hash(user.hash, password):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = user.id

        # Redirect user to home page
        return redirect("/index")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    

# LOGOUT
#--------------------------------------------------------------------------------------------------------------
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/home")


# INDEX 
#--------------------------------------------------------------------------------------------------------------
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    """User profile page and update profile"""

    # Get current user
    user = User.query.get(session["user_id"])

    # Update profile if POST
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()

        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email:
            user.email = email

        file = request.files.get("profile_image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            path = os.path.join(PROFILE_UPLOAD_FOLDER, filename)
            file.save(path)
            user.profile_image = filename

        # Commit changes to database
        db.session.commit()
        flash("Profiel bijgewerkt.")
        return redirect(url_for("index"))

    return render_template("index.html")


# HOME
#--------------------------------------------------------------------------------------------------------------
@app.route("/home")
def home():
    """Home page"""

    # Get current user if logged in
    user_id = session.get("user_id")
    user = User.query.get(user_id) if user_id else None
    username = user.username if user else None

    return render_template("home.html", username=username)


# ADMIN PAGE
#--------------------------------------------------------------------------------------------------------------
@app.route("/admin")
@login_required
def admin():
    """Admin overview page of all users"""

    # Check if current user is admin/superadmin
    current = User.query.get(session["user_id"])
    if not current or (not current.has_role("admin") and not current.has_role("superadmin")):
        abort(403)

    # Search term from query string ?q=
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        if q.isdigit():
            # Search by username or ID
            query = query.filter(
                or_(
                    User.username.ilike(f"%{q}%"),
                    User.id == int(q)
                )
            )
        else:
            query = query.filter(User.username.ilike(f"%{q}%"))

    # Execute query and get all users
    users = query.order_by(User.created_at.desc()).all()

    return render_template("admin.html", users=users, search=q)


# ADMIN DETAIL PAGE
#--------------------------------------------------------------------------------------------------------------
@app.route("/admin/user/<int:user_id>", methods=["GET", "POST"])
@login_required
def admin_detail(user_id):
    """Admin overview detail page per user and ability to change roles"""

    # Check if current user is admin/superadmin only admins and superadmins can access the page
    current = User.query.get(session["user_id"])
    if not current or (not current.has_role("admin") and not current.has_role("superadmin")):
        return render_template("apology.html", top=403, bottom="Toegang geweigerd"), 403        

    # Get the user to be viewed/edited
    user = User.query.get_or_404(user_id)

    # superadmin may NOT be edited by admin
    if user.has_role("superadmin") and not current.has_role("superadmin"):
        flash("Je hebt geen rechten om een superadmin te bewerken.")
        return redirect(url_for("admin"))

    # Get all available roles
    roles = Role.query.all()

    # Handle role updates via POST
    if request.method == "POST":
        selected_roles = request.form.getlist("roles")

        # Admins may not give superadmin
        if "superadmin" in selected_roles and not current.has_role("superadmin"):
            flash("Alleen een superadmin mag superadmin rechten toekennen.")
            return redirect(url_for("admin_detail", user_id=user.id))

        # Reset roles
        user.roles = []

        # Add new roles
        for role_name in selected_roles:
            role = Role.query.filter_by(name=role_name).first()
            if role:
                user.roles.append(role)

        # Commit changes to database
        db.session.commit()
        flash("Gebruikersrollen bijgewerkt.")
        return redirect(url_for("admin_detail", user_id=user.id))

    return render_template("admin_detail.html", viewed_user=user, roles=roles)


# BLOG PAGE
#--------------------------------------------------------------------------------------------------------------
@app.route("/blog")
def blog():
    """Overview of blog posts and search area"""

    # Searchterm from query string
    q = request.args.get("q", "").strip()

    # Base query
    query = BlogPost.query

    if q:
        # Add search filters
        query = (
            BlogPost.query
            .join(User)
            .filter(
                or_(
                    BlogPost.title.ilike(f"%{q}%"),
                    BlogPost.content.ilike(f"%{q}%"),
                    User.username.ilike(f"%{q}%"),
                    User.first_name.ilike(f"%{q}%"),
                    User.last_name.ilike(f"%{q}%"),
                )
            )
        )

    # Get all posts ordered by creation date descending
    posts = query.order_by(BlogPost.created_at.desc()).all()

    # Collect thread stats for each post
    thread_stats = {}
    thread_ids = [p.dialogue_thread_id for p in posts if p.dialogue_thread_id]

    # Bulk query 
    if thread_ids:
        threads = DialogueThread.query.filter(
            DialogueThread.id.in_(thread_ids)
        ).all()
        threads_by_id = {t.id: t for t in threads}

        # Gather stats
        for p in posts:
            if p.dialogue_thread_id and p.dialogue_thread_id in threads_by_id:
                t = threads_by_id[p.dialogue_thread_id]

                # Get thread score (default to 0 if None)
                score = t.score or 0

                # Number of comments in the dialogue
                try:
                    comment_count = t.comments.count()
                except TypeError:
                    comment_count = len(t.comments)

                # Store stats
                thread_stats[p.id] = {
                    "thread_id": t.id,
                    "comment_count": comment_count,
                    "score": score,
                }

    return render_template(
        "blog.html",
        posts=posts,
        search_query=q,
        thread_stats=thread_stats,
    )


# NEW BLOG POST
#--------------------------------------------------------------------------------------------------------------
@app.route("/blog/new", methods=["GET", "POST"])
@login_required
def new_blog():
    """Create a new blog post"""

    # Check if current user is author
    user_id = session.get("user_id")
    current_user = User.query.get(user_id) if user_id else None

    # Only authors can create blog posts
    if current_user is None or not current_user.has_role("author"):
        abort(403)

    # Handle form submission
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        errors = []
        if not title:
            errors.append("Titel is verplicht.")
        if not content:
            errors.append("Inhoud is verplicht.")

        # Process thumbnail
        thumb_file = request.files.get("thumbnail_image")
        thumb_filename = None
        if thumb_file and thumb_file.filename:
            filename = secure_filename(thumb_file.filename)
            path = os.path.join(BLOG_THUMB_UPLOAD_FOLDER, filename)
            thumb_file.save(path)
            thumb_filename = filename

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("new_blog.html", title=title, content=content)

        # Create and save new blog post
        post = BlogPost(
            title=title,
            content=content,
            author_id=current_user.id,
            thumbnail_image=thumb_filename
        )
        db.session.add(post)
        db.session.commit()

        flash("Blogpost succesvol aangemaakt.", "success")
        return redirect(url_for("blog"))

    return render_template("new_blog.html")


# UPLOAD IMAGE
#--------------------------------------------------------------------------------------------------------------
@app.route("/upload-image", methods=["POST"])
@login_required
def upload_image():
    """Handle image upload for blog editor"""

    # Get the uploaded file
    file = request.files.get("file")
    if not file:
        abort(400)

    # Save the file to the uploads directory
    filename = secure_filename(file.filename)
    upload_dir = os.path.join(app.static_folder, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # Save file
    path = os.path.join(upload_dir, filename)
    file.save(path)

    # Return the file URL for TinyMCE
    file_url = url_for("static", filename=f"uploads/{filename}", _external=False)
    return {"location": file_url}


# VIEW BLOG POST
#--------------------------------------------------------------------------------------------------------------
@app.route("/blog/<int:post_id>")
def view_blog(post_id):
    """View a single blog post"""

    # Get the blog post
    post = BlogPost.query.get_or_404(post_id)

    # Get dialogue thread info if the blog has been converted to a dialogue
    thread = None
    comment_count = 0
    thread_score = 0
    if post.dialogue_thread_id:
        thread = DialogueThread.query.get(post.dialogue_thread_id)
        if thread:
            comment_count = thread.comments.count()
            thread_score = thread.score or 0

    # Sidebar: recent blog posts
    sidebar_posts = (
        BlogPost.query
        .filter(BlogPost.id != post.id)
        .order_by(BlogPost.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "view_blog.html",
        post=post,
        thread=thread,
        comment_count=comment_count,
        thread_score=thread_score,
        sidebar_posts=sidebar_posts,
    )


# EDIT BLOG POST
#--------------------------------------------------------------------------------------------------------------
@app.route("/blog/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_blog(post_id):
    """Edit a blog post"""

    # Get the blog post
    post = BlogPost.query.get_or_404(post_id)

    # Get the current user from the session
    user_id = session.get("user_id")
    current_user = User.query.get(user_id) if user_id else None

    # Check if user is logged in
    if current_user is None:
        abort(403)

    # Only the author of the post or an admin/superadmin can edit
    if current_user.id != post.author_id and not (
        current_user.has_role("admin") or current_user.has_role("superadmin")
    ):
        abort(403)

    # Handle form submission
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        # Validate input
        if not title or not content:
            flash("Titel en inhoud zijn verplicht.", "danger")
            return render_template("edit_blog.html", post=post)

        post.title = title
        post.content = content

        # Optionally upload a new thumbnail
        file = request.files.get("thumbnail_image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            path = os.path.join(BLOG_THUMB_UPLOAD_FOLDER, filename)
            file.save(path)
            post.thumbnail_image = filename

        db.session.commit()

        flash("Blogpost bijgewerkt.", "success")
        return redirect(url_for("view_blog", post_id=post.id))

    return render_template("edit_blog.html", post=post)


# DELETE BLOG POST
#--------------------------------------------------------------------------------------------------------------
@app.route("/blog/delete/<int:post_id>")
@moderator_required
def delete_blog(post_id):
    """Delete a blog post (only for authors, admins and superadmins)"""

    # Bulk query
    post = BlogPost.query.get_or_404(post_id)

    # Delete the blog post
    db.session.delete(post)
    db.session.commit()
    flash("Blogpost verwijderd.")
    return redirect(url_for("blog"))


# MAKE DIALOGUE FROM BLOG POST
#--------------------------------------------------------------------------------------------------------------
@app.route("/blog/<int:post_id>/make-dialogue", methods=["POST"])
@login_required
def make_dialogue_from_blog(post_id):
    """Convert a blog post into a dialogue thread"""

    # Get the blog post
    post = BlogPost.query.get_or_404(post_id)

    # Get current user
    current = User.query.get(session["user_id"])

    # Only the author of the post or an admin/superadmin can convert
    if post.dialogue_thread_id:
        return redirect(url_for("view_thread", thread_id=post.dialogue_thread_id))

    # Copy thumbnail from blog to dialogue
    thumb_filename = None
    if post.thumbnail_image:
        thumb_filename = post.thumbnail_image
        src = os.path.join(BLOG_THUMB_UPLOAD_FOLDER, thumb_filename)
        dst = os.path.join(DIALOGUE_THUMB_UPLOAD_FOLDER, thumb_filename)
        try:
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
        except Exception:
            thumb_filename = None

    # Create dialogue thread
    thread = DialogueThread(
        title=post.title[:255],          
        body=post.content,              
        author_id=current.id,           
        thumbnail_image=thumb_filename
    )
    db.session.add(thread)
    db.session.flush() 

    # Link blog post to dialogue thread
    post.dialogue_thread_id = thread.id

    # Commit changes to the database
    db.session.commit()

    flash("Dialoog aangemaakt voor deze blog.", "success")
    return redirect(url_for("view_thread", thread_id=thread.id))


# Dialogue constant
MAX_TITLE_LENGTH = 255

# DIALOOG PAGE
#--------------------------------------------------------------------------------------------------------------
@app.route("/dialoog", methods=["GET"])
def dialoog():
    """overview of dialogue threads and search area"""

    # Get current user
    user_id = session.get("user_id")
    current_user = User.query.get(user_id) if user_id else None

    # search term from query string
    q = request.args.get("q", "").strip()

    # base query
    query = DialogueThread.query.join(User)
    if q:
        query = query.filter(
            or_(
                DialogueThread.title.ilike(f"%{q}%"),
                DialogueThread.body.ilike(f"%{q}%"),
                User.username.ilike(f"%{q}%"),
                User.first_name.ilike(f"%{q}%"),
                User.last_name.ilike(f"%{q}%"),
            )
        )

    # get all threads ordered by score desc, then creation date desc
    threads = query.order_by(
        DialogueThread.score.desc(),
        DialogueThread.created_at.desc()
    ).all()

    return render_template("dialoog.html", threads=threads, search_query=q)


# NEW DIALOOG THREAD
#--------------------------------------------------------------------------------------------------------------
@app.route("/dialoog/new", methods=["GET", "POST"])
@login_required
def new_dialoog():
    """Create a new dialogue thread"""

    # Get current user
    user_id = session.get("user_id")
    current_user = User.query.get(user_id) if user_id else None

    # Check if user is logged in
    if current_user is None:
        abort(403)

    # Handle form submission
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()

        # Validate input
        errors = []
        if not title:
            errors.append("Titel is verplicht.")

        # Process thumbnail (image or video)
        thumb_file = request.files.get("thumbnail")
        thumb_filename = None
        if thumb_file and thumb_file.filename:
            filename = secure_filename(thumb_file.filename)
            path = os.path.join(DIALOGUE_THUMB_UPLOAD_FOLDER, filename)
            thumb_file.save(path)
            thumb_filename = filename

        # Show errors if any
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "new_dialoog.html",
                title=title,
                body=body,
            )

        # Create and save new dialogue thread
        thread = DialogueThread(
            title=title,
            body=body or None,
            author_id=current_user.id,
            thumbnail_image=thumb_filename,
        )
        db.session.add(thread)
        db.session.commit()

        flash("Nieuwe dialoog gestart.", "success")
        return redirect(url_for("view_thread", thread_id=thread.id))

    # GET
    return render_template("new_dialoog.html")




# VIEW DIALOOG THREAD
#--------------------------------------------------------------------------------------------------------------
@app.route("/dialoog/<int:thread_id>", methods=["GET", "POST"])
def view_thread(thread_id):
    """View a single dialogue thread and its comments, handle new comments"""

    # Get the dialogue thread
    thread = DialogueThread.query.get_or_404(thread_id)

    # Get current user
    user_id = session.get("user_id")
    current_user = User.query.get(user_id) if user_id else None

    # Handle new comment submission
    if request.method == "POST":
        if current_user is None:
            flash("Log in om te reageren.", "warning")
            return redirect(url_for("login"))

        body = request.form.get("body", "").strip()
        parent_id_raw = request.form.get("parent_id", "").strip()
        parent_id = int(parent_id_raw) if parent_id_raw.isdigit() else None

        if not body:
            flash("Reactie mag niet leeg zijn.", "danger")
        else:
            comment = DialogueComment(
                body=body,
                author_id=current_user.id,
                thread_id=thread.id,
                parent_id=parent_id,
            )
            db.session.add(comment)
            db.session.commit()
            flash("Reactie geplaatst.", "success")
            return redirect(
                url_for(
                    "view_thread",
                    thread_id=thread.id,
                    comment="posted",
                    _anchor="comments",
                )
            )

    # Retrieve comments
    comments = (
        DialogueComment.query
        .filter_by(thread_id=thread.id)
        .order_by(DialogueComment.score.desc(), DialogueComment.created_at.asc())
        .all()
    )

    # Build the top-level comment tree 
    tree = []
    by_id = {c.id: c for c in comments}
    for c in comments:
        if c.parent_id and c.parent_id in by_id:
            continue
        tree.append(c)

    # Get sidebar threads
    sidebar_threads = (
        DialogueThread.query
        .filter(DialogueThread.id != thread.id)
        .order_by(DialogueThread.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "dialoog_thread.html",
        thread=thread,
        root_comments=tree,
        all_comments=comments,
        user=current_user,
        sidebar_threads=sidebar_threads,
    )


# EDIT THREAD
#--------------------------------------------------------------------------------------------------------------
@app.route("/dialoog/thread/<int:thread_id>/edit", methods=["POST"])
@login_required
def edit_thread(thread_id):
    """Edit a dialogue thread (only starter, admin or superadmin)"""

    # Get the dialogue thread
    thread = DialogueThread.query.get_or_404(thread_id)
    current = User.query.get(session["user_id"])

    # Only starter, admin or superadmin
    if not (
        current.id == thread.author_id
        or current.has_role("admin")
        or current.has_role("superadmin")
    ):
        abort(403)

    # Get form data
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()

    # Validate input
    if not title:
        flash("Titel mag niet leeg zijn.", "danger")
        return redirect(url_for("view_thread", thread_id=thread.id))

    # Update thread
    thread.title = title
    thread.body = body or None

    # Optionally upload a new thumbnail
    file = request.files.get("thumbnail")
    if file and file.filename:
        filename = secure_filename(file.filename)
        path = os.path.join(DIALOGUE_THUMB_UPLOAD_FOLDER, filename)
        file.save(path)
        thread.thumbnail_image = filename

    db.session.commit()
    flash("Dialoog bijgewerkt.", "success")
    return redirect(url_for("view_thread", thread_id=thread.id))


# DELETE THREAD
#--------------------------------------------------------------------------------------------------------------
@app.route("/dialoog/thread/<int:thread_id>/delete", methods=["POST"])
@login_required
def delete_thread(thread_id):
    """Delete a dialogue thread (only admin / superadmin)"""

    thread = DialogueThread.query.get_or_404(thread_id)
    current = User.query.get(session["user_id"])

    if not (current.has_role("admin") or current.has_role("superadmin")):
        abort(403)

    # 0) delete all thread votes (to avoid FK error)
    DialogueThreadVote.query.filter_by(thread_id=thread.id).delete(
        synchronize_session=False
    )

    # 1) delete all votes on comments of this thread
    for comment in thread.comments:
        DialogueCommentVote.query.filter_by(comment_id=comment.id).delete(
            synchronize_session=False
        )

    # 2) remove any linkage from BlogPost
    BlogPost.query.filter_by(dialogue_thread_id=thread.id).update(
        {BlogPost.dialogue_thread_id: None},
        synchronize_session=False,
    )

    # 3) then delete the thread itself (and via cascade the comments)
    db.session.delete(thread)
    db.session.commit()

    flash("Dialoog verwijderd.", "success")
    return redirect(url_for("dialoog"))


# VOTE THREAD
#--------------------------------------------------------------------------------------------------------------
@app.route("/dialoog/thread/<int:thread_id>/vote", methods=["POST"])
@login_required
def vote_thread(thread_id):
    """Upvote/downvote a thread (the dialogue itself)"""

    # Get the dialogue thread
    thread = DialogueThread.query.get_or_404(thread_id)
    current_user = User.query.get(session["user_id"])

    # Get vote direction
    direction = request.form.get("direction")
    if direction not in ("up", "down"):
        abort(400)

    # Determine vote value
    value = 1 if direction == "up" else -1

    # Check if user has already voted
    existing = DialogueThreadVote.query.filter_by(
        user_id=current_user.id,
        thread_id=thread.id
    ).first()

    # Update vote if exists
    if existing:
        if existing.value == value:
            # same vote again will remove vote
            thread.score -= existing.value
            db.session.delete(existing)
        else:
            # reverse vote
            thread.score -= existing.value
            existing.value = value
            thread.score += value
    
    # New vote
    else:
        vote = DialogueThreadVote(
            user_id=current_user.id,
            thread_id=thread.id,
            value=value
        )
        db.session.add(vote)
        thread.score += value

    db.session.commit()

    return redirect(request.referrer or url_for("dialoog"))


# VOTE COMMENT
#--------------------------------------------------------------------------------------------------------------
@app.route("/dialoog/comment/<int:comment_id>/vote", methods=["POST"])
@login_required
def vote_comment(comment_id):
    """Upvote / downvote a comment"""

    # Get the comment
    comment = DialogueComment.query.get_or_404(comment_id)

    # Get current user
    user_id = session.get("user_id")
    current_user = User.query.get(user_id)

    # get vote direction
    direction = request.form.get("direction")
    if direction not in ("up", "down"):
        abort(400)

    # Determine vote value
    value = 1 if direction == "up" else -1

    # Check if user has already voted
    existing = DialogueCommentVote.query.filter_by(
        user_id=current_user.id,
        comment_id=comment.id
    ).first()

    if existing:
        if existing.value == value:
            # Same vote again will remove vote
            comment.score -= existing.value
            db.session.delete(existing)
        else:
            # Reverse vote
            comment.score -= existing.value
            existing.value = value
            comment.score += value
    else:
        # New vote
        vote = DialogueCommentVote(
            user_id=current_user.id,
            comment_id=comment.id,
            value=value,
        )
        db.session.add(vote)
        comment.score += value

    db.session.commit()

    return redirect(
        url_for(
            "view_thread",
            thread_id=comment.thread_id,
            _anchor=f"comment-{comment.id}"
        )
    )


# DELETE COMMENT
#--------------------------------------------------------------------------------------------------------------
@app.route("/dialoog/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    """Delete a comment (owner or admin/superadmin)"""
    
    # Get the comment
    comment = DialogueComment.query.get_or_404(comment_id)
    current = User.query.get(session["user_id"])

    # only owner or admin/superadmin
    if not (
        current.id == comment.author_id
        or current.has_role("admin")
        or current.has_role("superadmin")
    ):
        abort(403)

    # Get the thread ID before deleting the comment
    thread_id = comment.thread_id
    db.session.delete(comment)
    db.session.commit()
    flash("Reactie verwijderd.", "success")
    return redirect(url_for("view_thread", thread_id=thread_id))


# EDIT COMMENT
#--------------------------------------------------------------------------------------------------------------
@app.route("/dialoog/comment/<int:comment_id>/edit", methods=["POST"])
@login_required
def edit_comment(comment_id):
    """Edit a comment (owner or admin/superadmin)"""

    # Get the comment
    comment = DialogueComment.query.get_or_404(comment_id)
    current = User.query.get(session["user_id"])

    # only owner or admin/superadmin
    if not (
        current.id == comment.author_id
        or current.has_role("admin")
        or current.has_role("superadmin")
    ):
        abort(403)

    # Get form data
    body = request.form.get("body", "").strip()
    if not body:
        flash("Reactie mag niet leeg zijn.", "danger")
    else:
        comment.body = body
        db.session.commit()
        flash("Reactie bijgewerkt.", "success")

    return redirect(
        url_for(
            "view_thread",
            thread_id=comment.thread_id,
            _anchor=f"comment-{comment.id}"
        )
    )

# OPINIE PAGE
#--------------------------------------------------------------------------------------------------------------
@app.route("/opinie")
def opinie():
    return render_template("apology.html", top=200, bottom="Opiniepagina in de maak")

# CONTACT PAGE
#--------------------------------------------------------------------------------------------------------------
@app.route("/contact")
def contact():
    return render_template("apology.html", top=200, bottom="Contactpagina in de maak")


# Create database tables and default roles if they don't exist
# ----------------------------------------------------------
with app.app_context():
    db.create_all()

    # Roles that can be assigned
    default_roles = ["user", "author", "admin", "superadmin"]

    for r in default_roles:
        if not Role.query.filter_by(name=r).first():
            db.session.add(Role(name=r))
    db.session.commit()
