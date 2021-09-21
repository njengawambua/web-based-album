
from flask import Flask, render_template,request,session,g,current_app,redirect,url_for,make_response
from flask_socketio import SocketIO,join_room,leave_room,rooms
from datetime import  datetime
import json
import sqlite3
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from random import random
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
maindb='maindb.sqlite3'
import os
from threading import Thread
import requests
from requests import Request
import ssl




app = Flask(__name__)


app.config['SECRET_KEY'] = 'secret!'
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'peterwambua254@gmail.com'
app.config['MAIL_PASSWORD'] = "njenga@254"
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True


sio = SocketIO(app,async_mode="threading")
mainn=0



def getdb(maindb):
  try:
    db = sqlite3.connect(maindb)
    return db
  except:
    return "db conn failed"

@app.route("/previewall/<id>")
def previewall(id):
   return render_template("previewall.html",id=id)

@sio.on("join",namespace="/listphotos")
def join(data):
  print("joining",data)
  d=str(data)
  join_room(d,namespace="/listphotos")
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      ##get album details
      al=cur.execute("select * from Albums where Id=(?)",[data]).fetchone()
      if not al:
        print("no album data")
        data={"Type":"NoData"}
        sio.emit("managealbum",data,room=request.sid,namespace="/listphotos")
        db.close()
        return
      else:
        print("album",al)
        myalbum={'Type':'Update','Id':al[0],'Event':al[1],'Venue':al[2],'EventDate':al[3],'Desc':al[4],'Date':al[5],"Flagged":al[8],'DP':al[7]}
        print("my album",myalbum)
        sio.emit("managealbum",myalbum,room=request.sid,namespace="/listphotos")
        #EMIT ALBUM DATA
        try:
          print("getting photos")
          photos=cur.execute("select * from EventMedia where AlbumId=(?)",[data]).fetchall()
          if not photos:
            print("no photos")
          else:
            print("photos",photos)
            print("almaost in loop")
            for photo in photos:
              print("in loop")
              ##get name desc
              ##add to dic
              dits={'Id':photo[0],"Name":photo[1],"Desc":photo[2],"Type":photo[7]}
              #EMIT PHOTO DATA
              print(dits)
              sio.emit("newdata",dits,room=request.sid,namespace="/listphotos")
            return
        except:
          print("failed to get photos")
          return("failed to get photos")
    except :
      print("unable to get albums")
      return "unable to get albums"
  except :
      print("failed to get db")
      return("failed to get db")

@app.route("/preview/<id>")
def preview(id):
  myphotos=[]
  myalbum={}
  print("\n\nthis is id",id)
  if request.method=='GET':
    albmid=id
    if not albmid:
      print("no album id go back")
      return("no album id go back")
    try:
      print("getting db")
      db=getdb(maindb)
      cur=db.cursor()
      print("got db")
      try:
        ##get album details
        al=cur.execute("select * from Albums where Id=(?)",[albmid]).fetchone()
        if not al:
          print("no album data")
        else:
          print("album",al)
          myalbum={'Id':al[0],'Event':al[1],'Venue':al[2],'EventDate':al[3],'Desc':al[4],'Date':al[5]}
          print("my album",myalbum)
      except :
        print("unable to get albums")
        return "unable to get albums"
      try:
        print("getting photos")
        photos=cur.execute("select * from EventMedia where AlbumId=(?)",[albmid]).fetchall()
        if not photos:
          print("no photos")
        else:
          print("photos",photos)
          for photo in photos:
            ##get name desc
            ##add to dic
            dits={'Id':photo[0],"Name":photo[1],"Desc":photo[2]}
            myphotos.append(dits)
          #add to list
        print("myphotooooos",myphotos)
        return render_template("listphotos.html",myphotos=myphotos,myalbum=myalbum)
      except :
        print("failed to get photos")
        return("failed to get photos")
    except :
        print("failed to get db")
        return("failed to get db")

