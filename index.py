import os
import re
import webapp2
import jinja2
from string import letters
from google.appengine.ext import db
import time
import hmac

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True ) ## autoescape escapes HTML

SECRET = 'fjk123'

def make_secure(s):
	return hmac.new(SECRET, s).hexdigest()
class User(db.Model):
	username = db.StringProperty(required=True)
	password=db.StringProperty(required=True)

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self,template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self,template, **kw):
		self.write(self.render_str(template,**kw))


class BlogPost(db.Model):
	title = db.StringProperty(required  = True)
	content = db.TextProperty(required= True)
	created=db.StringProperty(default =time.strftime("%B %d, %Y"))
	username=db.StringProperty(required=True)
	created2 = db.DateTimeProperty(auto_now = True)


def check(username):
	flag1=0
	flag2=0
	userandpass = username.split("|")
	users = db.GqlQuery("select * from User where username = :user", user=userandpass[0])
	for user in users:
		if user.password == userandpass[1]:
			return True
	return False
	
class NewPost(Handler):
	def get(self):
		username = self.request.cookies.get("username")
		if username and check(username):
			title=""
			content=""
			error=""  
			self.render("newpost.html", title=title, content=content, error=error)
		else:
			self.redirect("login")

	def post(self):
		title = self.request.get('title')
		content=self.request.get('content')
		username = self.request.cookies.get("username")
		if username:
			if check(username):
				if title and content:
					blogpost = BlogPost(title=title, content=content, username=username.split("|")[0])
					blogpost.put()
					self.redirect("/%s" % str(blogpost.key().id()))
				else:
					self.render("newpost.html", title=title,content=content, error="Please enter both Title and Content")
			else:
				self.redirect("login")
		else:
			self.redirect("login")

def getPost(id):
	id=int(id)
	post = BlogPost.get_by_id(id)
	title=post.title
	content=post.content.replace('\n',"<br>")
	created=post.created
	return post,title,content,created


class Blog(Handler):
	def get(self):
		username = self.request.cookies.get("username")
		posts=""
		
		if username:
			if check(username):
				user = username.split("|")[0]
				posts = db.GqlQuery("select * from BlogPost where username = :user order by created desc" ,user= user)
				self.render("index.html",username=user,posts=posts)
			else:
				self.redirect("login")
		else:
			self.redirect("login")



class SignUp(Handler):
	def get(self):
		username = self.request.cookies.get("username")
		if username and check(username):
			self.redirect("/")
		self.render("signup.html")

	def post(self):
		username= self.request.get("username")
		password= self.request.get("password")
		cpassword=self.request.get("confirm")
		database = db.GqlQuery('select * from User where username = :user ', user=(username))
		flag = 0
		for data in database:
			flag = 1

		if flag==0:
			if (username and password and cpassword):
				if (len (username) <= 5):
					self.render("signup.html", errors="Username must be atleast 5 characters long")
				else:
					if (password == cpassword):
						if (len(password) <= 5):
							self.render("signup.html",errors="Password must be atleast 5 characters long")
						else:
							newuser = User(username=username, password=make_secure(password))
							newuser.put()
							users = db.GqlQuery("select * from User where username = :user", user=newuser.username)
							self.login(newuser)
							self.redirect("login")
					else:
						self.render("signup.html", errors="Passwords don't match")
			else:
				self.render("signup.html",errors="Please enter all fields")

		else:
			self.render("signup.html", errors="User Already Exists")


	def login(self, u):
		self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % ("username", str(u.username)+"|"+(make_secure(str(u.password)))))
		# if (username and password and cpassword) and (password==cpassword):
		# 	self.redirect("signup.html")
		# else:
		# 	self.render("signup.html",error="Invalid Submission")

class LogIn(Handler):
	def get(self):
		username = self.request.cookies.get("username")
		if username:
			if check(username):
				self.redirect("/")
			else:
				self.render("login.html", Success="Welcome! You can log in now.")
		else:
			self.render("login.html")

	def post(self):
		username = self.request.get("username")
		password=self.request.get("password")
		if username and password:
			users = db.GqlQuery ('select * from User where username = :user', user=(username))
			flag=0
			for user in users:
				if user.password == make_secure(password):
					self.response.headers.add_header('Set-Cookie','%s=%s; Path=/' % ("username", str(user.username)+"|"+str(user.password)))
					self.redirect("/")
					flag=1
			if flag==0:
				self.render("login.html", error="Invalid username or password.")
		else:
			self.render("login.html", error="Please enter both username and password.")

class LogOut(Handler):
	def get(self):
		self.response.headers.add_header('Set-Cookie', 'username=; Path=/')
		self.redirect("login")

class ViewPost(Handler):
 		def get(self, id):
 			post,title,content,created = getPost(id)

 			self.render("post.html",title=title,content=content,created=created)
app = webapp2.WSGIApplication([
	('/', Blog),
    ('/newpost', NewPost),
    ('/([0-9]+)', ViewPost),
    ('/signup', SignUp),
    ('/login',LogIn),
    ('/logout',LogOut)
  ], debug=True)