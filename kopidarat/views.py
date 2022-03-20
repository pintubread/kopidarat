# Django imports 
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.db import connection, IntegrityError
from django.urls import reverse
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.template import loader

# Custom imports 
import datetime

# View Functions 
def index(request):
    '''
    Index view function responsible for the main page of the website.
    Takes in the request and returns the rendering of the main page.

    NOTE: The function for joining events is refactored out for better code clarity. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the main page (path: '') 
    '''
    # Get the current_user username and email, need to fix the login part to proceed 
    current_user = request.session.get("username", False)
    user_email = request.session.get("email", False)

    # Get all activities data from the database
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM activity WHERE %s < start_date_time ORDER BY start_date_time ASC', [datetime.datetime.now()])
        activities = cursor.fetchall()
    
    # Put all the records inside the dictionary context
    context = {'records' : activities}

    return render(request,"index.html", context)

def create_activity(request):
    '''
    create_activity view function responsible for the creating activity html page.
    Takes in the request and returns the rendering of the create_activity page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the create_activity page (path: '/create_activity')
    '''
    if request.method == 'POST': # TODO: catch error when there's no post method, e.g. cancel to create activity

        with connection.cursor() as cursor:

            # For now the email is still hard-coded, need to fix the login part first to proceed
            cursor.execute('INSERT INTO activity (inviter,activity_name,category,start_date_time,venue,capacity) VALUES (%s,%s,%s,%s,%s,%s)', [
                request.session.get("email",'aodowd0@auda.org.au'),request.POST['activity_name'],request.POST['category'], request.POST['start_date_time'],
                request.POST['venue'],request.POST['capacity']
            ])

            # Get the activity details, could be improved for later
            cursor.execute('SELECT activity_id FROM activity WHERE inviter =  %s AND activity_name = %s AND category = %s AND start_date_time = %s AND venue = %s AND capacity = %s',[
                request.session.get("email",'aodowd0@auda.org.au'),request.POST['activity_name'],request.POST['category'], request.POST['start_date_time'],
                request.POST['venue'],request.POST['capacity']
            ])
            activity_id = cursor.fetchone()

            # Joining the current user to the joins database
            cursor.execute('INSERT INTO joins VALUES (%s,%s)',[
                activity_id,request.session.get("email",'aodowd0@auda.org.au')
            ])

    return render(request, 'create_activity.html')

def join(request,activity_id):
    '''
    join view function that is responsible for the joining button on the main page.
    Takes in the request and the activity_id of the event and executes an SQL statement 
    to insert the user values to the joins table. Returns an http response redirect function.
    Argument:
        request: HTTP request
        activity_id: the activity_id of the associated event
    Return:
        HTTP response redirect to the main page. 
    '''
    with connection.cursor() as cursor:

        # The email here is still hardcoded, need to fix the login part first to proceed 
        cursor.execute('INSERT INTO joins VALUES (%s,%s)',[
            activity_id,request.session.get("email",'aodowd0@auda.org.au')
        ])

    return HttpResponseRedirect(reverse("index"))

def user_activity(request):
    '''
    user_activity view function that is responsible for the user_activity page.
    Takes in the request and the username of the user and returns the rendering 
    of the user_activity page. 
    Argument:
        request: HTTP request
    Return: 
        render function: renders the user_activity page (path: /user_activity)
    '''
    # need a dictionary to store some of the information that is needed to be passed to the html pages 
    context = dict()

    with connection.cursor() as cursor:
        
        # Get the name of the user, need to fix the login part first to proceed 
        cursor.execute('SELECT full_name FROM users WHERE email = %s',[
            request.session.get('email','aodowd0@auda.org.au')
        ])
        user_fullname = cursor.fetchone()

        # Get the table of activities where the current user is the inviter, need to fix the login part first to proceed 
        cursor.execute('SELECT * FROM activity WHERE inviter = %s',[
            request.session.get('email','aodowd0@auda.org.au')
        ])
        inviter_list = cursor.fetchall()

        # Get the table of activities where the user has joined in, need to fix the login part first to proceed 
        cursor.execute('SELECT a.activity_id, a.inviter, a.category, a.activity_name, a.start_date_time, a.venue FROM joins j, activity a WHERE j.activity_id = a.activity_id AND j.participant = %s', [
            request.session.get('email','aodowd0@auda.org.au')
        ])
        joined_activities_list = cursor.fetchall()

    context['user_fullname'] = user_fullname
    context['inviter_list'] = inviter_list
    context['joined_activities_list'] = joined_activities_list

    return render(request,'user_activity.html',context)

def update_activity(request,activity_id):
    
    if request.method == 'POST': # TODO: catch error when there's no post method, e.g. cancel to create activity
        with connection.cursor() as cursor:

            # Execute SQL query to update the values for the particular instance
            cursor.execute('UPDATE activity SET activity_name = %s, category = %s, start_date_time = %s, venue = %s, capacity = %s WHERE activity_id = %s', [
                request.POST['activity_name'],request.POST['category'],request.POST['start_date_time'],request.POST['venue'], request.POST['capacity'],activity_id
            ])

    return render(request, 'update_activity.html')
        
def delete_activity(request,activity_id):
    
    with connection.cursor() as cursor:

        # Execute SQL query to delete the user from joining the activity, need to fix the login part to proceed 
        cursor.execute('DELETE FROM joins WHERE activity_id = %s AND participant = %s', [
            activity_id, request.session.get('email','aodowd0@auda.org.au')
        ])
    
    return HttpResponseRedirect(reverse("user_activity"))


def create_review(request):
    if request.method =='POST':

        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO review VALUES (%s,%s,%s,%s)', [
                request.POST['activity_id'],datetime.datetime.now(),request.POST['participant'],
                request.POST['comment']
            ])

    return render(request, 'review.html')

def create_report(request):
    if request.method =='POST':
        
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO report VALUES (%s,%s,%s,%s,%s)', [
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

            # Get the email for the key for the other tables and other operations 
            with connection.cursor() as cursor:
                cursor.execute('SELECT email FROM user WHERE username = %s', request.session.get("username"))
                user_email = cursor.fetchone()
                request.session['email'] = user_email

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

    
    

