from flask import Flask, render_template, request, redirect, url_for
from flask_login import UserMixin, login_user, login_required, logout_user, current_user, LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import flash
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blogs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'thisisasecretkey'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'signin'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50))
    author = db.Column(db.String(20))
    post_date = db.Column(db.DateTime)
    content = db.Column(db.Text)
    image = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(50), default='General')
    tags = db.Column(db.String(200), default='')  # Comma-separated tags

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    long_description = db.Column(db.Text)
    technologies = db.Column(db.String(200))  # Comma-separated
    github_url = db.Column(db.String(200))
    live_url = db.Column(db.String(200))
    image = db.Column(db.String(100))
    featured = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    is_responded = db.Column(db.Boolean, default=False)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)


@app.route("/")
def home():
    
    return render_template("index.html", title="vatsuoK")

@app.route("/about")
def about():
    return render_template("about.html", title="vatsuoK -- About",)

@app.route("/services")
def services():
    return render_template("services.html", title="vatsuoK -- Services",)


@app.route("/blogs")
def blog_list():  
    article = Blog.query.order_by(Blog.post_date.desc()).all()
    print(current_user.is_anonymous)
    if current_user.is_anonymous:
        name = "guest"
    else:
        name = current_user.username
        print("bye")
    return render_template("blogs.html", blogs=article, name=name, title="Blogs - vatsuoK")  


# Blog functions

@app.route("/addpost", methods=['POST', 'GET'])
@login_required
def addpost():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('blog_list'))
    if request.method == 'POST':
        title = request.form['title']
        author = current_user.username
        content = request.form['content']
        category = request.form.get('category', 'General')
        tags = request.form.get('tags', '')
        code = request.form.get('code', '').strip()
        language = request.form.get('language', 'python')
        if code:
            content += f"\n<pre><code class=\"language-{language}\">{code}</code></pre>"
        post_date = datetime.now()
        new_post = Blog(title=title, author=author, content=content, category=category, tags=tags, post_date=post_date)
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, 'static/uploads', filename))
                new_post.image = filename
        
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('blog_list'))
    return render_template("addpost.html", title="Add Post - vatsuoK")

@app.route('/updatepost/<int:id>', methods=['POST', 'GET'])
@login_required
def updatepost(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('blog_list'))
    if request.method == 'POST':
        title = request.form['title']
        author = current_user.username
        content = request.form['content']
        category = request.form.get('category', 'General')
        tags = request.form.get('tags', '')
        post_date = datetime.now()
        post = Blog.query.filter_by(id=id).first()
        post.title = title
        post.author = author
        post.content = content
        post.category = category
        post.tags = tags
        post.post_date = post_date
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, 'static/uploads', filename))
                post.image = filename
        
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('blog_list'))
    edit = Blog.query.filter_by(id=id).first()
    return render_template('updatepost.html', edit=edit)

@app.route('/deletepost/<int:id>')
@login_required
def deletepost(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('blog_list'))
    post = Blog.query.filter_by(id=id).first()
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('blog_list'))

# Authentication routes
@app.route('/signin', methods=['POST', 'GET'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if user.approved:
                login_user(user)
                # Redirect admins to admin dashboard
                if user.is_admin:
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('blog_list'))
            else:
                flash('Your account is pending approval.', 'warning')
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('signin.html', title="Sign In - vatsuoK")


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if this is the first user, make admin
        is_first = User.query.count() == 0
        user = User(username=username, password=generate_password_hash(password), approved=is_first, is_admin=is_first)
        db.session.add(user)
        db.session.commit()

        if is_first:
            flash('Account created successfully. You are the admin.', 'success')
        else:
            flash('Account created successfully. Please wait for admin approval.', 'info')
        return redirect(url_for('signin'))
    return render_template('signup.html', title="Sign Up - vatsuoK")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))    

# @app.route('/admin_welcome')
# @login_required
# def admin_welcome():
#     if not current_user.is_admin:
#         return redirect(url_for('blog_list'))

#     # Get admin statistics
#     total_users = User.query.count()
#     pending_users = User.query.filter_by(approved=False).count()
#     total_contacts = Contact.query.count()
#     unread_contacts = Contact.query.filter_by(is_read=False).count()

#     return render_template('admin_welcome.html',
#                          total_users=total_users,
#                          pending_users=pending_users,
#                          total_contacts=total_contacts,
#                          unread_contacts=unread_contacts)

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('blog_list'))

    # Get all users for management
    users = User.query.all()

    # Get all contacts for management
    contacts = Contact.query.order_by(Contact.submitted_at.desc()).all()

    # Get statistics
    total_users = len(users)
    pending_users = User.query.filter_by(approved=False).count()
    total_contacts = len(contacts)
    unread_contacts = Contact.query.filter_by(is_read=False).count()

    return render_template('admin.html',
                         users=users,
                         contacts=contacts,
                         total_users=total_users,
                         pending_users=pending_users,
                         total_contacts=total_contacts,
                         unread_contacts=unread_contacts)

