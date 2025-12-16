import os

from flask import Flask, flash, redirect, render_template, request, session, url_for, abort
from flask_session import Session
from helpers import apology, login_required, blogger_required, moderator_required
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import requests
from sqlalchemy import func, or_
import shutil
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from llm_guard import guard_text, guard_image
import tempfile




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

OPINION_THUMB_UPLOAD_FOLDER = os.path.join(app.static_folder, "opinion_thumbs")
os.makedirs(OPINION_THUMB_UPLOAD_FOLDER, exist_ok=True)


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
    """User profile page and update profile (incl. optional password change)"""

    # Get current user
    user = User.query.get(session["user_id"])


    # Handle profile update via POST
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()

        current_password = (request.form.get("current_password") or "").strip()
        new_password = (request.form.get("new_password") or "").strip()
        confirmation = (request.form.get("confirmation") or "").strip()

        
        # Check if any password fields are filled
        pw_fields_filled = any([current_password, new_password, confirmation])

        # If any password fields are filled, all must be filled and validated
        if pw_fields_filled:
            if not current_password or not new_password or not confirmation:
                flash("Vul alle wachtwoordvelden in.")
                return redirect(url_for("index"))

            # Check current password
            if not check_password_hash(user.hash, current_password):
                flash("Huidig wachtwoord is onjuist.")
                return redirect(url_for("index"))

            # Check new password matches confirmation
            if new_password != confirmation:
                flash("Nieuwe wachtwoorden komen niet overeen.")
                return redirect(url_for("index"))

            # New password must be different from current
            if check_password_hash(user.hash, new_password):
                flash("Het nieuwe wachtwoord moet anders zijn dan het huidige.")
                return redirect(url_for("index"))

            # Minimum length for new password
            if len(new_password) < 3:
                flash("Het nieuwe wachtwoord moet minstens 8 tekens lang zijn.")
                return redirect(url_for("index"))
            

        # Update profile information
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


        # Update password
        if pw_fields_filled:
            user.hash = generate_password_hash(new_password)

        # Commit everything at once
        db.session.commit()

        if pw_fields_filled:
            flash("Profiel en wachtwoord bijgewerkt.")
        else:
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

        pending_blocks = []
        should_block = False

        # Process thumbnail
        thumb_file = request.files.get("thumbnail_image")
        thumb_filename = None
        if thumb_file and thumb_file.filename:
            import tempfile

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(thumb_file.filename)[1] or ".jpg"
            ) as tmp:
                tmp_path = tmp.name
                thumb_file.save(tmp_path)

            decision_img = guard_image(tmp_path, context="blog_thumbnail")

            try:
                os.remove(tmp_path)
            except Exception:
                pass

            if decision_img.get("action") in ("block", "review"):
                cats = decision_img.get("categories", {}) or {}

                if cats.get("nsfw"):
                    pending_blocks.append(
                        "Post tegengehouden: Mogelijk seksueel expliciete afbeelding gedetecteerd"
                    )
                    should_block = True

                if cats.get("gore"):
                    pending_blocks.append(
                        "Post tegengehouden: Mogelijk gewelddadige/bloederige afbeelding gedetecteerd"
                    )
                    should_block = True

                if cats.get("offensive_symbols"):
                    pending_blocks.append(
                        "Post tegengehouden: Mogelijk aanstootgevende symbolen gedetecteerd"
                    )
                    should_block = True

                if not pending_blocks:
                    pending_blocks.append(
                        "Post tegengehouden: Ongewenste afbeelding gedetecteerd."
                    )
                    should_block = True

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("new_blog.html", title=title, content=content)
        
        # text Content moderation via LLM guard
        decision = guard_text(title=title, body=content, context="blog_post")
        if decision.get("action") in ("block", "review"):
            found = decision.get("found", {})
            prof = found.get("profanity_terms", []) or []
            sus_urls = found.get("suspicious_urls", []) or []

            if prof:
                pending_blocks.append(
                    "Post tegengehouden: Mogelijke scheldwoorden gedetecteerd: "
                    + ", ".join(prof[:10])
                )
                should_block = True

            if sus_urls:
                pending_blocks.append(
                    "Post tegengehouden: Mogelijk schadelijke link gedetecteerd: "
                    + ", ".join(sus_urls[:5])
                )
                should_block = True

            if not prof and not sus_urls:
                pending_blocks.append("Post tegengehouden: Ongewenste inhoud gedetecteerd.")
                should_block = True

        if should_block:
            for msg in pending_blocks:
                flash(msg, "danger")
            return render_template("new_blog.html", title=title, content=content)

        if thumb_file and thumb_file.filename:
            thumb_file.stream.seek(0)
            filename = secure_filename(thumb_file.filename)
            path = os.path.join(BLOG_THUMB_UPLOAD_FOLDER, filename)
            thumb_file.save(path)
            thumb_filename = filename
        
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

    # Get vote direction from form
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


