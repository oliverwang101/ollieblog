from datetime import datetime
from hashlib import md5
from time import time
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from app import db, login
from app.search import add_to_index, remove_from_index, query_index

####        List of followers from db to update when requested      #### 
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)
####        function for loading all users     #### 
@login.user_loader
def load_user(id):
    #function to load user
    return User.query.get(int(id))

####        OBJ FOR USERS      #### 
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    followed = db.relationship(
        'User', secondary=followers,
        #left to right
        primaryjoin=(followers.c.follower_id == id),
        #right to left
        secondaryjoin=(followers.c.followed_id == id),
        #rights followers backref, lazy = vice versa
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    language = db.Column(db.String(5))

    # how object appears when it is called
    def __repr__(self):
        return '<User {}>'.format(self.username)
    # function for setting password of object
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    # function for checking password of user
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    # determines the picture/icon for user
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)
    
    #functions for following/unfollowing other users
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
    # for checking if already following or unfollowing
    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    #get followed posts of followed users( pagination limits # presented)
    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        #include own posts in feed of posts
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    #generate a JWT token for the resetted password
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    #static methods do not receive the class as a first argument
    #decodes a token, if can validate, return that user
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

# all class methods (special method associated with the class, and not an intance)
class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

####        OBJ for POSTS     #### 
class Post(SearchableMixin, db.Model):
    # the Post class + user who made post
    __searchable__  = ['body']
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_editing = db.Column(db.Boolean(False))
    curr_page = db.Column(db.Integer)
    language = db.Column(db.String(5))
    
    def __repr__(self):
        return '<Post {}>'.format(self.body)

    def set_edit_state(self, state):
        self.is_editing = state
