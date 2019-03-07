from flask import Flask, render_template, request, session, redirect, url_for
import yaml
from flask_mysqldb import MySQL
from passlib.context import CryptContext
from functools import wraps
from flask_uploads import UploadSet, configure_uploads, IMAGES
from flask_mail import Mail, Message


myctx = CryptContext(schemes=["sha256_crypt"])
app = Flask(__name__)

details=yaml.load(open('db.yaml'))

app.config['MYSQL_HOST']=details['host']
app.config['MYSQL_USER']=details['user']
app.config['MYSQL_PASSWORD']=details['password']
app.config['MYSQL_DB']=details['database']
app.secret_key= details['skey']

##############configure file uploads############
imgattach = UploadSet('photos', IMAGES)
app.config['UPLOADED_ARCHIVES_DEST']='uploads'
app.config['UPLOADS_DEFAULT_DEST']='uploads'
configure_uploads(app, imgattach)
################################################


mysql=MySQL(app)

def check_logged_in(func):
    @wraps(func)
    def wrap(*args, **kargs):
        if 'user' in session:
            return func(*args, **kargs)
        else:
            return redirect(url_for('login'))
    return wrap 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        un=str(request.form['un'])
        pw=request.form['pw']
        cur = mysql.connection.cursor()
        que="SELECT * from  users where username=%s"
        cur.execute(que,[un])
        result=cur.fetchall()
        if result:
            mysql.connection.commit()
            cur.close()
            if result[0][1] == un and myctx.verify(pw,result[0][2]):
                session['user']=result[0][1]
                session['role']=result[0][5]
                print('Successfully logged in!')
                return redirect(url_for('index'))
            else:
                return render_template('login.html', msg="Username or password wrong")
        else:
            return render_template('login.html', msg='Username not found')
    else:
        return render_template('login.html', msg='Please login')

@app.route('/updatepassword', methods=['GET', 'POST'])
@check_logged_in
def updpassword():
    if request.method == 'POST':
        pw=request.form['oldpw']
        npw=request.form['newpw']
        cpw=request.form['confpw']
        if npw != cpw:
            return render_template('updatepass.html',msg='New Passwords does not match!')
        #initialize cursor
        cur=mysql.connection.cursor()
        
        ###get hash
        row_count=cur.execute("select password from users where username=%s",[session['user']])
        data=cur.fetchall()

        if myctx.verify(pw, data[0][0]):
            hsh=myctx.hash(npw)
            cur.execute("update users set password=%s where username=%s", [hsh, session['user']])
            mysql.connection.commit()
            cur.close()
            return render_template('updatepass.html', msg='Password updated successfully!')
        else:
            return render_template('updatepass.html', msg='Incorrect old password')
    else:
        return render_template('updatepass.html', msg="Update your password!")
        
@app.route('/logout')
@check_logged_in
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/')
def index():
    if session.get('user') != None:
        return render_template('index.html', msg=session['user'])
    else:
        return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        un=request.form['un']
        pw=request.form['pw']
        rpw=request.form['rpw']
        if pw != rpw:
            return render_template('signup.html',msg='Passwords does not match!')
        eml=request.form['email']
        phno=request.form['phno']
        cur=mysql.connection.cursor()
        cur.execute('select username, email from users')
        result=''
        for u,e in cur:
            if u == un:
                result+='Username already taken\n'
            if e == eml:
                if len(result)>0:
                    result='Username and Email already taken\n'
                else:
                    result='Email already taken'
        if len(result) != 0:
            return render_template('signup.html', msg=result)
        else:
            hsh=myctx.hash(pw)
            que='insert into users(username, password, email, phone) values(%s, %s, %s, % s)'
            cur.execute(que,(un,hsh,eml,phno))
            mysql.connection.commit()
            cur.close()
            session['user']=un
            return render_template('index.html',msg=session['user'])
    return render_template('signup.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/store', methods=['GET', 'POST'])
def store():
    if request.method == 'POST':
            sname=request.form.get('stname')
            cur=mysql.connection.cursor()
            

            r1=cur.execute('select * from ware where city=%s',[sname])
            v=cur.fetchall()
            cur.close()    
            return render_template("store.html",details=v)
            
    else:
        cur=mysql.connection.cursor()
        r1=cur.execute('select city from ware group by city')
        v=cur.fetchall()
        cur.close()
        return render_template("store.html",data=v)

@app.route('/inquiry')
def inquiry():
    return 'inquiry'
    #return render_template('in.html')

@app.route('/adminpanel', methods=['GET', 'POST'])
def adminpanel():
    if request.method == 'GET':
        return render_template('adminpanel.html')

