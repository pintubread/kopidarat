# Django imports 
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.db import connection, IntegrityError
from django.urls import reverse
from django.core.mail import send_mail
from django.template import loader

# Custom imports 
import datetime

# View Functions for main pages for the member's side of the website 
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
    # Checking if user is logged in
    user_email = request.session.get("email", False)

    if user_email is not False:
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM category')
            categories = cursor.fetchall()

        all_activities_sql = "SELECT a.activity_id, u.full_name as inviter, a.category, a.activity_name, a.start_date_time, a.venue, a.capacity FROM activity a, users u WHERE a.inviter = u.email AND a.start_date_time>NOW()"
        ordering_sql =  " ORDER BY a.start_date_time ASC"

        # filtering method
        if request.method == "POST":
            # Filtering the categories
            list_of_categories = request.POST.getlist('categories') # list of categories that are selected for filter
            category_filters = ""
            #Check if any category is chosen
            if len(list_of_categories)>0:
                for category in list_of_categories:
                    category_filters+= " OR a.category=" + "'" + category + "'"# starting OR deleted, the rest for combining the categories 

                category_filter_sql = " AND (" + category_filters[3:] + ")" # starts from 3 because to delete the starting 'OR'

            # Filtering the time selection
            list_of_time_filters = request.POST.getlist('display_period')
            time_filter_sql=""
            #Check if any time filter is chosen
            if len(list_of_time_filters)>0:
                print(len(list_of_time_filters))
                display_period = list_of_time_filters[0].split('_') # Need the values in HTML to be split with underscore
                duration,unit = int(display_period[0]),display_period[1]

                time_filter_sql = " AND %s < %s "

                if unit == 'week':
                    limit_time = (datetime.datetime.now()) + datetime.timedelta(weeks=duration)
                elif unit == 'month':
                    limit_time = (datetime.datetime.now()) + datetime.timedelta(month=duration)
            
            with connection.cursor() as cursor:
                cursor.execute(all_activities_sql + category_filter_sql + time_filter_sql + ordering_sql, [ datetime.datetime.now(),datetime.datetime.now(),limit_time])
                activities = cursor.fetchall()

        # Get all activities data from the database
        else:
            with connection.cursor() as cursor:
                cursor.execute(all_activities_sql+ordering_sql)
                activities = cursor.fetchall()

        # Put all the records inside the dictionary context
        context = {'records' : activities,'full_name':request.session.get("full_name"),'categories':categories}

        return render(request,"index.html", context)
    else:
        return HttpResponseRedirect(reverse("frontpage"))