@sio.on("Managephoto",namespace ="/viewphoto")
def managephoto(data):
  print(data)
  userid=''
  user=''
  ##get db
  if 'User' in session.keys():
    print("in session")
    user=session['User']
    print(user)
  else:
    print("not in session relogin")
    return
  try:
    print("getting cursor")
    db=getdb(maindb)
    cur=db.cursor()
    print("got cursor")
    try:
      #get photo and check if allowed to edit it
      print("checking if photo exixst")
      p=cur.execute("select * from EventMedia where Id=(?)",([data['Id']])).fetchone()
      print(p)
      if not p:
        print("photo not found")
        db.close()
        return
      else:     
        print("photo found")  
        print(p)
        print(user['Id'])        
        ##no need to check if creator
        ##check if edit desc or delete photo
        if data['Type']=='Edit':
          print("checking if allowed")
          if user["Role"]=='Admin' or p[3]==user['Id']:
            print("got Edit")
            cur.execute("Update EventMedia set Description=? where Id=?",([data['Desc'],data['Id']]))
            db.commit()
            db.close()
            print("desc updated")
            return
          else:
            print("not allowed to edit")
            db.close()           
            return  
        if data['Type']=='Delete':
          print("checking if allowed")
          if user["Role"]=='Admin' or p[3]==user['Id']:
            print("got delete")
            cur.execute("Delete  from EventMedia where Id=?",([data['Id']]))
            db.commit()
            db.close()           
            sio.emit("listphotos",data,namespace="/gall")
            print("deleted")
            return
          else:
            db.close()
            print("not allowed to delete")
            return
        if data['Type']=='Flag':     
          print("got flag")
          cur.execute("Update EventMedia set Flagged=? where Id=?",(['True',data['Id']]))
          db.commit()
          db.close()
          print("desc updated")
          return
        ##add flag
        else:
          print("uknown type")
          db.close()
          return
    except:
      db.rollback()
      db.close()
      print("Unable to edit check db")
      return
  except:
    print("db error unable to get db")
    return

@app.route('/teste',methods=['POST'])
def teste():
  ext='.jpeg'
  imageext=('.jpeg','.JPEG','.jpg','.npg')
  audioext=('.mp3','.MP3','.aac','.AAC')
  videoext=('.mp4','.MP4','.MKV','.mkv')
  newdata={}
  if not session['User']:
    autoLogin()
    print("need to relogin")
    return "relogin"
  user=session['User']
  userid=user['Id']
  print("\n userid",userid)
  if request.method=="POST":
    desc=request.values
    pics=request.files
    albumid=desc['albumid']
    print(desc)
    print(albumid)
    print("length of files",len(pics))
    if len(pics)>0:
      try:
        print("getting db")
        db=getdb(maindb)
        cur=db.cursor()
        print("got db")
        for pic in pics:
          #take pic and same desc put in db after name change
          po=request.files[pic]
          print('pooo',po)
          if po:
            print("got po")
            print(po)
            print(type(po))
            fname=secure_filename(po.filename)
            if 'image' in po:
              print("got image")
              ext='.jpeg'
            if 'video' in po:
              print("got video")
            if 'audio' in po:
              print("got audio")
            if 'document' in po:
              print("got doc")           
            print(list(po))
          ##add to db
            if fname:
              print('\n this is fname',fname)
              ev=fname.rindex('.')
              ext=fname[ev:]
              print(ev)
              print(ext)
              #get desc
              print("before d")
              print(desc)
              descs=''
              print("during dec")
              g=dict(request.form)
              print(g)
              print(fname)
              print(g[po.filename])
              descs=g[po.filename]
              print("after d")
              if not descs:
                descs=""
              name="photo"+str(int(random()*1000000))+ext
              print("naame",name)
              try:
                print("adding photo",name)
                date=datetime.now()
                mimetype = po.content_type
                fg=mimetype.rindex('/')
                ds=mimetype[:fg]
                print("\n\n\n naaame \n",ds)
                albumid=int(albumid)
                newdata={"Name":name,"AlbumId":albumid,'Desc':descs}
                print("new data",newdata)
                print("adding photo to db",name)           
                print(name,descs,userid,date,albumid)
                cur.execute("insert into EventMedia (Name,Description,UserId,Date,AlbumId,Type) values (?,?,?,?,?,?)",([fname,descs,userid,date,albumid,ds]))
                z='./static/Images/EventPictures/'+fname
                print("saved to file",name)
                print(po)     
                print(mimetype)
                print(z)
                po.stream.seek(0)
                po.save(z,buffer_size=16384)
                po.close()
                print("data commited")
                db.commit()
              except :
                db.rollback()
                cur.close()
                db.close()
                print("unable to add this pic",name)
            else:
              print("did not get secure file name",pic)
          else:
            print("did not get file",pic)
        print(newdata)
        sio.emit("newdata",newdata,namespace="/listphotos")
        print("\n \n at the end this is the album id\n",albumid)
        return redirect(url_for('previewall',id=albumid))
      except:
        print("did not get db")
        return ("did not get db")
    else:
      print("no files")
      return "missing files"
  else:
    print("use get")
    return ("use get")

