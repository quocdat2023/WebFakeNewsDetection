from pymongo import MongoClient
from bson.objectid import ObjectId
import os, pathlib, pickle, re, string, requests, google.auth.transport.requests, pandas as pd,urllib.request,datetime
from flask import Flask,flash, render_template, request, abort, redirect, url_for, session,jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.decomposition import TruncatedSVD
from authlib.integrations.flask_client import OAuth
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
from werkzeug.utils import secure_filename
# from bson.objectid import ObjectId

app = Flask(__name__) 

UPLOAD_FOLDER = 'static/uploads/'

client = MongoClient('127.0.0.1', 27017)
db = client.fakenews
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
GOOGLE_CLIENT_ID = "410564700513-0qlmt8cg5qt6pjihuf6us28j1q7e09mv.apps.googleusercontent.com"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  
        else:
            return function()
    return wrapper

tfvect = TfidfVectorizer(analyzer='word', max_features=4189, ngram_range=(1, 2))
loaded_model = pickle.load(open('./static/model/LogisticRegression.pkl', 'rb'))
dataframe = pd.read_csv('./static/data/data_new.csv',on_bad_lines='skip')
dataframe.reset_index(inplace = True)
dataframe.drop(["index"], axis = 1, inplace = True)
global student
student = db.admin.find({})

def wordopt(text):
    text = text.lower()
    text = re.sub('\[.*?\]', '', text)
    text = re.sub("\\W"," ",text) 
    text = re.sub('https?://\S+|www\.\S+', '', text)
    text = re.sub('<.*?>+', '', text)
    text = re.sub('[%s]' % re.escape(string.punctuation), '', text)
    text = re.sub('\n', '', text)
    text = re.sub('\w*\d\w*', '', text)    
    return text

dataframe["data"] = dataframe["data"].apply(wordopt)
x = dataframe['data']
y = dataframe['label']
name = ""
picture = ""
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=0)

def fake_news_det(news):
    tfid_x_train = tfvect.fit_transform(x_train)
    tfid_x_test = tfvect.transform(x_test)
    input_data = [news]
    vectorized_input_data = tfvect.transform(input_data)
    prediction = loaded_model.predict(vectorized_input_data)
    return prediction


@app.route('/')
def home():
    return render_template('index.html',names = name,pictures = picture)


@app.route("/user-manual")
def manual():
       student = db.admin.find({})
       return render_template("user-manual.html",details=student)


@app.route("/insert",methods=['POST'])
def insert():
       name = request.form.get('Fname')
       mobile = request.form.get('mobile')
       address = request.form.get('address')
       comment = request.form.get('comment')

       db.admin.insert_one(
              {
                     'name': name,
                     'mobile': mobile,
                     'address': address,
                     'comment': comment
              }
       )
       return redirect("/usermanual")


@app.route("/reflect",methods=['POST'])
def reflect():
    if 'image_upload' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['image_upload']
    email = request.form.get('email')
    name = request.form.get('fullname')
    phone = request.form.get('phone')
    link = request.form.get('link')
    content = request.form.get('content')
    label = 0
    today = datetime.date.today().strftime("%d/%m/%Y")
    if file.filename == '':
        flash('No image selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.realnews.insert_one({ 
                     'email': email,
                     'fullname': name,
                     'phone': phone,
                     'link': link,
                     'content':content,
                     'image':filename,
                     'label':label,
                     'date': today}) 
        # print('upload_image filename: ' + filename)
        # flash('Image successfully uploaded and displayed below')
        return redirect("/check")
    else:
        # flash('Allowed image types are - png, jpg, jpeg, gif')
        return redirect(request.url)

@app.route('/display/<filename>')
def display_image(filename):
    #print('display_image filename: ' + filename)
    return redirect(url_for('static', filename='uploads/' + filename), code=301)

@app.route("/update/<id>")
def update(id):
    # student = db.admin.find({})
    # student = db.admin.find_one({ "_id": id})
    return render_template("update.html", details=student)

@app.route("/view/<id>")
def view(id):
    # student = db.admin.find({})
    news = db.realnews.find_one({"_id": ObjectId(id)})
    return render_template("view.html", details=news)


@app.route("/update_record/<id>",methods=["POST"])
def update_record(id):

    name = request.form.get('Fname')
    mobile = request.form.get('mobile')
    address = request.form.get('address')
    comment = request.form.get('comment')

    db.admin.update_one(
            {"_id": id},
           {'$set':
                   {
                            'name': name,
                            'mobile': mobile,
                            'address': address,
                            'comment': comment
                   }
          })

    return redirect('/show')



@app.route('/delete/<id>/')
def delete(id):
    db.admin.delete_one({"_id": ObjectId(id)})
    return redirect("/usermanual ")

@app.errorhandler(404)
def error_404(e):
       return render_template('404.html')


@app.route('/predicts', methods=['GET','POST'])
def predicts():
    if ((request.method == 'POST') and (request.form['message'] != "")):
        message = request.form['message']
        pred = fake_news_det(message)
        if pred > 0:
            return '<h3 style="color:#d9534f;"><b>Tin giả</b></h3>'
        else:
            return '<h3 style="color:#5f4dee;"><b>Tin thật</b></h3>'
    else:
        # return redirect("/check")
        return jsonify({'error' : 'Missing data!'})

@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["picture"] = id_info.get("picture")
    global name,picture
    name = session["name"] 
    picture = session["picture"] 

    return redirect("/protected_area")

@app.route("/logout")
def logout():
    session.clear()
    global name,picture
    name = ""
    picture = ""
    return redirect("/")

@app.route("/protected_area")
@login_is_required
def protected_area():
    return render_template('index.html',names = name,pictures = picture)

@app.route('/detectfakenews')
def detectfakenews():
    return render_template('detect-fake-news.html',names = name,pictures = picture)

@app.route('/preventfakenews')
def preventfakenews():
    return render_template('prevent-fake-news.html',names = name,pictures = picture)

@app.route('/usermanual')
def usermanual():
    realnews = db.realnews.find({})
    return render_template('user-manual.html',names = name,pictures = picture,reals =realnews )

@app.route('/forum')
def forum():
    # realnews = db.realnews.find({"label":1})
    realnews = db.realnews.find({})
    return render_template('forum.html',names = name,pictures = picture,reals =realnews )

@app.route('/check')
def check():
    return render_template('check.html',names = name,pictures = picture)

@app.route('/admin/login/')
def loginAdmin():
    return render_template('login.html')
    
@app.route("/loginadmin", methods=['POST'])
def loginadmin():
    if request.method == "POST":
        user = request.form.get("user")
        password = request.form.get("password")
        user_found = db.admin.find_one({"user": user})
        if user_found:
            user_val = user_found['user']
            passwordcheck = user_found['password']
            if password == passwordcheck:
                session["user"] = user_val
                global users,name
                users  =  session["user"]
                name = user_found['name']
                return redirect('/dashboard')
            else:
                return redirect('login.html')
        else:
            return redirect('login.html')
    else:
        return redirect('login.html')

@app.route("/dashboard")
def dashboard():
    realnews = db.realnews.find({})
    return render_template('dashboard.html',names = users,ten = name,pictures = picture,reals =realnews)

app.run(port=5000,debug=True)