def create_activity(request):
    '''
    create_activity view function responsible for the creating activity html page.
    Takes in the request and returns the rendering of the create_activity page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the create_activity page (path: '/create_activity')
    '''
    #Check if user is logged in
    user_email = request.session.get("email", False)

    if user_email is not False:
        context={}
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM category')
            categories = cursor.fetchall()
            context["categories"]=categories

        if request.method == 'POST': 

            with connection.cursor() as cursor:

                # Insert the activity into the database
                cursor.execute('INSERT INTO activity (inviter,activity_name,category,start_date_time,venue,capacity) VALUES (%s,%s,%s,%s,%s,%s)', [
                    request.session.get("email"),request.POST['activity_name'],request.POST['category'], request.POST['start_date_time'],
                    request.POST['venue'],request.POST['capacity']
                ])

                # Get the activity details
                cursor.execute('SELECT activity_id FROM activity WHERE inviter =  %s AND activity_name = %s AND category = %s AND start_date_time = %s AND venue = %s AND capacity = %s',[
                    request.session.get("email"),request.POST['activity_name'],request.POST['category'], request.POST['start_date_time'],
                    request.POST['venue'],request.POST['capacity']
                ])
                activity_id = cursor.fetchone()

                # Joining the current user to the joins database
                cursor.execute('INSERT INTO joins VALUES (%s,%s)',[
                    activity_id,request.session.get("email")
                ])
                return HttpResponseRedirect(reverse("user_activity"))
        else:
            return render(request, 'create_activity.html',context)
    return HttpResponseRedirect(reverse("index"))

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
    user_email = request.session.get("email", False)
    message = ''

    if user_email is not False:

        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM joins WHERE activity_id=%s AND participant=%s',[
                activity_id,user_email
            ])
            joined = cursor.fetchone()

            if joined is not None:
                message = "You have joined this activity"
            else:
                cursor.execute('INSERT INTO joins VALUES (%s,%s)',[
                activity_id,user_email
                ])
    return HttpResponseRedirect(reverse("index"),{"message": message})


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
            
            # Get the table of activities where the current user is the inviter
            cursor.execute('SELECT * FROM activity a, users u WHERE a.inviter = u.email AND a.inviter = %s ORDER BY a.start_date_time ASC',[
                user_email
            ])
            inviter_list = cursor.fetchall()

            # Get the table of activities where the user has joined in
            cursor.execute('SELECT a.activity_id, u.full_name, a.category, a.activity_name, a.start_date_time, a.venue FROM joins j, activity a, users u WHERE j.activity_id = a.activity_id AND a.inviter = u.email AND j.participant = %s ORDER BY a.start_date_time ASC', [
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
        context['inviter_list'] = inviter_list
        context['joined_activities_list'] = joined_activities_list
        context['reviews_list'] = reviews_list
        context['reports_list'] = reports_list

        return render(request,'user_activity.html',context)

    else:
        return HttpResponseRedirect(reverse("index"))

def update_activity(request,activity_id):
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

    if user_email is not False:
        if request.method == 'POST': # TODO: catch error when there's no post method, e.g. cancel to create activity
            with connection.cursor() as cursor:

                # Execute SQL query to update the values for the particular instance
                cursor.execute('UPDATE activity SET activity_name = %s, category = %s, start_date_time = %s, venue = %s, capacity = %s WHERE activity_id = %s', [
                    request.POST['activity_name'],request.POST['category'],request.POST['start_date_time'],request.POST['venue'], request.POST['capacity'],activity_id
                ])
            return HttpResponseRedirect(reverse("user_activity"))

        else:
            return render(request, 'update_activity.html')

    return HttpResponseRedirect(reverse("index"))

def delete_activity(request,activity_id):
    '''
    delete_activity view function which is responsible for the delete button 
    in the user_activity page. Takes in the request and activity_id of the event
    and executes a SQL statement to delete the activity from the user's display.
    Argument: 
        request: HTTP request
        activity_id: the activity_id of the event
    Return:
        HTTP Response Redirect to the main page
    '''
    user_email = request.session.get("email", False)

    if user_email is not False:
        with connection.cursor() as cursor:

            # Execute SQL query to delete the user from joining the activity
            cursor.execute('DELETE FROM joins WHERE activity_id = %s AND participant = %s', [
                activity_id, request.session.get('email')
            ])
        return HttpResponseRedirect(reverse("user_activity"))
    else:
        return HttpResponseRedirect(reverse("index"))

def participants(request,activity_id):
    """ 
    View function that enables people who have signed up in the activity to view everyone else who signed up.
    Takes in the request and activity_id of the event and returns a render function that renders the 
    participants page. 
    Arguments:
        request: HTTP request
        activity_id: activity_id of the event
    Return:
        render function: render the participants page (path: /participants/<activity_id>)
    """
    # context dicitonary to store the values 
    context={}
    user_email = request.session.get("email", False)

    if user_email is not False:

        with connection.cursor() as cursor:
            # Execute SQL query to check if user is registered under this activity
            cursor.execute('SELECT * FROM joins WHERE activity_id=%s AND participant=%s', [
                activity_id, user_email
            ])
            user=cursor.fetchone()

        if user is not None:
            cursor.execute('SELECT u.full_name, u.email, u.phone_number FROM users u, joins j WHERE j.activity_id=%s AND u.email=j.participant AND u.email<>%s',
            [int(activity_id),user_email])
            participants=cursor.fetchall()

            cursor.execute('SELECT a.activity_name,a.inviter FROM activity a WHERE a.activity_id=%s',[activity_id])
            activity_name,inviter = cursor.fetchone()

            context["participants"] = participants
            context["activity_name"] = activity_name
            context["inviter"] = inviter
            return render(request,'participants.html',context)
        else:
            return HttpResponseRedirect(reverse("user_activity"))

    # TODO:to add additional message saying user is not registered for the activity        
    return HttpResponseRedirect(reverse("index"))

def create_review(request):
    '''
    create_review view function which is responsible for the creating review page.
    Takes in the request and returns a render function to render the review page.
    Argument: 
        request: HTTP request
    Return: 
        render function: renders the review page (path: /create_review)
    '''
    user_email = request.session.get("email", False)
    message=""
    if user_email is not False:

        if request.method =='POST':

            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM joins WHERE activity_id=%s AND participant=%s', [
                request.POST['activity_id'], user_email
            ])
                joined = cursor.fetchone()
                if joined is not None:
                    cursor.execute('SELECT * FROM activity WHERE activity_id=%s AND start_date_time<now()', [
                    request.POST['activity_id']])
                    happened = cursor.fetchone()
                    if happened is not None: 
                        cursor.execute('INSERT INTO review VALUES (%s,%s,%s,%s)', [
                            request.POST['activity_id'],datetime.datetime.now(),user_email,
                            request.POST['comment']
                        ])
                    else:
                        message = "The activity has yet to take place, hence you cannot give a review."
                else:
                    message="You are unable to give a review -- either the activity id does not exist, or you were never registered for the activity"

        return render(request, 'review.html',{"message":message})
    else:
        return HttpResponseRedirect(reverse("index"))