@app.route('/viewphoto')
def viewphoto():
  return render_template('viewphoto.html')

@sio.on("image")
def image(data):
  print(data)
  n=str(int(random()*100000)) +"jpg"
  fi=open(n,"wb+")
  print(fi)
  print("write data")
  fi.write(data)
  print("written data")
  fi.flush()
  fi.close()

@sio.on("image",namespace="/mine")
def image(data):
  for i in data:
    print(i['Type'])
    n=str(int(random()*100000)) +".jpg"
    print(n)
    fi=open(n,"wb+")
    print(fi)
    print("write data")
    fi.write(i['File'])
    print("written data")
    fi.flush()
    fi.close()

@app.route('/addphotos')
def addphotos():
  userid=67123653
  if request.method=='GET':
    photos=request.files['eventphotos']
    albumid=request.args.get('albumid')
    try:
      db=getdb(maindb)
      cur=db.cursor()
      try:
        for i in photos:
          #get photo name or create one
          #add to db
          name=i
          date=datetime.now()
          cur.execute("insert into EventMedia (Name,Date,UserId,AlbumId) values(?,?,?,?)",([name,date,userid,albumid]))
          db.commit()
        cur.close()
        db.close()
      except :
        db.rollback()
        cur.close()
        db.close()
        print("failed to add photo")
        return("failed to add photo")
    except :
      print("failed to get db")
      return("failed to get db")

@app.route('/addphoto/<albumid>/')
def addphoto(albumid):
  print(albumid)
  return render_template('addphotos.html',albumid=albumid)

