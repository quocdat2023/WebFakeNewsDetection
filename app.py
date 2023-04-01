from pymongo import MongoClient
from bson.objectid import ObjectId
import os, pathlib, pickle, re, string, pandas as pd, requests, google.auth.transport.requests, urllib.request, datetime
from flask import Flask, flash, render_template, request, abort, redirect, url_for, session, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.decomposition import TruncatedSVD
from authlib.integrations.flask_client import OAuth
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
from werkzeug.utils import secure_filename
from flask_pymongo import PyMongo
from pyvi import ViTokenizer
from vncorenlp import VnCoreNLP
from bs4 import BeautifulSoup
import random


app = Flask(__name__) 
app.config["SECRET_KEY"] = "secrectkey"
client = MongoClient("mongodb+srv://quocdat51930:2TyF3b3x3yOnhIT4@webdetectfakenews.z898ahe.mongodb.net/?retryWrites=true&w=majority")
db = client.fakenews
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = 'static/uploads/'

# app.secret_key = "secret key"
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


global student
name = ""
picture = ""
student = db.admin.find({})
users = ""

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
    # new = db.realnews.find().limit(3)
    pipeline = [
        { '$sample': { 'size': 3 } },
        { '$limit': 3 }
    ]
    new = db.forum_report.aggregate(pipeline)
    news = db.forum_report.find_one({"_id": ObjectId(id)})
    return render_template("view.html", details=news,newtop3=new)

@app.route("/admin/view/<id>")
def adminview(id):
    # new = db.realnews.find().limit(3)
    pipeline = [
        { '$sample': { 'size': 3 } },
        { '$limit': 3 }
    ]
    new = db.forum_report.aggregate(pipeline)
    news = db.forum_report.find_one({"_id": ObjectId(id)})
    return render_template("view.html", details=news,newtop3=new)


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
        query = request.form['message']
        domains = ['nghiencuulichsu.com','nguoikesu.com', 'lyluanchinhtri.vn','tingia.gov.vn','thethao247.vn', 'chinhphu.vn', 'nld.com.vn', 'plo.vn', 'vtc.vn', 'tienphong.vn', 'quochoi.vn', 'baochinhphu.vn', 'laodong.vn',  'vietnamnet.vn', 'suckhoedoisong.vn', 'tuoitre.vn', 'thanhnien.vn', 'vov.vn', 'doisongphapluat.vn', 'hanoimoi.com.vn', 'tapchicongsan.org', 'hochiminh.org', 'nhandan.com.vn','baophapluat.vn', 'baodautu.vn', 'vnmedia.vn', 'giaoducthoidai.vn', 'baodansinh.vn', 'vanhien.vn', 'dantri.com.vn', 'baomoi.com', 'bnews.vn', 'vnanet.vn', 'vietnam.vnanet.vn', 'cucnghethuatbieudien.gov.vn', 'moh.gov.vn', 'covid19.gov.vn']
        random.shuffle(domains)
        site_query = ' OR '.join([f'site:{domain}' for domain in domains])
        url = "https://www.google.com/search?q=" + query.replace(" ", "+") + " " + site_query
        # print(url)

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        links = []
        a = 0
        for div in soup.find_all('div', class_='yuRUbf'):
            link = div.find('a')['href']
            if link.endswith('/'):
                link = link[:-1]
            a = a + 1
            links.append("<tr><td>"+str(a)+"</td><td><a style='overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 1; /* number of lines to show */ line-clamp: 1; -webkit-box-orient: vertical;' target='_blank' href="+link+">"+link+"</a></td></tr>")
        
        links_html = ''.join(links)  # Concatenate all links as HTML code
        return links_html  # Return the concatenated HTML code

        
    else:
        # return redirect("/check")
        return jsonify({'error' : 'Missing data!'})