def create_report(request):
    '''
    create_report view function which is responsible for the reports page.
    Takes in the request and returns a render function to render the reports page.
    Argument: 
        request: HTTP request
    Return:
        render function: renders the reports page (path: /create_report)
    '''
    user_email = request.session.get("email", False)
    message=""

    if user_email is not False:
        if request.method =='POST':
            
            with connection.cursor() as cursor:
                cursor.execute('SELECT email FROM users WHERE username = %s ',[
                    request.POST['username']
                ])
                email = cursor.fetchone()
                if email is not None:
                    cursor.execute('INSERT INTO report VALUES (%s,%s,%s,%s,%s)', [
                        user_email,datetime.datetime.now(),email,
                        request.POST['comment'],request.POST['severity']
                    ])
                else:
                    message="Username does not exist. Please try again."
        return render(request,'report.html',{"message":message})
    else:
        return HttpResponseRedirect(reverse("index"))

# View functions for the admin side of the website 
def admin_index(request):
    '''
    index_admin view function that is responsible for the rendering of the administrator's page.
    Takes in a request and returns the rendering of the administrator's page.
    Argument:
        request: HTTP request
    Return:
        render function: renders the administrator's main page (path: /admin_index)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        # dictionary to store all the values
        context = dict()

        with connection.cursor() as cursor:

            # Select the top 5 most active users (identified by usernames) based on the number of activities joined
            cursor.execute('SELECT u.username, COUNT(j.participant) AS total_join FROM users u, joins j WHERE u.email = j.participant GROUP BY u.username ORDER BY total_join DESC ,u.username ASC LIMIT 5')
            list_of_active_users = cursor.fetchall()

            # Select the top 5 most inactive users (identified by usernames) based on the number of activities joined
            cursor.execute('SELECT u.username, COUNT(j.participant) AS total_join FROM users u, joins j WHERE u.email = j.participant GROUP BY u.username ORDER BY total_join ASC ,u.username ASC LIMIT 5')
            list_of_inactive_users = cursor.fetchall()

            # Select the top 5 activities with the most reviews, by counting the number of reviews 
            cursor.execute('SELECT a.activity_id,a.activity_name, COUNT(r.comment) AS total_reviews FROM activity a, review r WHERE a.activity_id = r.activity_id GROUP BY a.activity_id, a.activity_name ORDER BY total_reviews DESC, a.activity_id ASC LIMIT 5')
            list_of_reviewed_activities = cursor.fetchall()

            # Select the 5 most reported users (counted if the severity is medium or high only)
            cursor.execute("SELECT u.username, COUNT(r.comment) AS total_reports FROM users u, report r WHERE u.email = r.report_user AND (r.severity = 'medium' OR r.severity = 'high') GROUP BY u.username ORDER BY total_reports DESC, u.username ASC LIMIT 5")
            list_of_user_reports = cursor.fetchall()

        context = {
            'list_of_active_users' : list_of_active_users,
            'list_of_inactive_users' : list_of_inactive_users,
            'list_of_reviewed_activities' : list_of_reviewed_activities,
            'list_of_user_reports' : list_of_user_reports
        }
        return render(request, 'admin_index.html', context)
    else:
        return HttpResponseRedirect(reverse('login'))

def admin_user(request):
    '''
    user_admin view function responsible for the list of users page from the admin side.
    Takes in the request and returns the rendering of the admin_user page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_user page (path: /admin_user)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()

        # TODO: Make a CRUD for the admin site 
        with connection.cursor() as cursor:
            # Get the list of users
            # Find out last activity of users 
            cursor.execute('SELECT * FROM users')
            list_of_users = cursor.fetchall()
        
        context['list_of_users'] = list_of_users

        return render(request,'admin_user.html',context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))

