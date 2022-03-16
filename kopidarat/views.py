from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.db import connection, IntegrityError
from django.urls import reverse
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.template import loader

import datetime

# Create your views here.
def index(request):
    # return render(request,"index.html")
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM activity WHERE %s < start_date_time ORDER BY start_date_time ASC', [datetime.datetime.now()])
        activities = cursor.fetchall()
    
    results = {'records' : activities}

    return render(request,"index.html", results)

def create_activity(request):
    if request.method == 'POST':

        with connection.cursor() as cursor:

            cursor.execute('INSERT INTO activity(inviter,activity_name,category,start_date_time,venue,capacity) VALUES (%s %s %s %s %s %s)', [
                request.POST['inviter'],request.POST['activity_name'],request.POST['category'], request.POST['start_date_time'],
                request.POST['venue'],request.POST['capacity']
            ])

            # Insert inviter into table 'joins' as participant, not sure of how to insert the activity_id
            #
            # cursor.execute('INSERT INTO joins(activity_id,participant) VALUES (%s %s)', [
            #   request.POST['...'], request.POST['inviter']
            # ])
            #

    return render(request, 'create_activity.html')

def create_review(request):
    if request.method =='POST':

        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO review VALUES (%s %s %s %s)', [
                request.POST['activity_id'],datetime.datetime.now(),request.POST['participant'],
                request.POST['comment']
            ])

    return render(request, 'review.html')

def create_report(request):
    if request.method =='POST':
        
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO report VALUES (%s %s %s %s %s)', [
                request.POST['submitter'],datetime.datetime.now(),request.POST['user'],
                request.POST['comment'],request.POST['severity']
            ])

    return render(request,'report.html')


def login_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("index"))
    if request.method == "POST":
        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        # Check if authentication successful
        if user is not None:
            login(request, user)
            request.session["username"] = username
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "login.html")


def logout_view(request):
    logout(request)
    if "username" in request.session:
        del request.session["username"]
    return HttpResponseRedirect(reverse("index"))


def register(request):
    context={}
    status=''

    if request.method == "POST":
        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "register.html", {
                "message": "Passwords must match."
            })
        # Attempt to create new user
        # to do: modify that it directly inserts new user to database

        ## Check if customerid is already in the table
        with connection.cursor() as cursor:

            cursor.execute("SELECT * FROM user WHERE email = %s", [request.POST['email']])
            user = cursor.fetchone()

            ## No user with same email
            if user == None:
                cursor.execute("SELECT * FROM user WHERE username = %s",[request.POST['username']])
                user = cursor.fetchone()

                if user == None:
                    cursor.execute("INSERT INTO user VALUES (%s, %s, %s, %s, 'Member')"
                            , [request.POST['full_name'], request.POST['username'], request.POST['email'],
                            request.POST['password']])
                    cursor.execute("INSERT INTO member VALUES %s", [request.POST['email']])
                    return redirect('index')
                else:
                    status = 'Customer with username %s already exists' % (request.POST['username'])    
            else:
                status = 'Customer with email %s already exists' % (request.POST['email'])    
    context['status'] = status
    return render(request, "register.html", context)

def forget_password(request):
    if request.method == "POST":
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM user WHERE email = %s", [request.POST['email']])
            user_fullname = cursor.fetchone()
            if user_fullname == None:
                return render(request, "forget_password.html", 
                {"message": "The given email is not registered under any account."})
            else:
                html_message = loader.render_to_string('reset_password_email.html',
                {'full_name': user_fullname})
                send_mail(subject="KopiDarat Account Password Reset",
                message="Looks like you've forgotten your KopiDarat password! To reset your password, follow the link below:",
                recipient_list=[request.post['email'],],
                fail_silently=False, html_message=html_message)
                return render(request,"reset_password_email_sent.html")
    return render(request,"forget_password.html")






def reset_password(request):
    if request.method == "POST":
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "reset_password.html", {
                "message": "Passwords must match."
            })
        
        with connection.cursor() as cursor:
            cursor.execute("UPDATE user SET password=%s WHERE email=%s",[request.POST['password'],request.user.email])
            return render(request,"reset_password_successful.html")
    return render(request,"reset_password.html")

    
    