@app.route('/addproduct', methods=['POST'])
def addproduct():
    if 'imgfile' in request.files:
            pnum=request.form.get('tno')
            ptype=request.form.get('ptype')
            prsize=request.form.get('prosize')
            destype=request.form.get('design')
            upimg=request.files['imgfile']

            cur=mysql.connection.cursor()
            
########### check if the product already exits#############
            r1=cur.execute('select * from product_data where product_number=%s',[pnum])
            if r1 != 0:
                return render_template("adminpanel.html", msg="Product number already exist.")

            row=cur.execute('select pid from product_data order by pid desc limit 1')
            if row == 0:
                val=1
            else:
                val=cur.fetchall()
                val=val[0][0]+1
            
            upimg = 'a'+str(val)+upimg.filename
            filename= imgattach.save(request.files['imgfile'], name=upimg)
            rowcnt=cur.execute("insert into product_data(product_number, product_type, product_size, design_type, image_name) values(%s,%s,%s,%s,%s)", [pnum, ptype, prsize, destype, upimg])

            mysql.connection.commit()
            cur.close()        
            return render_template("adminpanel.html")
            
    else:
        return 'fail'

@app.route('/removeproduct', methods=['GET', 'POST'])
def removeproduct():
    if request.method == 'GET':
        return render_template('removeproduct.html')
    else:
        pnum=request.form.get('tno')
        r1=cur.execute('select * from product_data where product_number=%s',[pnum])
        if r1 == 0:
            return render_template('adminpanel.html',msg="Product does not exist")
        else:
            ###### show details
                return 'hello'
            ###########

@app.route('/addstore', methods=['POST'])
def addstore():
    if request.method == 'POST':
            sname=request.form.get('stname')
            saddr=request.form.get('stadd')
            scity=request.form.get('stcity')
            spin=request.form.get('stpin')
            spho=request.form.get('stpno')

            cur=mysql.connection.cursor()
            
########### check if the product already exits#############
            r1=cur.execute('select * from ware where storname=%s', [sname])
            if r1 != 0:
                return render_template("adminpanel.html", msg="Store already exist.")
            r=cur.execute("insert into ware(storname, addr, city, pin, phonno) values(%s,%s,%s,%s,%s)", (sname, saddr, scity, spin,spho))
            mysql.connection.commit()
            cur.close()        
            return render_template("adminpanel.html",msg="Store successfully added")
            
    else:
        return 

@app.route('/review', methods=['POST','GET'])
def review():
    if request.method == 'POST':
            review=request.form.get('add')

            cur=mysql.connection.cursor()
            r1=cur.execute('insert into revs(rev) values (%s)',[review])

            mysql.connection.commit()
            cur.close()        
            return render_template("review.html",msg="Review added Successfully")
            
    else:
        return render_template("review.html")



@app.route('/removestore', methods=['POST'])
def removestore():
    if request.method == 'POST':
            sname=request.form.get('stname')

            cur=mysql.connection.cursor()
            
########### check if the product already exits#############
            r1=cur.execute('select * from ware where storname=%s',sname)
            if r1 != 0:
                r1=cur.execute('delete from ware where storname=%s',sname)

            else:
                return render_template("adminpanel.html", msg="Store Doesn't exist")
            

            mysql.connection.commit()
            cur.close()        
            return render_template("adminpanel.html",msg="Store Removed Successfully")
            
    else:
        return 




cart=[]

@app.route('/quotation', methods=['GET', 'POST'])
def quotation():
    print("sdasd")
    if request.method == 'POST':
        pro=request.form.get('add')
        #d=request.form.get('tilecount')
        cart.append(pro)
        print("here")
        cur=mysql.connection.cursor()
        r1=cur.execute('select * from product_data where product_number=%s',[pro])
        print(cart)
        if r1 != 0:
            #for r in cart:
            #insert into ware(storname, addr, city, pin, phonno) values(%s,%s,%s,%s,%s)", (sname, saddr, scity, spin,spho))
            r1=cur.execute('create table temp(pid int auto_increment primary key,n1 varchar (40),n2 varchar(40),n3 varchar(40),n4 varchar(40))')

            for i in cart:

                r1=cur.execute('select * from product_data where product_number=%s',[i])
                v=cur.fetchall()
                print(v)
                for row in v:
                
                    r1=cur.execute('insert into temp(n1,n2,n3) values (%s,%s,%s)',[row[1],row[2],row[3]])
                
            r1=cur.execute('select * from temp')  
            c123=cur.fetchall()
            #print("works")
           # print(c)

            r1=cur.execute('drop table temp')  
            
           
        

        else:

            return render_template("quotation.html", msg="Product Doesn't exist",data=c123 )
            
      
        mysql.connection.commit()
        cur.close()        
        return render_template("quotation.html",msg="Product added Successfully",data=c123)
            

        
        





    return render_template("quotation.html")

 
if __name__ == '__main__':
    app.run(debug=True)