def admin_user_create(request):
    '''
    admin_user_create view function responsible for the creation of users from the admin side.
    Takes in the request and returns the rendering of the admin_user_create page.
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_user_create page (path: /admin_user_create)
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    context = dict()
    message = ''

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                created_user_type = request.POST['type']
                
                cursor.execute('INSERT INTO users (full_name,username,email,phone_number,password,type) VALUES (%s,%s,%s,%s,%s,%s)', [
                    request.POST['full_name'],request.POST['username'],request.POST['email'],request.POST['phone_number'],request.POST['password'],request.POST['type']
                    ])

                if created_user_type == 'member':
                    cursor.execute('INSERT INTO member (email) VALUES (%s)', [ request.POST['email']])
                elif created_user_type == 'administrator':
                    cursor.execute('INSERT INTO administrator (email) VALUES (%s)', [ request.POST['email']])
                else:
                    message = 'Please indicate a right user type'

        context['message'] = message
        return render(request,'admin_user_create.html',context)

    return HttpResponseRedirect(reverse('admin_index'))

def admin_user_edit(request,edit_email):
    '''
    admin_user_edit view function responsible for the editing of user's credentials from the admin side.
    Takes in the request and the user's email and returns the rendering of the admin_user_edit page.
    Argument:
        request: HTTP request
        edit_email: user email that wants to be edited
    Return:
        render function: renders the admin_user_edit page (path: /admin_user_edit/edit_email)
    '''
    user_email = request.session.get('email',False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST': 
            
            with connection.cursor() as cursor:

                cursor.execute('UPDATE users SET full_name = %s, username = %s, phone_number = %s, password = %s, type = %s WHERE email = %s', [
                    request.POST['full_name'], request.POST['username'],request.POST['phone_number'],request.POST['password'],request.POST['type'], edit_email
                ])

            return HttpResponseRedirect(reverse('admin_user'))
        
        else:
            return render(request,'admin_user_edit.html')

    return HttpResponseRedirect(reverse('admin_index'))

def admin_user_delete(request,delete_email):
    '''
    admin_user_delete view function responsible for the deleting users from the database from the admin side.
    Takes in the request and the user's email and executes a SQL query to delete the user from the database.
    Argument:
        request: HTTP request
        delete_email: user email that wants to be deleted
    Return: 
        HTTP Response Redirect to the admin_user page
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                cursor.execute('SELECT type FROM users WHERE email = %s', [ delete_email ])
                delete_type = cursor.fetchone()

                # check which type, to correctly initiate the ON DELETE CASCADE
                if delete_type == 'administrator' and user_email!= delete_email: # also check so that the admin does not delete him/herself
                    cursor.execute ('DELETE FROM administrator WHERE email = %s', [ delete_email ])   
                    # TODO: pops up the message if the admin is trying to delete him/herself      
                elif delete_type == 'member':
                    cursor.execute ('DELETE FROM member WHERE email = %s', [ delete_email ])

        return HttpResponseRedirect(reverse('admin_user'))

    return HttpResponseRedirect(reverse('admin_index'))

