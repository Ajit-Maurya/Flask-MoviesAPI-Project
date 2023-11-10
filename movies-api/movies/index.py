from flask import Flask,jsonify,request,send_file
from movies.model.model import Movie,MovieSchema,Session,User,Rating
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import JWTManager,jwt_required,create_access_token,get_jwt_identity
from sqlalchemy import func,or_,asc,desc
from decimal import Decimal
from flask_swagger_ui import get_swaggerui_blueprint
import os

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'super-secret'
jwt = JWTManager(app)
SWAGGER_URL = '/api/docs'
API_URL = '/swagger.json'
SWAGGER_JSON_PATH = os.path.abspath("movies/swagger.json")

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
    API_URL,
    config={  # Swagger UI config overrides
        'app_name': "Test application"
    },
    # oauth_config={  # OAuth config. See https://github.com/swagger-api/swagger-ui#oauth2-configuration .
    #    'clientId': "your-client-id",
    #    'clientSecret': "your-client-secret-if-required",
    #    'realm': "your-realms",
    #    'appName': "your-app-name",
    #    'scopeSeparator': " ",
    #    'additionalQueryStringParams': {'test': "hello"}
    # }
)

app.register_blueprint(swaggerui_blueprint,url_prefix=SWAGGER_URL)
    
@app.route('/swagger.json')
def swagger_json():
    return send_file(SWAGGER_JSON_PATH,mimetype='application/json')

@app.route('/')
def home():
    return "hello"


@app.route('/register',methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    session = Session()

    user = session.query(User).filter_by(username=username).first()
    if user is not None:
        return jsonify({'error':'user already registered!'})

    user = User(username=username,role='user')
    user.set_password(password)

    
    session.add(user)
    session.commit()
    session.close()
    return jsonify({'message':'user created successfully!'})

@app.route('/login',methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    session = Session()

    user = session.query(User).filter_by(username=username).first()

    if user and user.check_password(password):
        access_token = create_access_token(identity=user.id)
        return jsonify({'access_token':access_token}),200
    return jsonify({'error':'Invalid_Credentials'}),401



@app.route('/movies')
def get_movies():
    session = Session()
    page = request.args.get('page',default=1,type=int)
    per_page = request.args.get('per_page',default=10,type=int)
    genre = request.args.get('genre',type=str)
    director = request.args.get('director',type=str)
    release_year = request.args.get('release_year',type=int)
    search_query = request.args.get('search_query',type=str)
    sort_field = request.args.get('sort_field',default='release_date',type=str)
    sort_direction = request.args.get('sort_direction',default='asc',type=str)

    query = session.query(Movie)

    if genre:
        query = query.filter_by(genre=genre)
    if director:
        query = query.filter_by(director=director)
    if release_year:
        query = query.filter(func.strtftime('%Y',Movie.release_date) == str(release_year))
    if search_query:
        query = query.filter(
            or_(
                Movie.title.ilike(f"%{search_query}%"),
                Movie.cast.ilike(f"%{search_query}%"),
                Movie.description.ilike(f"%{search_query}%"),
                Movie.genre.ilike(f"%{search_query}%"),
            )
        )
    
    if sort_field == 'release_date':
        if sort_direction == 'asc':
            query = query.order_by(asc(Movie.release_date))
        else:
            query = query.order_by(desc(Movie.release_date))

    elif sort_field == 'ticket_price':
        if sort_direction == 'asc':
            query = query.order_by(asc(Movie.ticket_price))
        else:
            query = query.order_by(desc(Movie.ticket_price))

    total_items = query.count()
    paginated_movies = query.offset((page-1)*per_page).limit(per_page).all()

    schema = MovieSchema(many=True)
    movies = schema.dump(paginated_movies)

    response = {
        'movies': movies,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_items + per_page - 1) // per_page,
        'total_items': total_items
    }
    session.close()
    return jsonify(response)

@app.route('/movies/<int:pk>')
def get_movie(pk):
    schema = MovieSchema(many=True)
    session = Session()
    movie = session.query(Movie).filter_by(id=pk)
    if movie is None:
        return jsonify({'error':'Movie not found'}),404
    movie = schema.dump(movie)

    session.close()
    return jsonify(movie)

@app.route('/movies',methods=['POST'])
@jwt_required()
def add_movie():
    try:
        movie_data = request.get_json()
        release_date_str = movie_data['release_date']
        release_date = datetime.strptime(release_date_str,'%Y-%M-%d')

        required = ['title','release_date','avg_rating']
        for field in required:
            if field not in movie_data:
                return jsonify({'error':f"{field} is not present!"})

        movie = Movie(
            title = movie_data['title'],
            description = movie_data['description'],
            release_date = release_date,
            director = movie_data['director'],
            cast = movie_data['cast'],
            genre = movie_data['genre'],
            avg_rating = movie_data['avg_rating'],
            ticket_price = movie_data['ticket_price']
        )
        if movie.is_valid():
            session = Session()
            session.add(movie)
            session.commit()
            session.close()
            return jsonify({"message":"movie added successfully!"}),204
        return jsonify({'error':'movie addition unsuccessful'})
    except ValueError as e:
        return jsonify({'error':str(e)}),400
    except IntegrityError as e:
        return jsonify({'error':'Movie with same title is already present!'}),400



@app.route('/movies/<int:pk>',methods=['PUT'])
@jwt_required()
def update_movie(pk):
    session = Session()
    current_user = get_jwt_identity()
    movie = session.query(Movie).filter_by(id=pk).first()
    user = session.query(User).filter_by(id=current_user).first()
    if user.role == 'admin' or user.role == 'moviemaker':
        if movie is None:
            return jsonify({'error':'Movie not found'}),404
        data = request.get_json()

        updatable = ['title','description','release_date','cast','director','genre','avg_rating','ticket_price']

        for item in updatable:
            if item in data:
                setattr(movie,item,data[item])

        session.commit()
        session.close()
        return jsonify({'message':'Updated Successfully!'}),204
    return jsonify({'error':'Access Denied'}),401

@app.route('/movies/<int:pk>',methods=['DELETE'])
@jwt_required()
def delete_movie(pk):
    current_user = get_jwt_identity()
    session = Session()
    user = session.query(User).filter_by(id=current_user).first()
    if user.role == 'admin' or user.role == 'moviemaker':
        movie = session.query(Movie).filter_by(id=pk).first()
        if movie is None:
            return jsonify({'error':'Movie not found'}),404
        session.delete(movie)
        session.commit()
        session.close()
        return jsonify({'message':'successfully deleted!'})
    return jsonify({'error':'Access Denied'}),401

@app.route('/update_rating/<int:pk>',methods=['PUT'])
@jwt_required()
def update_rating(pk):
    current_user = get_jwt_identity()
    session = Session()
    rating_data = request.args.get('rating',type=float)
    if rating_data is None:
        return jsonify({'error':'rating is not present1'}),400
    
    movie = session.query(Movie).filter_by(id=pk).first()
    if movie is None:
        return jsonify({'error':'No such movies exists with given id!'}),400
    
    rating = session.query(Rating).filter_by(user_id=current_user,movie_id=pk).first()
    if rating is None:
        rating = Rating(user_id=current_user,movie_id=pk,rating=Decimal(rating_data))
        session.add(rating)
    
    movie.update_avg_rating(Decimal(rating_data))
    session.commit()
    session.close()

    return jsonify({'message':'rated sccessfully!'}),200