# OPINION POLLS PAGE
# --------------------------------------------------------------------------------------------------
@app.route("/opinie", methods=["GET"])
def opinie():
    """Show all opinion polls, ordered by popularity, plus user vote info."""

    # Get all polls ordered by total votes desc, then creation date desc
    polls = (
        OpinionPoll.query
        .order_by((OpinionPoll.yes_count + OpinionPoll.no_count).desc(),
                  OpinionPoll.created_at.desc())
        .all()
    )

    # Current user (may be None)
    user_id = session.get("user_id")
    current_user = User.query.get(user_id) if user_id else None

    # Get user's votes
    user_votes = {}
    if current_user:
        votes = OpinionVote.query.filter_by(user_id=current_user.id).all()
        for v in votes:
            user_votes[v.poll_id] = "yes" if v.value == 1 else "no"

    # Render template
    return render_template(
        "opinie.html",
        polls=polls,
        user=current_user,
        user_votes=user_votes,
        now_utc=datetime.utcnow(),
    )


# CREATE NEW OPINION POLL
# --------------------------------------------------------------------------------------------------
@app.route("/opinie/new", methods=["POST"])
@login_required
def new_opinie():
    """Create a new opinion poll with default duration of 3 days."""

    # Get current user
    current_user = User.query.get(session["user_id"])

    # Get and validate form data
    question = (request.form.get("question") or "").strip()
    description = (request.form.get("description") or "").strip()

    # Backend length limits to keep cards compact
    max_question_len = 80
    max_description_len = 220

    if not question:
        flash("Vraag is verplicht.", "danger")
        return redirect(url_for("opinie"))
    if not description:
        flash("Toelichting is verplicht.", "danger")
        return redirect(url_for("opinie"))
    if len(question) > max_question_len:
        flash(f"Vraag mag maximaal {max_question_len} tekens bevatten.", "danger")
        return redirect(url_for("opinie"))
    if len(description) > max_description_len:
        flash(f"Toelichting mag maximaal {max_description_len} tekens bevatten.", "danger")
        return redirect(url_for("opinie"))

    # Thumbnail is required
    thumb_file = request.files.get("thumbnail")
    if not thumb_file or not thumb_file.filename:
        flash("Thumbnail is verplicht.", "danger")
        return redirect(url_for("opinie"))

    filename = secure_filename(thumb_file.filename)
    path = os.path.join(OPINION_THUMB_UPLOAD_FOLDER, filename)
    thumb_file.save(path)
    thumb_filename = filename

    # Default duration 3 days
    expires_at = datetime.utcnow() + timedelta(days=3)

    poll = OpinionPoll(
        question=question,
        description=description,
        author_id=current_user.id,
        thumbnail_image=thumb_filename,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        yes_count=0,
        no_count=0,
        score=0,
    )
    db.session.add(poll)
    db.session.commit()

    flash("Nieuwe peiling gestart.", "success")
    return redirect(url_for("opinie"))


# VOTE ON OPINION POLL
# --------------------------------------------------------------------------------------------------
@app.route("/opinie/<int:poll_id>/vote", methods=["POST"])
@login_required
def vote_opinie(poll_id):
    """Vote yes/no on an opinion poll."""

    # Get the poll and current user
    poll = OpinionPoll.query.get_or_404(poll_id)
    current_user = User.query.get(session["user_id"])

    # Use model property or datetime comparison for expiry
    if poll.is_expired:
        flash("Deze peiling is gesloten; stemmen is niet meer mogelijk.", "warning")
        return redirect(url_for("opinie"))

    choice = request.form.get("choice")
    if choice not in ("yes", "no"):
        abort(400)

    # Map to +1 / -1
    value = 1 if choice == "yes" else -1

    # Check for existing vote
    existing = OpinionVote.query.filter_by(
        user_id=current_user.id,
        poll_id=poll.id,
    ).first()

    if existing:
        # Same vote again doesn't lead to change
        if existing.value == value:
            flash("Je hebt al zo gestemd op deze peiling.", "info")
            return redirect(url_for("opinie"))

        # Remove previous counts
        if existing.value == 1:
            poll.yes_count = max(0, (poll.yes_count or 0) - 1)
        else:
            poll.no_count = max(0, (poll.no_count or 0) - 1)

        existing.value = value
    else:
        # New vote record
        existing = OpinionVote(
            user_id=current_user.id,
            poll_id=poll.id,
            value=value,
        )
        db.session.add(existing)

    # Update counters and score
    if value == 1:
        poll.yes_count = (poll.yes_count or 0) + 1
    else:
        poll.no_count = (poll.no_count or 0) + 1

    poll.score = (poll.yes_count or 0) - (poll.no_count or 0)

    db.session.commit()
    flash("Stem geregistreerd.", "success")
    return redirect(url_for("opinie"))