@sio.on("joinphoto",namespace="/viewphoto")
def jp(data):
    print("\n\n\n",data)
    sid=request.sid
    print(sid)
    ds=str(data)
    join_room(ds)
    print(rooms())
    print("joined")
    try:
      print("getting db")
      db=getdb(maindb)
      cur=db.cursor()
      print("got db")
      try:
        ###given photo id get photo and comments
        print("getting photo details")
        ph=cur.execute("select * from EventMedia where Id=(?)",([data])).fetchone()
        if not ph:
          print("no photo found")
          db.close()
          mydet={'Type':'NoData'}
          sio.emit("myphoto",mydet,room=request.sid,namespace="/viewphoto")
          db.close()
          return "error"
        else:
          print("got photo",ph)
          ##get name desc and date
          mydet={'Name':ph[1],'Desc':ph[2],'Date':ph[4],'Id':data,'Album':ph[5],'Type':'Update',"Flagged":ph[6],"Mimetype":ph[7]}
          #sio emit this
          sio.emit("myphoto",mydet,room=request.sid,namespace="/viewphoto")
          print("\n\n",mydet)
          try:
            print("getting photo comments",data)
            com=cur.execute("select * from Comments where GroupId=(?) order by Date desc",([data])).fetchall()
            if not com:
              print("no comments")
              mycom=""
              db.close()
              return
            else:
              print("got comments for",id)
              print(com)
              for c in com:
                ##get comment,date
                #emit this
                sd={"Comment":c[2],"Id":c[0],"Date":c[3],"Flagged":c[5],"Edited":c[6]}
                sio.emit("mycomment",sd,room=request.sid,namespace="/viewphoto")
                try:
                  print("getting commentor details",c[1])
                  userdp=cur.execute("select * from Account where Id=(?)",([c[1]])).fetchone()
                  if userdp:
                    mycom={'CommentId':c[0],'Date':c[3],'Username':userdp[1],'DP':userdp[3]}
                    #emit this
                    print("got user details",mycom)
                    sio.emit("commentor",mycom,room=request.sid,namespace="/viewphoto")
                  else:
                    pass
                except:
                  
                  print("unable to get user dp")
                  return ("unable to get user dp")
              #sio.join_room(id)
              print("joined room")
              db.close()
              return
          except:
            print("unable to get comments")
            return("unable to get comments")
      except:
        print("unable to get photo data")
        return("unable to get photo data")
    except:
      print("unable to get db and cur")
      return ("unable to get db and cur")

@app.route('/photov/<id>')
def photov(id):
  return render_template('view.html',id=id)

@app.route('/photo')
def photo():
  print(request.cookies)
  alldet=[]
  mydet={}
  if request.method=='GET':
    id=request.args.get("id")
    print("photo id",id)
    try:
      print("getting db")
      db=getdb(maindb)
      cur=db.cursor()
      print("got db")
      try:
        ###given photo id get photo and comments
        print("getting photo details")
        ph=cur.execute("select * from EventMedia where Id=(?)",([id])).fetchone()
        if not ph:
          print("no photo found")
          return "error"
        else:
          print("got photo",ph)
          ##get name desc and date
          mydet={'Name':ph[1],'Desc':ph[2],'Date':ph[4],'Id':id,'Album':ph[5]}
          try:
            print("getting photo comments",id)
            com=cur.execute("select * from Comments where GroupId=(?) order by Date desc",([ph[0]])).fetchall()
            if not com:
              print("no comments")
              mycom=""
            else:
              print("got comments for",id)
              print(com)
              for c in com:
                ##get comment,date
                mycom={}
                try:
                  print("getting commentor details",c[1])
                  userdp=cur.execute("select * from Users where Id=(?)",([c[1]])).fetchone()
                  ##get userdp
                  username=userdp[1]+" "+userdp[2]+" "+userdp[3]
                  mycom={'CommentId':c[0],'Comment':c[2],'Date':c[3],'UserId':userdp[0],'Username':username,'DP':userdp[9]}
                  alldet.append(mycom)
                  print("got user details",mycom)
                except:
                  print("unable to get user dp")
                  return ("unable to get user dp")
            print("all my detail",alldet)
            print("all my detail",mydet)
            #sio.join_room(id)
            print("joined room")
            return render_template('viewphoto.html',alldet=alldet,mydet=mydet)
          except:
            print("unable to get comments")
            return("unable to get comments")
      except:
        print("unable to get photo data")
        return("unable to get photo data")
    except:
      print("unable to get db and cur")
      return ("unable to get db and cur")

@app.route('/g')
def g():
  return render_template('gallery.html')

