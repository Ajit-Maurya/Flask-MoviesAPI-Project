from sqlalchemy import create_engine,Column,Integer,String,DATE,DECIMAL,ForeignKey
from sqlalchemy.orm import sessionmaker,relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
from marshmallow import Schema
from datetime import datetime
from werkzeug.security import generate_password_hash,check_password_hash


Base = declarative_base()

class Movie(Base):
    __tablename__ = 'movies'
    id = Column(Integer,primary_key=True,autoincrement=True)
    title = Column(String(70),unique=True)
    description = Column(String(1000))
    release_date = Column(DATE)
    director= Column(String(40))
    cast= Column(String(40))
    genre = Column(String(40))
    avg_rating = Column(DECIMAL(precision=4,scale=2))
    ticket_price = Column(DECIMAL(precision=8,scale=2))

    def is_valid(self):
        if self.avg_rating < 1 or self.avg_rating > 10:
            raise ValueError("rating value should between 1 and 10!")
        
        current_date = datetime.now()
        release = datetime.combine(self.release_date,datetime.min.time())
        if current_date < release:
            raise ValueError("release date should be in past! not in future")
        
        return True
    
    def update_avg_rating(self,rating):
        self.avg_rating = (self.avg_rating+rating)/2
    
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer,primary_key=True,autoincrement=True)
    username = Column(String(50),unique=True,nullable=False)
    password = Column(String(100),nullable=False)
    role = Column(String(30),nullable=False,default='user')

    def set_password(self,password):
        self.password = generate_password_hash(password,method='pbkdf2:sha256')
    
    def check_password(self,password):
        return check_password_hash(self.password,password)
    
class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer,primary_key=True,autoincrement=True)
    name = Column(String(30),unique=True,nullable=False)


class Rating(Base):
    __tablename__ = 'ratings'
    id = Column(Integer,primary_key=True,autoincrement=True)
    user_id = Column(Integer,ForeignKey('users.id'))
    movie_id = Column(Integer,ForeignKey('movies.id'))
    rating = Column(DECIMAL(precision=4,scale=2))


engine = create_engine('sqlite:///movie.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def create_superuser():
    username = 'admin'
    password = 'password'
    role = 'admin'

    superuser = User(username=username,role=role)
    superuser.set_password(password)

    try:
        session.add(superuser)
        session.commit()
    except IntegrityError:
        session.rollback()

def create_roles():
    roles = ['admin','moviemaker','user']

    role_data = session.query(Role).filter_by(id=1).first()

    if role_data is not None:
        return ""

    for role in roles:
        rola_data = Role(name=role)
        session.add(rola_data)
        session.commit()



# Role.metadata.create_all(engine)
create_superuser()
create_roles()

Base.metadata.create_all(engine)

class MovieSchema(Schema):
    class Meta:
        fields = ('id','title','description','release_date','cast','director','genre','avg_rating','ticket_price')