def admin_activity(request):
    '''
    user_activity view function responsible for the list of activities page from the admin side.
    Takes in the request and returns the rendering of the admin_activity page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_activity page (path: /admin_activity)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()

        # TODO: Make a CRUD for the admin site 
        with connection.cursor() as cursor:
            # Get the list of users 
            cursor.execute('SELECT * FROM activity')
            list_of_activities = cursor.fetchall()
        
        context['list_of_activities'] = list_of_activities

        return render(request,'admin_activity.html',context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))

def admin_activity_create(request):
    '''
    admin_activity_create view function responsible for the creation of activity from the admin side.
    Takes in the request and returns the rendering of the admin_activity_create page.
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_user_create page (path: /admin_activity_create)
    '''
    user_email = request.session.get('email',False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:
        
        context = dict()
        with connection.cursor() as     cursor:
            cursor.execute('SELECT * FROM category')
            categories = cursor.fetchall()
            
        if request.method == 'POST':

            with connection.cursor() as cursor:
                
                # TODO: Add the checking of inputs 
                cursor.execute('INSERT INTO activity (inviter,category,activity_name,start_date_time,venue,capacity VALUES (%s,%s,%s,%s,%s,%s)', [
                    request.POST['inviter'],request.POST['category'],request.POST['activity_name'],request.POST['start_date-time'],request.POST['venue'],request.POST['capacity']
                ])

        context = {'categories' : categories}

        return render(request,'admin_activity_create.html',context)

    return HttpResponseRedirect(reverse('admin_activity'))

def admin_activity_edit(request,activity_id):
    '''
    admin_activity_edit view function responsible for the editing of activity from the admin side.
    Takes in the request and the user's email and returns the rendering of the admin_activity_edit page.
    Argument:
        request: HTTP request
        activity_id: activity_id that wants to be edited
    Return:
        render function: renders the admin_user_edit page (path: /admin_activity_edit/activity_id)
    '''
    user_email = request.session.get('email',False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST': 
            
            with connection.cursor() as cursor:

                cursor.execute('UPDATE activity SET inviter  = %s, category = %s, activity_name = %s, start_date_time = %s, venue = %s, capacity = %s WHERE activity_id = %s', [
                    request.POST['inviter'], request.POST['category'],request.POST['activity_name'],request.POST['start_date_time'],request.POST['venue'], request.POST['capacity'], activity_id
                ])

            return HttpResponseRedirect(reverse('admin_activity'))
        
        else:
            return render(request,'admin_activity_edit.html')

    return HttpResponseRedirect(reverse('admin_index'))

def admin_activity_delete(request,activity_id):
    '''
    admin_activity_delete view function responsible for the deleting activities from the database from the admin side.
    Takes in the request and the activity ID and executes a SQL query to delete the user from the database.
    Argument:
        request: HTTP request
        activity_id: activity ID that wants to be deleted
    Return:
        HTTP Response Redirect to the admin_activity page
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                cursor.execute('DELETE FROM activity WHERE activity_id = %s', [ activity_id ])

        return HttpResponseRedirect(reverse('admin_activity'))

    return HttpResponseRedirect(reverse('admin_index'))

def admin_review(request):
    '''
    user_review view function responsible for the list of reviews page from the admin side.
    Takes in the request and returns the rendering of the admin_review page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_review page (path: /admin_review)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()

        with connection.cursor() as cursor:
            # Get the list of users 
            cursor.execute('SELECT * FROM review')
            list_of_reviews = cursor.fetchall()
        
        context['list_of_reviews'] = list_of_reviews

        return render(request,'admin_review.html',context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))

def admin_review_delete(request,activity_id,timestamp,participant_email):
    '''
    admin_review_delete view function responsible for the deleting reviews from the database from the admin side.
    Takes in the request and the activity ID and executes a SQL query to delete the review from the database.
    Argument:
        request: HTTP request
        activity_id: activity ID of the review that wants to be deleted
        timestamp: timestamp of the review that wants to be deleted
        participant_email: participant of the review that wants to be deleted
    Return:
        HTTP Response Redirect to the admin_review page
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                cursor.execute('DELETE FROM review WHERE activity_id = %s AND timestamp = %s AND participant = %s', [ 
                    activity_id, timestamp,participant_email ])

        return HttpResponseRedirect(reverse('admin_review'))

    return HttpResponseRedirect(reverse('admin_index'))