@app.route('/createalbum',methods=['GET'])
def createalbum():
  userid=108824877907
  event=""
  venue=''
  date=''
  if request.method=='GET':
    event=request.args.get('event')
    venue=request.args.get('venue')
    date=request.args.get('date')
    desc=request.args.get('desc')
    print(type(date))
    if not event or not venue or not date:
      print("missing data")
      return 'missing data'
    print("got album data",event,venue,date)
    try:
      print("getting db")
      db=getdb(maindb)
      cur=db.cursor()
      print("got db")
      try:
        print("adding album to db")
        createdon=datetime.now()
        print('data',event,venue,date,desc,createdon,userid)
        cur.execute("insert into Albums (Event,Venue,EventDate,Description,Date,UserId) values (?,?,?,?,?,?)",([event,venue,date,desc,createdon,userid]))
        db.commit()
        cur.close()
        db.close()
        print("added album to db")
        return redirect(url_for('gallery'))
      except :
        db.rollback()
        cur.close()
        db.close()
        print("failed to create album")
        return("failed to create album")
    except :
      print("failed to get db")
      return("failed to get db")


def getUser():
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      print("getting user")
      u=cur.execute("select * from Account").fetchone()
      if not u:
        print("no user in account")
        return False
      else:
        print("got user")
        us={'Id':u[0],'Name':u[1],'Email':u[2],'DP':u[3],'Role':u[4]} 
        session['User']=us
        return us    
    except:
      print("failed to get user")
      return False
  except:
    print("failed to get db")
    return False   


@app.route('/')
def gall():
  print("in home")
  s=getUser()
  print(s)
  if getUser():
    print("got session")
  else:
    print("session creation error")
  return render_template("galery.html")

@sio.on("connect",namespace="/gallery")
def gcon():
  print("connected")
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      print("getting albums")
      albums=cur.execute("select * from Albums").fetchall()
      if not albums:
        print("no albums")
        #sio.emit()
        return
      else:
        print("got albums")
        print(albums)
        for alb in albums:
          da={'Id':alb[0],'Event':alb[1],'Venue':alb[2],'EventDate':alb[3],'Desc':alb[4],'Date':alb[5],'Cover':alb[7]}
          #sio emit this
          sio.emit("newalbum",da,room=request.sid,namespace="/gallery")
        return
    except :
      print("failed to get albums")
      return ("failed to get albums")
  except :
    print("failed to get db and cursor")
    return ("failed to get db and cursor")

@app.route('/gallery')
def gallery():
  mydata=[]
  if request.method=='GET':
    try:
      print("getting db")
      db=getdb(maindb)
      cur=db.cursor()
      print("got db")
      try:
        print("getting albums")
        albums=cur.execute("select * from Albums").fetchall()
        if not albums:
          print("no albums")
        print("got albums")
        print(albums)
        for alb in albums:
          da={'Id':alb[0],'Event':alb[1],'Venue':alb[2],'EventDate':alb[3],'Desc':alb[4],'Date':alb[5],'Cover':alb[7]}
          print(da)
          mydata.append(da)
        print("my data",mydata)
        return render_template("Gallery.html",mydata=mydata)
      except :
        print("failed to get albums")
        return ("failed to get albums")
    except :
      print("failed to get db and cursor")
      return ("failed to get db and cursor")

@sio.on("albumcover",namespace="/listphotos")
def albumcover(data):
  print("got data",data)
  user=''
  if 'User' in session.keys():
    user=session['User']
  else:
    print("not in session")
    return
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      al=cur.execute("select * from Albums where Id=?",([data['Id']])).fetchone()
      if user['Role']=='Admin' and al:
        print("allowed to edit")
        if data['Type']=='Edit':
          ##give it a name
          n=data['Name']
          b=n.rindex('.')
          c=n[b:]
          print(c)
          k=str(int(random()*1000000))+c
          print(k)
          h="./static/Images/AlbumCovers/"+k
          print(h)
          fi=open(h,"wb+")
          print(fi)
          print("write data")
          fi.write(data['File'])
          fi.flush()
          fi.close()
          cur.execute("UPDATE Albums set Cover=? where Id=?",(k,data['Id']))
          db.commit()
          da={"File":k,
              "Id":data['Id']
              }
          sio.emit("albumcover",da,room=request.sid,namespace="/gallery")
          sio.emit("albumcover",da,room=request.sid,namespace="/listphotos")
          print("commited and emmited")
          db.close()
          return
        else:
          print(data['Type'])
          return
      else:
        print("not allowed")
        db.close()
        return
    except:
      print("unable to update")
      db.rollback()
      db.close()
      return
  except:
    print("db error")
    return

