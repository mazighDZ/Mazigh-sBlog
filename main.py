import datetime as dt
from functools import wraps


from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
# from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, AnonymousUserMixin, \
    login_required
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

from forms import CreatePostForm, LoginForm, CommentsForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'

Bootstrap(app)
ckeditor = CKEditor(app)
# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app, session_options={'expire_on_commit': False})
# create logine manager
login_manager = LoginManager()
# inszialization with app
login_manager.init_app(app)


# loader manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# added avatar to our users using gravatar flassk
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# CONFIGURE TABLES


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    username = db.Column(db.String(100))
    posts = db.relationship("BlogPost", back_populates="author")
    comments = db.relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = db.relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = db.relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent_post = db.relationship("BlogPost", back_populates="comments")
    comment_author = db.relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


class Form(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired()])
    submit = SubmitField()


class AnonymousUser(AnonymousUserMixin):
    id = None  # add an id attribute to the default AnonymousUser


login_manager.anonymous_user = AnonymousUser

with app.app_context():
    db.create_all()


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(400)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def get_all_posts():
    print(current_user)
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, user=current_user)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = Form()
    if request.method == 'POST' and form.validate():
        # check if user alredy exist in data base
        if not User.query.filter_by(username=form.username.data).first() and not User.query.filter_by(
                email=form.email.data).first():
            # hash password of user
            user_password = form.password.data
            password_hash = generate_password_hash(
                user_password, method='pbkdf2:sha256', salt_length=8)

            new_user = User(username=form.username.data,
                            password=password_hash, email=form.email.data)
            with app.app_context():
                db.session.add(new_user)
                db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
        elif User.query.filter_by(email=form.email.data).first():
            flash('you alredy register with this email  ')
            return render_template("register.html", form=form)
        else:
            flash('username already taken ')
            return render_template("register.html", form=form)
    return render_template("register.html", form=form)


@app.route('/login', methods=['post', 'get'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)

                return redirect(url_for('get_all_posts'))
            else:
                flash('wrong password')

        else:
            flash('user name does not exist')

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['post', 'get'])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentsForm()
    comments_post = Comment.query.all()

    if request.method == 'POST':
        if current_user.is_authenticated:
            with app.app_context():
                new_comment = Comment(
                    text=form.body.data, author_id=current_user.id, post_id=post_id)  # ,blog_id=post_id)
                db.session.add(new_comment)
                db.session.commit()
            form.body.data = ''
            comments_post = Comment.query.all()
            return render_template("post.html", post=requested_post, user=current_user, form=form,
                                   comments=comments_post)
        else:
            flash('you must login to add comments')
    return render_template("post.html", post=requested_post, user=current_user, form=form, comments=comments_post)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=['POST', 'GET'])
@login_required
def add_new_post():
    post_form = CreatePostForm()
    if request.method == 'POST':
        date = dt.datetime.now()
        # will pass id of current user to poster that we create db relationship
        new_post = BlogPost(title=post_form.title.data,
                            subtitle=post_form.subtitle.data,
                            author_id=current_user.id,
                            date=date,
                            img_url=post_form.img_url.data,
                            body=post_form.body.data,
                            )
        with app.app_context():
            db.session.add(new_post)
            db.session.commit()
        return redirect(url_for('get_all_posts'))
    else:
        return render_template("make-post.html", form=post_form)


@app.route("/edit-post/<int:post_id>", methods=['post', 'get'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author_id=current_user.id,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
