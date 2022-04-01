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
        cursor.execute('SELECT * FROM activity WHERE %s < end_date_time ORDER BY start_date_time ASC', [datetime.datetime.now()])
        activities = cursor.fetchall()
    
    results = {'records' : activities}

    return render(request,"index.html", results)

def create_activity(request):
<<<<<<< Updated upstream
    if request.method == 'POST':
=======
    '''
    create_activity view function responsible for the creating activity html page.
    Takes in the request and returns the rendering of the create_activity page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the create_activity page (path: '/create_activity')
    '''
    # Check if user is logged in
    user_email = request.session.get("email", False)

    if user_email is not False:
        context = {}
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM category')
            categories = cursor.fetchall()
            context["categories"] = categories

        if request.method == 'POST':

            with connection.cursor() as cursor:
                cursor.execute('CALL create_new_activity(%s,%s,%s,%s,%s,%s)',[
                    user_email,request.POST['category'],request.POST['activity_name'],request.POST['start_date_time'],request.POST['venue'], request.POST['capacity']])
                return HttpResponseRedirect(reverse("user_activity"))
        else:
            return render(request, 'create_activity.html', context)
    return HttpResponseRedirect(reverse("index"))


def join(request, activity_id):
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
    user_email = request.session.get("email", False)
    message = ''

    if user_email is not False:

        with connection.cursor() as cursor:
            try:
                cursor.execute('INSERT INTO joins VALUES (%s,%s)', [
                                activity_id, user_email])
            except IntegrityError:
                message='You have registered for this activity.'
            except Exception:
                message='We regret to inform you that the activity has reached its maximum capacity.'
            
    return index(request,message)


def user_activity(request):
    '''
    user_activity view function that is responsible for the user_activity page.
    Takes in the request and the username of the user and returns the rendering 
    of the user_activity page. 

    # NOTE: the function for deleting and updating events is refactored out for better code clarity. 
    Argument:
        request: HTTP request
    Return: 
        render function: renders the user_activity page
    '''
    user_email = request.session.get("email", False)

    if user_email is not False:

        # need a dictionary to store some of the information that is needed to be passed to the html pages
        context = dict()

        with connection.cursor() as cursor:

            # Get the table of past activities where the current user is the inviter
            cursor.execute('SELECT * FROM activity a, users u WHERE a.inviter = u.email AND a.inviter = %s AND a.start_date_time < NOW() ORDER BY a.start_date_time ASC', [
                user_email
            ])
            past_inviter_list = cursor.fetchall()

            # Get the table of upcoming activities where the current user is the inviter
            cursor.execute('SELECT * FROM activity a, users u WHERE a.inviter = u.email AND a.inviter = %s AND a.start_date_time > NOW() ORDER BY a.start_date_time ASC', [
                user_email
            ])
            inviter_list = cursor.fetchall()

            # Get the table of upcoming activities created by other user where the user has signed up for
            cursor.execute('SELECT a.activity_id, u.full_name, a.category, a.activity_name, a.start_date_time, a.venue FROM joins j, activity a, users u WHERE j.activity_id = a.activity_id AND a.inviter = u.email AND a.inviter <> j.participant AND j.participant = %s AND NOW() <= a.start_date_time ORDER BY a.start_date_time ASC', [
                user_email
            ])
            upcoming_activities_list = cursor.fetchall()

            # Get the table of past activities created by other user where the user has joined
            cursor.execute('SELECT a.activity_id, u.full_name, a.category, a.activity_name, a.start_date_time, a.venue FROM joins j, activity a, users u WHERE j.activity_id = a.activity_id AND a.inviter = u.email AND a.inviter <> j.participant AND j.participant = %s AND NOW() > a.start_date_time ORDER BY a.start_date_time ASC', [
                user_email
            ])
            joined_activities_list = cursor.fetchall()

            # Get table of reviews that user has created
            cursor.execute('SELECT a.activity_id, r.timestamp, r.comment FROM review r, activity a, users u WHERE r.activity_id = a.activity_id AND r.participant = u.email AND r.participant = %s ORDER BY a.start_date_time ASC', [
                user_email
            ])
            reviews_list = cursor.fetchall()

            # Get table of reviews that user has created
            cursor.execute('SELECT r.timestamp, r.report_user, r.comment, r.severity FROM report r, users u WHERE r.report_user = u.email AND r.submitter = %s ORDER BY r.timestamp ASC', [
                user_email
            ])
            reports_list = cursor.fetchall()

        context['user_fullname'] = request.session.get('full_name')
        context['past_inviter_list'] = past_inviter_list
        context['inviter_list'] = inviter_list
        context['upcoming_activities_list'] = upcoming_activities_list
        context['joined_activities_list'] = joined_activities_list
        context['reviews_list'] = reviews_list
        context['reports_list'] = reports_list

        return render(request, 'user_activity.html', context)

    else:
        return HttpResponseRedirect(reverse("index"))


def update_activity(request, activity_id):
    '''
    update_activity view function responsible for the update activity page.
    Takes in the request and activity_id of the event and returns a render function
    that renders the update_activity page. Executes SQL statement to update the values
    inside the activity table.
    Argument:
        request: HTTP request
        activity_id: the activity id of the event
    Return: 
        render function: renders the update activity page (path: /update_activity)
    '''
    user_email = request.session.get("email", False)
    context={}

    if user_email is not False:

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM activity WHERE activity_id=%s', [activity_id])
            this_activity = cursor.fetchone()

        if request.method == 'POST':  # TODO: catch error when there's no post method, e.g. cancel to create activity
            with connection.cursor() as cursor:

                # Execute SQL query to update the values for the particular instance
                cursor.execute('UPDATE activity SET activity_name = %s, category = %s, start_date_time = %s, venue = %s, capacity = %s WHERE activity_id = %s', [
                    request.POST['activity_name'], request.POST['category'], request.POST[
                        'start_date_time'], request.POST['venue'], request.POST['capacity'], activity_id
                ])
                cursor.execute('SELECT * FROM activity WHERE activity_id=%s', [activity_id])
                this_activity = cursor.fetchone()
            return HttpResponseRedirect(reverse("user_activity"))

        context['this_activity'] = this_activity
        return render(request,'admin_activity_edit.html',context)

    return HttpResponseRedirect(reverse("index"))
>>>>>>> Stashed changes

        with connection.cursor() as cursor:

            cursor.execute('INSERT INTO activity VALUES (%s %s %s %s %s %s %s)', 
            [ request.POST['inviter'],request.POST['category'],request.POST['activity_name'], request.POST['start_date_time'],
            request.POST['end_date_time'], request.POST['venue'],request.POST['capacity']])

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

    
    