@sio.on("PhotoComment",namespace="/viewphoto")
def broadComment(comment):
  print(type(comment))
  e=comment
  print(rooms())
  user=session['User']
  comment['DP']=user['DP']
  #PhotoComment(data)
  userid=""
  Name=''
  print(comment)
  print("\n\nthis is my session user\n\n",session['User'])
  if session['User']:
    print("got usr")
    user=session['User']
    userid=user['Id']   
    Name=user['Name']
  else:
    return
  print(userid)
  #userid
  #type
  #comment
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    date=datetime.now()
    try:
      date=datetime.now()
      date=datetime.ctime(date)
      Date=date
      if comment["Type"]=='Create':
        print("got create")
        pis=int(random()*100000000)
        cur.execute("INSERT into Comments (Id,Comment,UserId,GroupId,Date) values(?,?,?,?,?)",([pis,comment['Comment'],userid,comment['PhotoId'],Date]))
        db.commit()
        print("after commit")
        comment['Date']=date
       # comment['Name']=Name
        comment['Id']=pis
        print(comment['PhotoId'])
        vs=int(comment['PhotoId'])
        print(rooms())
        print(comment)
        print("before emit")
       #  sio.emit("mycomment",sd,room=data,namespace="/viewphoto")
        r=str(comment['PhotoId'])
        print(r)
        print(rooms())
        print(request.namespace)
        for i in rooms():
         # print(rooms()[1])
        
          print(type(i))
          if i==r:
            print("got room")
        sio.emit("mycomment",comment,room=r,namespace="/viewphoto")
        mycom={'CommentId':pis,'Date':Date,'Username':Name,'DP':user['DP']}     
        print("b4 second")     
        sio.emit("commentor",mycom,room=r,namespace="/viewphoto")
        #print(room())
        print('created')
        db.close()
        return ''
      else:
        print("not create")
        print(comment)
        try:
          print("getting comment")
          print(comment['Id'])
          d=comment['Id']
          com=cur.execute("select * from Comments where Id=(?)",([d])).fetchone()
          if not com:
            print("comment not found")
            db.close()
            return
          else:
            print("comment found")
            print(com)
            print(session['User'])
            if com[1]==userid:
              if comment["Type"]=='Delete':
                print("got delete")
                cur.execute("DELETE from Comments where Id=?",([comment['Id']]))
                db.commit()
                print("deleted")
                comment['Date']=date
                comment['Name']=Name
                sio.emit("Removecomment",comment,room=com[0],namespace="/viewphoto")
                db.close()
                return
              elif comment["Type"]=='Edit':
                print("got edit")
                cur.execute("UPDATE  Comments set Comment=?,Date=? where Id=?",([comment['Comment'],date,comment['Id']]))
                db.commit()
                print("edited")
                comment['Date']=date
                comment['Name']=Name
                sio.emit("Editcomment",comment,room=com[0],namespace="/viewphoto")
                db.close()
                return
              elif comment["Type"]=='Flag':
                print("got flag")
                cur.execute("UPDATE Comments set Flag=? where Id=(?)",(['True',comment['Id']]))
                db.commit()
                print("flagged")
                comment['Date']=date
                comment['Name']=Name
                sio.emit("Flagcomment",comment,room=com[0],namespace="/viewphoto")
                db.close()
                return
              else:
                db.close()
                print("dont know what to change")
                return
            else:
              db.close()
              print("not the same user")
              return
          return
        except :
          db.close()
          print("unable to get message")
          return("unable to get message")
    except:
      db.rollback()
      db.close()
      print("unable to change")
      return("unable to change")
  except :
    print("unable to get db and cursor")
    return("unable to get db and cursor")