@app.route('/approve_user/<int:user_id>')
@login_required
def approve_user(user_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    user = User.query.get_or_404(user_id)
    user.approved = True
    db.session.commit()

    flash(f'User {user.username} has been approved.', 'success')
    return redirect(url_for('admin'))

@app.route('/toggle_admin/<int:user_id>')
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    action = 'promoted to admin' if user.is_admin else 'removed from admin'
    flash(f'User {user.username} has been {action}.', 'success')
    return redirect(url_for('admin'))

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin'))
    user = User.query.get_or_404(user_id)
    # Check if user has posts
    posts_count = Blog.query.filter_by(author=user.username).count()
    if posts_count > 0:
        flash(f'Cannot delete user {user.username} because they have {posts_count} post(s).', 'danger')
        return redirect(url_for('admin'))
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} has been deleted.', 'success')
    return redirect(url_for('admin'))

# Contact management routes
@app.route('/mark_contact_read/<int:contact_id>')
@login_required
def mark_contact_read(contact_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    contact = Contact.query.get_or_404(contact_id)
    contact.is_read = True
    db.session.commit()
    flash('Contact message marked as read.', 'success')
    return redirect(url_for('admin'))

@app.route('/mark_contact_responded/<int:contact_id>')
@login_required
def mark_contact_responded(contact_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    contact = Contact.query.get_or_404(contact_id)
    contact.is_responded = True
    db.session.commit()
    flash('Contact message marked as responded.', 'success')
    return redirect(url_for('admin'))

@app.route('/delete_contact/<int:contact_id>')
@login_required
def delete_contact(contact_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    contact = Contact.query.get_or_404(contact_id)
    db.session.delete(contact)
    db.session.commit()
    flash('Contact message deleted.', 'success')
    return redirect(url_for('admin'))

@app.route('/post/<int:id>')
def post(id):
    post = Blog.query.get_or_404(id)
    # Calculate reading time (approx 200 words per minute)
    word_count = len(post.content.split())
    reading_time = max(1, round(word_count / 200))
    
    # Get related posts (same category, exclude current)
    related_posts = Blog.query.filter_by(category=post.category).filter(Blog.id != id).limit(3).all()
    
    return render_template('post.html', post=post, reading_time=reading_time, related_posts=related_posts)

# Project routes
@app.route('/projects')
def projects():
    featured_projects = Project.query.filter_by(featured=True).all()
    all_projects = Project.query.order_by(Project.created_date.desc()).all()
    return render_template('projects.html', featured_projects=featured_projects, all_projects=all_projects)

@app.route('/project/<int:id>')
def project_detail(id):
    project = Project.query.get_or_404(id)
    technologies = [tech.strip() for tech in project.technologies.split(',')] if project.technologies else []
    return render_template('project_detail.html', project=project, technologies=technologies)

@app.route('/add_project', methods=['GET', 'POST'])
@login_required
def add_project():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('projects'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        long_description = request.form.get('long_description', '')
        technologies = request.form['technologies']
        github_url = request.form.get('github_url', '')
        live_url = request.form.get('live_url', '')
        featured = 'featured' in request.form
        
        new_project = Project(
            title=title,
            description=description,
            long_description=long_description,
            technologies=technologies,
            github_url=github_url,
            live_url=live_url,
            featured=featured
        )
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, 'static/uploads', filename))
                new_project.image = filename
        
        db.session.add(new_project)
        db.session.commit()
        flash('Project added successfully!', 'success')
        return redirect(url_for('projects'))
    
    return render_template('add_project.html')

@app.route('/update_project/<int:id>', methods=['GET', 'POST'])
@login_required
def update_project(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('projects'))
    
    project = Project.query.get_or_404(id)
    
    if request.method == 'POST':
        project.title = request.form['title']
        project.description = request.form['description']
        project.long_description = request.form.get('long_description', '')
        project.technologies = request.form['technologies']
        project.github_url = request.form.get('github_url', '')
        project.live_url = request.form.get('live_url', '')
        project.featured = 'featured' in request.form
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, 'static/uploads', filename))
                project.image = filename
        
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('project_detail', id=project.id))
    
    return render_template('update_project.html', project=project)

@app.route('/delete_project/<int:id>')
@login_required
def delete_project(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('projects'))
    
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('projects'))

# Search functionality
@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        # Search in title, content, and tags
        blogs = Blog.query.filter(
            db.or_(
                Blog.title.contains(query),
                Blog.content.contains(query),
                Blog.tags.contains(query)
            )
        ).all()
    else:
        blogs = []
    
    return render_template('search.html', blogs=blogs, query=query)

# Contact form
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']

        # Save contact message to database
        contact_message = Contact(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        db.session.add(contact_message)
        db.session.commit()

        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Return JSON response for AJAX requests
            return {'success': True, 'message': 'Thank you for your message! I\'ll get back to you soon.'}
        else:
            # Traditional form submission - redirect with flash message
            flash('Thank you for your message! I\'ll get back to you soon.', 'success')
            return redirect(url_for('contact'))

    return render_template('contact.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
    os.system('clear')
    app.run(debug=False, host='0.0.0.0')