def admin_report(request):
    '''
    user_report view function responsible for the list of reports page from the admin side.
    Takes in the request and returns the rendering of the admin_report page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_report page (path: /admin_report)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()

        with connection.cursor() as cursor:
            # Get the list of users 
            cursor.execute('SELECT * FROM report')
            list_of_reports = cursor.fetchall()
        
        context['list_of_reports'] = list_of_reports

        return render(request,'admin_report.html',context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))

def admin_report_delete(request,submitter_email,timestamp):
    '''
    admin_report_delete view function responsible for the deleting reports from the database from the admin side.
    Takes in the request, submitter's email, and timestamp, and executes a SQL query to delete the report from the database.
    Argument:
        request: HTTP request
        submitter_email: the report submitter's email that wants to be deleted
        timestamp: the timestamp of the report that wants to be deleted
    Return:
        HTTP Response Redirect to the admin_report page
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                cursor.execute('DELETE FROM report WHERE submitter = %s AND timestamp = %s', [ submitter_email,timestamp ])

        return HttpResponseRedirect(reverse('admin_report'))

    return HttpResponseRedirect(reverse('admin_index'))

# View function for category popularity list
def frontpage(request):
    '''
    frontpage view function is a friendly front page for the website
    that introduces a little of what KopiDarat is about and displays 
    general stats of the website to get new visitors interested,
    from the number of activities, number of registered users,
    and the list of activity categories with its respective popularity
    Argument:
        request: HTTP request
    Return:
        render function: renders the category_popularity page (path: /category_popularity)
    '''
    context={}
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM activity')
        activity_count=cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count=cursor.fetchone()[0]
        cursor.execute('SELECT category, COUNT(*) FROM activity GROUP BY category ORDER BY COUNT(*) DESC')
        categories = cursor.fetchall()

        context["activity_count"]=activity_count
        context["user_count"]=user_count
        context["categories"] = categories
        return render(request,'frontpage.html',context)
        

# View functions for login functions 
def login_view(request):
    #Check if user is already signed in
    if request.session.get("email",False) is not False:
        if request.session.get('type') == 'administrator':
            return HttpResponseRedirect(reverse("admin_index"))
        else:
            return HttpResponseRedirect(reverse("index"))

    if request.method == "POST":
        # Attempt to sign user in
        user_id = request.POST["user_id"]
        password = request.POST["password"]
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE email=%s AND password=%s',[user_id,password])
            user1 = cursor.fetchone()
            cursor.execute('SELECT * FROM users WHERE username=%s AND password=%s',[user_id,password])
            user2 = cursor.fetchone()
        
        if user1 is not None or user2 is not None:

            # User logged in by email
            if user1 is not None:
                request.session["email"] = user_id
                with connection.cursor() as cursor:
                    cursor.execute('SELECT username,full_name,type FROM users WHERE email = %s', [user_id])
                    username,full_name,type = cursor.fetchone()
                    request.session["username"] = username
                    request.session["full_name"] = full_name
                    request.session["type"] = type

            # User logged in by username
            else:
                request.session["username"] = user_id
                with connection.cursor() as cursor:
                    cursor.execute('SELECT email,full_name,type FROM users WHERE username = %s', [user_id])
                    email,full_name,type = cursor.fetchone()
                    request.session["email"] = email
                    request.session["full_name"] = full_name
                    request.session["type"] = type

            if request.session["type"] == 'administrator':
                return HttpResponseRedirect(reverse("admin_index"))
            else:
                return HttpResponseRedirect(reverse("index"))
        
        # No matching user-password combination found
        else:
            return render(request, "login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "login.html",{"message":"Please login to view our site."})

def logout_view(request):
    if "email" in request.session:
        del request.session["email"]
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

        ## Check if customerid is already in the table
        with connection.cursor() as cursor:

            cursor.execute("SELECT * FROM users WHERE email = %s", [request.POST['email']])
            user = cursor.fetchone()

            ## No user with same email
            if user == None:
                cursor.execute("SELECT * FROM users WHERE username = %s",[request.POST['username']])
                user = cursor.fetchone()

                if user == None:
                    cursor.execute("INSERT INTO users VALUES (%s, %s, %s, %s, %s, 'member')"
                            , [request.POST['full_name'], request.POST['username'], request.POST['email'],
                            request.POST['phone_number'],request.POST['password']])

                    cursor.execute("INSERT INTO member VALUES (%s)", [
                        request.POST['email']
                    ])
                    request.session["username"] = request.POST['username']
                    request.session["full_name"] = request.POST['full_name']
                    request.session["type"] = 'member'

                    return HttpResponseRedirect('index')
                else:
                    status = 'Customer with username %s already exists' % (request.POST['username'])    
            else:
                status = 'Customer with email %s already exists' % (request.POST['email'])    
    context['message'] = status
    return render(request, "register.html", context)



    
    