def PhotoComment(comment):
  #check if user in session
  userid=""
  Name=''
  print(comment)
  print("\n\nthis is my session user\n\n",session['User'])
  if session['User']:
    print("got usr")
    user=session['User']
    userid=user['Id']   
    Name=user['Name']
  else:
    return
  print(userid)
  #userid
  #type
  #comment
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    date=datetime.now()
    try:
      date=datetime.now()
      date=datetime.ctime(date)
      Date=date
      if comment["Type"]=='Create':
        print("got create")
        pis=int(random()*100000000)
        cur.execute("INSERT into Comments (Id,Comment,UserId,GroupId,Date) values(?,?,?,?,?)",([pis,comment['Comment'],userid,comment['PhotoId'],Date]))
        db.commit()
        print("after commit")
        comment['Date']=date
        comment['Name']=Name
        comment['Id']=pis
        print(comment['PhotoId'])
        vs=comment['PhotoId']
        print(rooms())
        print(comment)
        print("before emit")
        sio.emit("mycomment",comment,namespace="/viewphoto")
        print(room())
        print('created')
        db.close()
        return ''
      else:
        print("not create")
        print(comment)
        try:
          print("getting comment")
          print(comment['Id'])
          d=comment['Id']
          com=cur.execute("select * from Comments where Id=(?)",([d])).fetchone()
          if not com:
            print("comment not found")
            db.close()
            return
          else:
            print("comment found")
            print(com)
            print(session['User'])
            if com[1]==userid:
              if comment["Type"]=='Delete':
                print("got delete")
                cur.execute("DELETE from Comments where Id=?",([comment['Id']]))
                db.commit()
                print("deleted")
                comment['Date']=date
                comment['Name']=Name
                sio.emit("Removecomment",comment,room=com[0],namespace="/viewphoto")
                db.close()
                return
              elif comment["Type"]=='Edit':
                print("got edit")
                cur.execute("UPDATE  Comments set Comment=?,Date=? where Id=?",([comment['Comment'],date,comment['Id']]))
                db.commit()
                print("edited")
                comment['Date']=date
                comment['Name']=Name
                sio.emit("Editcomment",comment,room=com[0],namespace="/viewphoto")
                db.close()
                return
              elif comment["Type"]=='Flag':
                print("got flag")
                cur.execute("UPDATE Comments set Flag=? where Id=(?)",(['True',comment['Id']]))
                db.commit()
                print("flagged")
                comment['Date']=date
                comment['Name']=Name
                sio.emit("Flagcomment",comment,room=com[0],namespace="/viewphoto")
                db.close()
                return
              else:
                db.close()
                print("dont know what to change")
                return
            else:
              db.close()
              print("not the same user")
              return
          return
        except :
          db.close()
          print("unable to get message")
          return("unable to get message")
    except:
      db.rollback()
      db.close()
      print("unable to change")
      return("unable to change")
  except :
    print("unable to get db and cursor")
    return("unable to get db and cursor")


@sio.on("editdesc",namespace="/view")
def editdesc(data):
  print(data)
  print("got data")
  ####get photo from db
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got db and cursor")

    try:
      print("getting photo")
      pi=cur.execute("select * from Photos where Id=?",([data['Id']])).fetchone()
      if not pi:
        print("failed to get pic with this Id")
        return
      else:
        print("got photo using id")
        print(pi)
        try:
          cur.execute("UPDATE EventPhotos set Description=? where Id=?",([data['Desc'],data['Id']]))
          db.commit()
          sio.emit()
          cur.close()
          db.close()
          return
        except:
          print("failed to update desc")
          db.rollback()
          cur.close()
          db.close()
          return
    except:
      print("did not get pic ")
      cur.close()
      db.close()
      return
  except:
    print("failed to get db and cursor")
    return