# UPDATE POLL DURATION (ADMIN / SUPERADMIN)
# --------------------------------------------------------------------------------------------------
@app.route("/opinie/<int:poll_id>/update-time", methods=["POST"])
@login_required
def update_poll_time(poll_id):
    """Update the remaining time of a poll (admin/superadmin only)."""

    poll = OpinionPoll.query.get_or_404(poll_id)
    current_user = User.query.get(session["user_id"])

    # Only admins and superadmins may change timing for any poll
    if not current_user or not (
        current_user.has_role("admin") or current_user.has_role("superadmin")
    ):
        abort(403)

    # Parse duration value and unit
    raw_value = (request.form.get("duration_value") or "").strip()
    unit = (request.form.get("duration_unit") or "seconds").strip()

    try:
        value = int(raw_value)
    except ValueError:
        flash("Voer een geldig getal in voor de duur.", "danger")
        return redirect(url_for("opinie"))

    if value <= 0:
        flash("Duur moet groter zijn dan 0.", "danger")
        return redirect(url_for("opinie"))

    # Convert to seconds
    factor_map = {
        "seconds": 1,
        "minutes": 60,
        "hours": 3600,
        "days": 86400,
    }
    factor = factor_map.get(unit, 1)
    total_seconds = value * factor

    # polltime between 10 seconds and 30 days
    min_seconds = 10
    max_seconds = 30 * 24 * 3600
    if total_seconds < min_seconds or total_seconds > max_seconds:
        flash("Duur moet tussen 10 seconden en 30 dagen liggen.", "danger")
        return redirect(url_for("opinie"))

    # Update expiry time
    poll.expires_at = datetime.utcnow() + timedelta(seconds=total_seconds)
    db.session.commit()

    flash("Peilingtijd bijgewerkt.", "success")
    return redirect(url_for("opinie"))


# DELETE OPINION POLL
# --------------------------------------------------------------------------------------------------
@app.route("/opinie/<int:poll_id>/delete", methods=["POST"])
@login_required
def delete_opinie(poll_id):
    """Delete an opinion poll (only creator, admin or superadmin)."""

    # Get the poll and current user
    poll = OpinionPoll.query.get_or_404(poll_id)
    current_user = User.query.get(session["user_id"])

    # Check permissions
    allowed = (
        current_user.id == poll.author_id
        or current_user.has_role("admin")
        or current_user.has_role("superadmin")
    )
    if not allowed:
        abort(403)

    # Delete the poll
    db.session.delete(poll)
    db.session.commit()
    flash("Peiling verwijderd.", "success")
    return redirect(url_for("opinie"))


# MAKE DIALOGUE FROM POLL
# --------------------------------------------------------------------------------------------------
@app.route("/opinie/<int:poll_id>/make-dialogue", methods=["POST"])
@login_required
def poll_make_dialogue(poll_id):
    """Create a dialogue thread from an opinion poll."""

    # Get the poll and current user
    poll = OpinionPoll.query.get_or_404(poll_id)
    current = User.query.get(session["user_id"])

    # Only the poll creator, admin or superadmin can convert
    if poll.dialogue_thread_id:
        return redirect(url_for("view_thread", thread_id=poll.dialogue_thread_id))

    # Copy original thumbnail to dialogue folder
    thumb_filename = None
    if poll.thumbnail_image:
        thumb_filename = poll.thumbnail_image
        src = os.path.join(OPINION_THUMB_UPLOAD_FOLDER, thumb_filename)
        dst = os.path.join(DIALOGUE_THUMB_UPLOAD_FOLDER, thumb_filename)
        try:
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
        except Exception:
            thumb_filename = None

    # Create dialogue thread based on the poll
    thread = DialogueThread(
        title=poll.question[:255],
        body=poll.description or None,
        author_id=current.id,
        thumbnail_image=thumb_filename,
    )
    db.session.add(thread)
    db.session.flush() 

    poll.dialogue_thread_id = thread.id
    db.session.commit()

    flash("Dialoog aangemaakt voor deze peiling.", "success")
    return redirect(url_for("view_thread", thread_id=thread.id))


# CONTACT PAGE
#--------------------------------------------------------------------------------------------------------------
@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact page with contact details and contact form"""

    name = ""
    email = ""
    subject = ""
    message = ""

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        subject = (request.form.get("subject") or "").strip()
        message = (request.form.get("message") or "").strip()

        errors = []

        if not name:
            errors.append("Naam is verplicht.")
        if not email:
            errors.append("E-mailadres is verplicht.")
        if not subject:
            errors.append("Onderwerp is verplicht.")
        if not message:
            errors.append("Bericht is verplicht.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "contact.html",
                name=name,
                email=email,
                subject=subject,
                message=message,
            )

        flash("Bedankt voor je bericht. We nemen zo snel mogelijk contact met je op.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")


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