@app.route('/searchurl', methods=['GET','POST'])
def UrlSearch():
     if ((request.method == 'POST') and (request.form['message'] != "")):
        query = request.form['message']
        domains = ['thethao247.vn', 'chinhphu.vn', 'nld.com.vn', 'plo.vn', 'vtc.vn', 'tienphong.vn', 'quochoi.vn', 'baochinhphu.vn', 'laodong.vn',  'vietnamnet.vn', 'suckhoedoisong.vn', 'tuoitre.vn', 'thanhnien.vn', 'vov.vn', 'doisongphapluat.vn', 'hanoimoi.com.vn', 'tapchicongsan.org', 'hochiminh.org', 'nhandan.com.vn','baophapluat.vn', 'baodautu.vn', 'vnmedia.vn', 'giaoducthoidai.vn', 'baodansinh.vn', 'vanhien.vn', 'dantri.com.vn', 'baomoi.com', 'bnews.vn', 'vnanet.vn', 'vietnam.vnanet.vn', 'cucnghethuatbieudien.gov.vn', 'moh.gov.vn', 'covid19.gov.vn']
        random.shuffle(domains)
        site_query = ' OR '.join([f'site:{domain}' for domain in domains])
        url = "https://www.google.com/search?q=" + query.replace(" ", "+") + " " + site_query
        # print(url)

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        links = []
        for div in soup.find_all('div', class_='yuRUbf'):
            link = div.find('a')['href']
            links.append(link)
        for item in links:
            return "<li>"+item+"</li>"

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
    global name,picture,id_google
    name = session["name"] 
    picture = session["picture"] 
    id_google = session["google_id"]
    return redirect("/protected_area")

@app.route("/logout")
def logout():
    session.clear()
    global name,picture,users
    name = ""
    picture = ""
    users = ""
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
    law = db.forum_report.find({"Category":"law","Status":1}).limit(12)
    disaster = db.forum_report.find({"Category":"disaster","Status":1}).limit(12)
    ecomomy = db.forum_report.find({"Category":"ecomomy","Status":1}).limit(12)
    health = db.forum_report.find({"Category":"health","Status":1}).limit(12)
    seciurity = db.forum_report.find({"Category":"seciurity","Status":1}).limit(12)
    other = db.forum_report.find({"Category":"other","Status":1}).limit(12)
    return render_template('forum.html',names = name,pictures = picture,law =law,disaster=disaster,ecomomy = ecomomy,health = health, seciurity = seciurity,other=other)

@app.route('/post')
def post():
    # realnews = db.realnews.find({"label":1})
    law = db.forum_report.find({"Category":"law","Status":1}).limit(12)
    disaster = db.forum_report.find({"Category":"disaster","Status":1}).limit(12)
    ecomomy = db.forum_report.find({"Category":"ecomomy","Status":1}).limit(12)
    health = db.forum_report.find({"Category":"health","Status":1}).limit(12)
    seciurity = db.forum_report.find({"Category":"seciurity","Status":1}).limit(12)
    other = db.forum_report.find({"Category":"other","Status":1}).limit(12)
    return render_template('post.html',names = name,pictures = picture,law =law,disaster=disaster,ecomomy = ecomomy,health = health, seciurity = seciurity,other=other)


@app.route('/admin/mangeforum')
def mangeforum():
    # realnews = db.realnews.find({"label":1})
    law = db.forum_report.find({"Category":"law","Status":1}).limit(100)
    disaster = db.forum_report.find({"Category":"disaster","Status":1}).limit(100)
    ecomomy = db.forum_report.find({"Category":"ecomomy","Status":1}).limit(100)
    health = db.forum_report.find({"Category":"health","Status":1}).limit(100)
    seciurity = db.forum_report.find({"Category":"seciurity","Status":1}).limit(100)
    other = db.forum_report.find({"Category":"other","Status":1}).limit(100)
    return render_template('mangeforum.html',names = name,pictures = picture,law =law,disaster=disaster,ecomomy = ecomomy,health = health, seciurity = seciurity,other=other)


@app.route('/check')
def check():
    return render_template('check.html',names = name,pictures = picture)

@app.route('/admin/login/')
def loginAdmin():
    return render_template('login.html')


@app.route('/admin/dashboard/')
def dashboard():
    if not users:
        return redirect(url_for('login'))
    else:
         return render_template('dashboard.html',names = users,ten = name,pictures = picture)
   

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
                return redirect('/admin/dashboard/')
            else:
                return redirect('login.html')
        else:
            return redirect('login.html')
    else:
        return redirect('login.html')


app.run(port=5000,debug=True)