@sio.on("managealbums",namespace="/gallery")
def manage(data):
  user=session['User']
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      if data['Type']=='Create':
        print("got create")
        date=datetime.ctime(datetime.now())
        #check if allowed to add
        aid=int(random()*100000000)
        cur.execute("insert into Albums (Id,Event,Venue,EventDate,Description,Date,UserId) values (?,?,?,?,?,?,?)",([aid,data['Event'],data['Venue'],data['Date'],data['Desc'],date,user['Id']]))
        db.commit()
        cur.close()
        db.close()
        print("added album to db")
        data['Id']=aid
        sio.emit("newalbum",data,namespace="/gallery")
        print("emited")
        return
      else:
        db.close()
        print("npt here")
        return
    except:
      db.rollback()
      db.close()
      print("failed to create")
      return
  except:
    print("db error")
    return

@sio.on("managealbum",namespace = "/listphotos")
def managealbum(data):
  print(data)
  user=''
  if 'User' in session.keys():
    user=session['User']
  try:
    print("getting db and cur")
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      print("getting album")
      date=datetime.ctime(datetime.now())
      al=cur.execute("select * from Albums where Id=?",([data['Id']])).fetchone()
      if not al:
        print('album not found')     
        db.close()
        return
      else:
        print("got album")
        print(al)
        if user["Role"]=='Admin':
          if data['Type']=='Edit':
            print("got edit")
            cur.execute("UPDATE Albums set Event=?,Venue=?,EventDate=?,Description=? where Id=?",([data['Event'],data['Venue'],data['Date'],data['Desc'],data['Id']]))
            db.commit()
            print("added to db")
            cur.close()
            db.close()
            ####remember rooms album id for listphotos
            data['Type']='Update'
            sio.emit("managealbum",data,namespace="/listphotos")
            sio.emit("managealbum",data,namespace="/gallery")
            print("emited")
            return
          elif data['Type']=="Delete":
            print("got delete")
            cur.execute("DELETE  from EventMedia where AlbumId=?",([data['Id']]))
            print("deleted all photos in album")
            cur.execute("DELETE  from Albums where Id=?",([data['Id']]))
            print("deleted album")
            db.commit()
            db.close()
            print("emitting")
            sio.emit("managealbum",data,namespace="/listphotos")
            sio.emit("managealbum",data,namespace="/gallery")
            print("emited")
            return
          elif data['Type']=='Flag':
            print("got flag")
            cur.execute("UPDATE Albums set Flagged=? where Id=?",(['True',data['Id']]))
            db.commit()
            print("album flagged")
            cur.close()
            db.close()
            data.pop('Reason')
            ####remember rooms album id for listphotos
            print("emitting")
            sio.emit("managealbum",data,namespace="/listphotos")
            sio.emit("managealbum",data,namespace="/gallery")
            print("emited")
            return
          else:
            print("unkown type command")
            db.close()
            return
        else:
          print("not allowed to add album")
          db.close()
          return
    except:
      db.rollback()
      db.close()
      print("unable to manage")
      return
  except:
     print("failed to get db")
     return

@app.route('/editAlbum/',methods=['GET'])
def editAlbum():

  if request.method=='GET':
    albumid=request.args.get('albumid')
    event=request.args.get('event')
    venue=request.args.get('venue')
    eventdate=request.args.get('eventdate')
    desc=request.args.get('desc')
    if event=="" or venue=="" or eventdate=="":
      print("missing data")
      return("missing data")
    print("got data",albumid,event,venue,eventdate,desc)
    try:
      print("getting db")
      db=getdb(maindb)
      cur=db.cursor()
      print("got db")
      try:
        ###add to db
        print("adding to db")
        cur.execute("UPDATE Albums set Event=?,Venue=?,EventDate=?,Description=? where Id=?",(event,venue,eventdate,desc,albumid))
        db.commit()
        print("added to db")
        cur.close()
        db.close()
        ###sio emit data
        return redirect(url_for('preview',id=albumid))
      except :
        db.rollback()
        cur.close()
        db.close()
        print("failed to add to db")

        return("failed to add to db")
    except:
      print("failed to get to db")
      return("failed to get to db")
