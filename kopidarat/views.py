# Django imports
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.db import connection, IntegrityError
from django.urls import reverse
from django.core.mail import send_mail
from django.template import loader
from dateutil.relativedelta import relativedelta

# Custom imports
import datetime

# View Functions for main pages for the member's side of the website
def index(request,*kwargs):
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
    message=''
    empty=True
    if kwargs:
        message=''.join(kwargs)
    if user_email is not False:
        with connection.cursor() as cursor:
            cursor.execute("SELECT a.activity_id, u.full_name as inviter, a.category, a.activity_name, a.start_date_time, a.end_date_time,a.venue, a.capacity, (SELECT COUNT(*) FROM activity a1, joins j1 WHERE j1.activity_id = a1.activity_id AND a.activity_id=a1.activity_id) AS joined FROM activity a, users u WHERE a.inviter = u.email AND a.start_date_time>NOW() AND a.category IN (SELECT a2.category FROM joins j2, activity a2 WHERE j2.activity_id = a2.activity_id AND j2.participant= '"+user_email+"' AND a.start_date_time - NOW() < '7 days' GROUP BY a2.category ORDER BY COUNT(*) DESC LIMIT 3) AND a.activity_id NOT IN (SELECT a3.activity_id FROM activity a3,joins j3 WHERE j3.participant='"+user_email+"' AND j3.activity_id=a3.activity_id) ORDER BY a.start_date_time ASC")
            recommended_activities = cursor.fetchall()
            if len(recommended_activities)>0:
                empty=False
        
        # Put all the records inside the dictionary context
        context = {'recommended_activities':recommended_activities,
        'message':message}

        if empty:
            context['empty']=empty
        return render(request, "index.html", context)
    else:
        return HttpResponseRedirect(reverse("frontpage"))

def all_activities(request,*kwargs):
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
    message=''
    if kwargs:
        message=''.join(kwargs)
    if user_email is not False:
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM category')
            categories = cursor.fetchall()

        all_activities_sql = "SELECT a.activity_id, u.full_name as inviter, a.category, a.activity_name, a.start_date_time, a.end_date_time,a.venue, a.capacity, (SELECT COUNT(*) FROM activity a1, joins j1 WHERE j1.activity_id = a1.activity_id AND a.activity_id=a1.activity_id) AS joined FROM activity a, users u WHERE a.inviter = u.email AND a.start_date_time>NOW() AND a.activity_id NOT IN (SELECT a1.activity_id FROM activity a1,joins j1 WHERE j1.participant='"+user_email+"' AND j1.activity_id=a1.activity_id)"
        ordering_sql = " ORDER BY a.start_date_time ASC"
        
        
        if request.method == "POST":
            # filtering method for categories
            list_of_categories = request.POST.getlist('categories')
            category_filters = ""
            category_filter_sql=""
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
                display_period = list_of_time_filters[0].split('_') # Need the values in HTML to be split with underscore
                duration,unit = int(display_period[0]),display_period[1]

                if unit == 'week':
                    limit_time = (datetime.datetime.now()) + datetime.timedelta(weeks=duration)
                elif unit == 'month':
                    limit_time = (datetime.datetime.now()) + relativedelta(month=duration)
                time_filter_sql = " AND a.start_date_time <"+limit_time.strftime("'%Y-%m-%d %H:%M:%S'")
            
            with connection.cursor() as cursor:
                cursor.execute(all_activities_sql + category_filter_sql + time_filter_sql + ordering_sql)
                activities = cursor.fetchall()
        
        else:
            with connection.cursor() as cursor:
                cursor.execute(all_activities_sql+ordering_sql)
                activities = cursor.fetchall()

        # Put all the records inside the dictionary context
        context = {'records' : activities,
        'full_name':request.session.get("full_name"),
        'categories':categories,
        'message':message}
        return render(request, "all_activities.html", context)
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
    # Check if user is logged in
    user_email = request.session.get("email", False)
    message = ''
    if user_email is not False:
        context = {}
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM category')
            categories = cursor.fetchall()
            context["categories"] = categories

        if request.method == 'POST':
            with connection.cursor() as cursor:
                try:
                    cursor.execute('CALL create_new_activity(%s,%s,%s,%s,%s,%s,%s)',[
                        user_email,request.POST['category'],request.POST['activity_name'],request.POST['start_date_time'],request.POST['end_date_time'],request.POST['venue'], request.POST['capacity']])
                except Exception as e:
                    message = str(e)
                    if 'violates check constraint "activity_check"' in message:
                        message = "Activity's end date and time must be after activity's start date and time."
        
        context['message'] = message
        return render(request, 'create_activity.html', context)
    return HttpResponseRedirect(reverse("index"))

def create_review(request,activity_id):
    '''
    create_review view function which is responsible for the creating review page.
    Takes in the request and returns a render function to render the review page.
    Argument: 
        request: HTTP request
    Return: 
        render function: renders the review page (path: /create_review)
    '''
    user_email = request.session.get("email", False)
    message = ""
    context={}

    if user_email is not False:

        with connection.cursor() as cursor:
            cursor.execute('SELECT u.full_name AS name, a.activity_name AS activity FROM activity a, users u WHERE a.activity_id=%s AND u.email=a.inviter',[activity_id])
            activity_details = cursor.fetchone()
            context["activity_details"]=activity_details

            if request.method == 'POST':
                try:
                    cursor.execute('INSERT INTO review VALUES (%s,%s,%s,%s,%s)', [
                                activity_id, datetime.datetime.now(
                                ), user_email,request.POST['rating'],
                                request.POST['comment']
                            ])
                except Exception as e:
                    message=str(e)
                    
        context["message"]=message
        return render(request, 'review.html', context)
    else:
        return HttpResponseRedirect(reverse("index"))

def create_report(request, username):
    '''
    create_report view function which is responsible for the reports page.
    Takes in the request and returns a render function to render the reports page.
    Argument: 
        request: HTTP request
    Return:
        render function: renders the reports page (path: /create_report)
    '''
    user_email = request.session.get("email", False)
    context={}
    message = ""

    if user_email is not False:
        
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE username=%s', [username])
            this_participant=cursor.fetchone()

        if request.method == 'POST':
            with connection.cursor() as cursor:
                try:
                    cursor.execute('INSERT INTO report VALUES (%s,%s,(SELECT email FROM users WHERE username=%s),%s,%s)', [
                        user_email, datetime.datetime.now(), username,
                        request.POST['comment'], request.POST['severity']])
                    cursor.execute('SELECT * FROM users WHERE username=%s', [username])
                    this_participant=cursor.fetchone()
                except IntegrityError:
                    message = 'There exists no user with the username '+request.POST['username']+'. Please try again.'

        context['message'] = message
        context['this_participant'] = this_participant
        return render(request, 'report.html', context)

    return HttpResponseRedirect(reverse("user_activity"))

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
                message='You have successfully registered for this activity!'
            except IntegrityError:
                message='You have registered for this activity.'
            except Exception as e:
                string_message=str(e)
                message=string_message.split(".",1)[0]+"."
            
        return index(request,message)
    else:
        HttpResponseRedirect("index")

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
        inviter_past_list_empty=True
        inviter_future_list_empty=True
        joined_future_activities_list_empty=True
        joined_past_activities_list_empty=True
        reports_list_empty=True
        reviews_list_empty=True

        with connection.cursor() as cursor:

            # Get the table of past activities where the current user is the inviter
            cursor.execute('SELECT * FROM activity a, users u WHERE a.inviter = u.email AND a.inviter = %s AND a.start_date_time < NOW() ORDER BY a.start_date_time ASC', [
                user_email
            ])
            past_inviter_list = cursor.fetchall()
            if len(past_inviter_list)>0:
                inviter_past_list_empty=False
            if inviter_past_list_empty:
                context["inviter_past_list_empty"]=inviter_past_list_empty

            # Get the table of upcoming activities where the current user is the inviter
            cursor.execute('SELECT a.activity_id, u.full_name as inviter, a.category, a.activity_name, a.start_date_time, a.end_date_time, a.venue, count_participant.count, a.capacity FROM activity a, users u, joins j, (SELECT j1.activity_id, COUNT(j1.participant) as count FROM activity a1, joins j1 WHERE j1.activity_id = a1.activity_id GROUP BY j1.activity_id) AS count_participant WHERE a.inviter = u.email AND a.inviter = %s AND j.activity_id = a.activity_id AND j.participant = u.email AND count_participant.activity_id = a.activity_id AND a.start_date_time > NOW() ORDER BY a.start_date_time ASC', [
                user_email
            ])
            inviter_list = cursor.fetchall()
            if len(inviter_list)>0:
                inviter_future_list_empty=False
            if inviter_future_list_empty:
                context["inviter_future_list_empty"]=inviter_future_list_empty

            # Get the table of upcoming activities created by other user where the user has signed up for
            cursor.execute('SELECT a.activity_id, u.full_name, a.category, a.activity_name, a.start_date_time, a.end_date_time, a.venue FROM joins j, activity a, users u WHERE j.activity_id = a.activity_id AND a.inviter = u.email AND a.inviter <> j.participant AND j.participant = %s AND NOW() <= a.start_date_time ORDER BY a.start_date_time ASC', [
                user_email
            ])
            upcoming_activities_list = cursor.fetchall()
            if len(upcoming_activities_list)>0:
                joined_future_activities_list_empty=False
            if joined_future_activities_list_empty:
                context["joined_future_activities_list_empty"]=joined_future_activities_list_empty

            # Get the table of past activities created by other user where the user has joined
            cursor.execute('SELECT a.activity_id, a.inviter, u.full_name, a.category, a.activity_name, a.start_date_time, a.end_date_time, a.venue FROM joins j, activity a, users u WHERE j.activity_id = a.activity_id AND a.inviter = u.email AND a.inviter <> j.participant AND j.participant = %s AND NOW() > a.start_date_time ORDER BY a.start_date_time ASC', [
                user_email
            ])
            joined_activities_list = cursor.fetchall()
            if len(joined_activities_list)>0:
                joined_past_activities_list_empty=False
            if joined_past_activities_list_empty:
                context["joined_past_activities_list_empty"]=joined_past_activities_list_empty
            

            # Get table of reviews that user has created
            cursor.execute('SELECT r.timestamp, a.activity_name, r.rating, r.comment FROM review r, activity a, users u WHERE r.activity_id = a.activity_id AND r.participant = u.email AND r.participant = %s ORDER BY a.start_date_time ASC', [
                user_email
            ])
            reviews_list = cursor.fetchall()
            if len(reviews_list)>0:
                reviews_list_empty=False
            if reviews_list_empty:
                context["reviews_list_empty"]=reviews_list_empty

            # Get table of reports that user has created
            cursor.execute('SELECT r.timestamp, r.report_user, r.comment, r.severity FROM report r, users u WHERE r.report_user = u.email AND r.submitter = %s ORDER BY r.timestamp ASC', [
                user_email
            ])
            reports_list = cursor.fetchall()
            if len(reports_list)>0:
                reports_list_empty=False
            if reports_list_empty:
                context["reports_list_empty"]=reports_list_empty

        context['user_fullname'] = request.session.get('full_name')
        context['inviter_past_list'] = past_inviter_list
        context['inviter_future_list'] = inviter_list
        context['joined_future_activities_list'] = upcoming_activities_list
        context['joined_past_activities_list'] = joined_activities_list
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
    message=''

    if user_email is not False:

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM activity WHERE activity_id=%s', [activity_id])
            this_activity = cursor.fetchone()

        if request.method == 'POST':  # TODO: catch error when there's no post method, e.g. cancel to create activity
            with connection.cursor() as cursor:
                try:
                    # Execute SQL query to update the values for the particular instance
                    cursor.execute('UPDATE activity SET activity_name = %s, category = %s, start_date_time = %s,end_date_time = %s, venue = %s, capacity = %s WHERE activity_id = %s', [
                        request.POST['activity_name'], request.POST['category'], request.POST[
                            'start_date_time'], request.POST['end_date_time'],request.POST['venue'], request.POST['capacity'], activity_id
                    ])
                    cursor.execute('SELECT * FROM activity WHERE activity_id=%s', [activity_id])
                    this_activity = cursor.fetchone()
                except Exception as e:
                    message = str(e)

        context['message'] = message
        context['this_activity'] = this_activity
        return render(request,'update_activity.html',context)

    return HttpResponseRedirect(reverse("index"))

def delete_activity(request, activity_id):
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

def participants(request, activity_id):
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
    context = {}
    user_email = request.session.get("email", False)
    has_passed = False

    if user_email is not False:

        with connection.cursor() as cursor:
            # Execute SQL query to check if user is registered under this activity
            cursor.execute('SELECT * FROM joins WHERE activity_id=%s AND participant=%s', [
                activity_id, user_email
            ])
            user = cursor.fetchone()

        if user is not None:
            with connection.cursor() as cursor:
                cursor.execute("SELECT u.full_name, u.username, u.email, u.phone_number, (CASE WHEN u.email=a.inviter THEN 'Inviter' ELSE 'Participant' END) AS remarks FROM users u, joins j, activity a WHERE j.activity_id = a.activity_id AND j.activity_id=%s AND u.email=j.participant AND u.email<>%s",
                            [int(activity_id), user_email])
                participants = cursor.fetchall()

                cursor.execute(
                    'SELECT a.activity_name,a.inviter,a.end_date_time FROM activity a WHERE a.activity_id=%s', [activity_id])
                activity_name, inviter, end_time = cursor.fetchone()

                if end_time < datetime.datetime.now():
                    has_passed = True

            context["has_passed"] = has_passed
            context["participants"] = participants
            context["activity_name"] = activity_name
            context["inviter"] = inviter
            return render(request, 'participants.html', context)
        else:
            message="You are not registered for this activity, hence you are not authorised to view this page."
            return index(request,message)

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
            cursor.execute(
                'SELECT u.username, COUNT(j.participant) AS total_join FROM users u, joins j WHERE u.email = j.participant GROUP BY u.username ORDER BY total_join DESC ,u.username ASC LIMIT 5')
            list_of_active_users = cursor.fetchall()

            # Select the top 5 activities with the most reviews, by counting the number of reviews
            cursor.execute('SELECT a.activity_id,a.activity_name, COUNT(r.comment) AS total_reviews FROM activity a, review r WHERE a.activity_id = r.activity_id GROUP BY a.activity_id, a.activity_name ORDER BY total_reviews DESC, a.activity_id ASC LIMIT 5')
            list_of_reviewed_activities = cursor.fetchall()

            # Select the 5 most reported users (counted if the severity is medium or high only)
            cursor.execute("SELECT u.username, COUNT(r.comment) AS total_reports FROM users u, report r WHERE u.email = r.report_user AND (r.severity = 'medium' OR r.severity = 'high') GROUP BY u.username ORDER BY total_reports DESC, u.username ASC LIMIT 5")
            list_of_user_reports = cursor.fetchall()

            # Select activities created by administrators
            cursor.execute("SELECT * FROM activity a, users u WHERE a.inviter = u.email AND u.type = 'administrator' ORDER BY a.start_date_time ASC")
            list_of_activities_by_admin = cursor.fetchall()

        context = {
            'list_of_active_users': list_of_active_users,
            'list_of_reviewed_activities': list_of_reviewed_activities,
            'list_of_user_reports': list_of_user_reports,
            'list_of_activities_by_admin': list_of_activities_by_admin
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

        with connection.cursor() as cursor:
            # Get the list of users
            cursor.execute(
                'SELECT * FROM users ORDER BY type ASC, full_name ASC')
            list_of_users = cursor.fetchall()

        context['list_of_users'] = list_of_users

        return render(request, 'admin_user.html', context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))

def admin_inactive_users(request):
    '''
    view function responsible for displaying the list of users who never participated in any activity.
    Takes in the request and returns the rendering of the admin_user page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_user page (path: /admin_user)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')
    list_of_inactive_users_empty=True

    if user_type == 'administrator' and user_email is not False:

        context = dict()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT u.full_name, u.username, u.email, u.phone_number FROM users u WHERE u.email NOT IN (SELECT j.participant FROM joins j) AND u.type<>'administrator'"
            )
            list_of_inactive_users = cursor.fetchall()
            if len(list_of_inactive_users)>0:
                list_of_inactive_users_empty=False
            if list_of_inactive_users_empty:
                context['list_of_inactive_users_empty']=list_of_inactive_users_empty

        context['list_of_inactive_users'] = list_of_inactive_users

        return render(request, 'admin_inactive_users.html', context)
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
                try:
                    created_user_type = request.POST['type']

                    cursor.execute('INSERT INTO users (full_name,username,email,phone_number,password,type) VALUES (%s,%s,%s,%s,%s,%s)', [
                        request.POST['full_name'], request.POST['username'], request.POST[
                            'email'], request.POST['phone_number'], request.POST['password'], request.POST['type']
                    ])

                    if created_user_type == 'member':
                        cursor.execute('INSERT INTO member (email) VALUES (%s)', [
                                    request.POST['email']])
                    elif created_user_type == 'administrator':
                        cursor.execute('INSERT INTO administrator (email) VALUES (%s)', [
                                    request.POST['email']])
                    else:
                        message = 'Please indicate a right user type'
                except Exception as e:
                    message = str(e)

        context['message'] = message
        return render(request, 'admin_user_create.html', context)

    return HttpResponseRedirect(reverse('admin_index'))

def admin_user_edit(request, edit_email):
    '''
    admin_user_edit view function responsible for the editing of user's credentials from the admin side.
    Takes in the request and the user's email and returns the rendering of the admin_user_edit page.
    Argument:
        request: HTTP request
        edit_email: user email that wants to be edited
    Return:
        render function: renders the admin_user_edit page (path: /admin_user_edit/edit_email)
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')
    context = {}
    message = ''

    if user_type == 'administrator' and user_email is not False:

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM users WHERE email = %s', [edit_email])
            obj = cursor.fetchone()

        if request.method == 'POST':
            with connection.cursor() as cursor:
                try:
                    cursor.execute('UPDATE users SET full_name = %s, username = %s, phone_number = %s, password = %s, type = %s WHERE email = %s', [
                        request.POST['full_name'], request.POST['username'], request.POST[
                            'phone_number'], request.POST['password'], request.POST['type'], edit_email
                    ])
                    cursor.execute(
                        'SELECT * FROM users WHERE email = %s', [edit_email])
                    obj = cursor.fetchone()
                except Exception as e:
                    message = str(e)

        context['obj'] = obj
        context['message'] = message
        return render(request, 'admin_user_edit.html', context)

    return HttpResponseRedirect(reverse('admin_index'))

def admin_user_delete(request, delete_email):
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

        with connection.cursor() as cursor:
            cursor.execute("SELECT type FROM users WHERE email = %s", [delete_email])
            delete_type = cursor.fetchone()[0]

            # check which type, to correctly initiate the ON DELETE CASCADE
            # also check so that the admin does not delete him/herself
            if delete_type == 'administrator':
                if user_email != delete_email:
                    cursor.execute("DELETE FROM users WHERE email= %s",[delete_email])
                    cursor.execute("DELETE FROM administrator WHERE email = %s",[delete_email])
                else:
                    request.session["message"]="You cannot delete yourself"
                # TODO: pops up the message if the admin is trying to delete him/herself
            elif delete_type == 'member':
                print("Check")
                cursor.execute("DELETE FROM users WHERE email= %s",[delete_email])
                cursor.execute("DELETE FROM member WHERE email = %s",[delete_email])
                print("Hooray")

        return HttpResponseRedirect(reverse('admin_user'))
    else:
        return HttpResponseRedirect(reverse('index'))

def admin_activity(request):
    '''
    admin_activity view function responsible for the list of activities page from the admin side.
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

        with connection.cursor() as cursor:
            # Get the list of activities
            cursor.execute('SELECT a.activity_id, u.full_name as inviter, a.category, a.activity_name, a.start_date_time, a.venue, count_participant.count, a.capacity, a.end_date_time FROM activity a, users u, joins j, (SELECT j1.activity_id, COUNT(j1.participant) as count FROM activity a1, joins j1 WHERE j1.activity_id = a1.activity_id GROUP BY j1.activity_id) AS count_participant WHERE a.inviter = u.email AND j.activity_id = a.activity_id AND j.participant = u.email AND count_participant.activity_id = a.activity_id AND count_participant.count <= a.capacity GROUP BY a.activity_id, u.full_name, a.category, a.activity_name, a.start_date_time, a.venue, count_participant.count, a.capacity ORDER BY a.start_date_time ASC')
            list_of_activities = cursor.fetchall()

        context['list_of_activities'] = list_of_activities

        return render(request, 'admin_activity.html', context)
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
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM category')
            categories = cursor.fetchall()

        if request.method == 'POST':

            with connection.cursor() as cursor:
                try:
                    cursor.execute('CALL create_new_activity(%s,%s,%s,%s,%s,%s,%s)',[
                        user_email,request.POST['category'],request.POST['activity_name'],request.POST['start_date_time'],request.POST['end_date_time'],request.POST['venue'], request.POST['capacity']])
                except Exception as e:
                    message = str(e)
        
        context['message'] = message
        context['categories'] = categories
        return render(request, 'admin_activity_create.html', context)

    return HttpResponseRedirect(reverse('admin_activity'))

def admin_activity_edit(request, activity_id):
    '''
    admin_activity_edit view function responsible for the editing of activity from the admin side.
    Takes in the request and the user's email and returns the rendering of the admin_activity_edit page.
    Argument:
        request: HTTP request
        activity_id: activity_id that wants to be edited
    Return:
        render function: renders the admin_user_edit page (path: /admin_activity_edit/activity_id)
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')
    context = {}
    message = ''

    if user_type == 'administrator' and user_email is not False:

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM activity WHERE activity_id=%s', [activity_id])
            this_activity = cursor.fetchone()

        if request.method == 'POST':

            with connection.cursor() as cursor:
                try:
                    cursor.execute('UPDATE activity SET category = %s, activity_name = %s, start_date_time = %s,end_date_time = %s, venue = %s, capacity = %s WHERE activity_id = %s', [
                        request.POST['category'], request.POST['activity_name'], request.POST[
                            'start_date_time'], request.POST['end_date_time'], request.POST['venue'], request.POST['capacity'], activity_id
                    ])
                    cursor.execute('SELECT * FROM activity WHERE activity_id=%s', [activity_id])
                    this_activity = cursor.fetchone()
                except Exception as e:
                    message = str(e)

        context['message']= message
        context['this_activity'] = this_activity
        return render(request,'admin_activity_edit.html',context)

    return HttpResponseRedirect(reverse('admin_index'))

def admin_activity_delete(request, activity_id):
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

                cursor.execute(
                    'DELETE FROM activity WHERE activity_id = %s', [activity_id])

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

        return render(request, 'admin_review.html', context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))

def admin_review_delete(request, activity_id, timestamp, participant_email):
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
                    activity_id, timestamp, participant_email])

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

        return render(request, 'admin_report.html', context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))

def admin_report_delete(request, submitter_email, timestamp):
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

                cursor.execute('DELETE FROM report WHERE submitter = %s AND timestamp = %s', [
                               submitter_email, timestamp])

        return HttpResponseRedirect(reverse('admin_report'))

    return HttpResponseRedirect(reverse('admin_index'))

# View function for the main page
def frontpage(request):
    '''
    frontpage view function is a friendly front page for the website
    that introduces a little of what KopiDarat is about and displays 
    general stats of the website to get new visitors interested,
    from the number of activities, number of registered users,
    and the list of activity categories with its respective popularity.
    Argument:
        request: HTTP request
    Return:
        render function: renders the category_popularity page (path: /category_popularity)
    '''
    user_email = request.session.get("email", False)
    if user_email is not False:
        return HttpResponseRedirect(reverse('index'))
    context = {}
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM activity')
        activity_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        cursor.execute(
            'SELECT category, COUNT(*) FROM activity GROUP BY category ORDER BY COUNT(*) DESC')
        categories = cursor.fetchall()
    # Select the top 5 activities with the highest average rating
        cursor.execute('SELECT a.activity_id,a.activity_name, CAST(AVG(r.rating) AS NUMERIC(10,2)) AS rating FROM activity a, review r WHERE a.activity_id = r.activity_id GROUP BY a.activity_id, a.activity_name ORDER BY rating DESC, a.activity_id ASC LIMIT 5')
        top_rated_activities = cursor.fetchall()

        context["activity_count"] = activity_count
        context["user_count"] = user_count
        context["categories"] = categories
        context["top_rated_activities"] = top_rated_activities
        return render(request, 'frontpage.html', context)

# View functions for login functions
def login_view(request):
    '''
    login_view view function responsible for the login page.
    Takes in the request and returns the rendering of the login page.
    Argument:
        request: HTTP Request
    Return:
        render function: renders the login page (path: /login)
    '''
    # Check if user is already signed in
    if request.session.get("email", False) is not False:
        return HttpResponseRedirect(reverse("index"))

    if request.method == "POST":
        # Attempt to sign user in
        user_id = request.POST["user_id"]
        password = request.POST["password"]
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM users WHERE email=%s AND password=%s', [user_id, password])
            user1 = cursor.fetchone()
            cursor.execute(
                'SELECT * FROM users WHERE username=%s AND password=%s', [user_id, password])
            user2 = cursor.fetchone()

        if user1 is not None or user2 is not None:

            # User logged in by email
            if user1 is not None:
                request.session["email"] = user_id
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT username,full_name,type FROM users WHERE email = %s', [user_id])
                    username, full_name, type = cursor.fetchone()
                    request.session["username"] = username
                    request.session["full_name"] = full_name
                    request.session["type"] = type

            # User logged in by username
            else:
                request.session["username"] = user_id
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT email,full_name,type FROM users WHERE username = %s', [user_id])
                    email, full_name, type = cursor.fetchone()
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
        return render(request, "login.html", {"message": "Please login to view our site."})

def logout_view(request):
    '''
    logout_view view function responsible for logging out the user from the website.
    Argument:
        request: HTTP Request
    Return:
        HTTP Response Redirect to the frontpage (path: /category_popularity)
    '''
    if "email" in request.session:
        del request.session["email"]
    return HttpResponseRedirect(reverse("frontpage"))

def register(request):
    '''
    register view function responsible for the registration page.
    Takes in the request and returns the rendering of the register page.
    Argument:
        request: HTTP Request
    Return: 
        render function: renders the registration page (path: /register)
    '''
    context = {}
    status = ''

    if request.method == "POST":
        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "register.html", {
                "message": "Passwords must match."
            })
        
        with connection.cursor() as cursor:
            try:
                cursor.execute("CALL add_new_member(%s, %s, %s, %s, %s)", [request.POST['full_name'], request.POST['username'], request.POST['email'],request.POST['phone_number'], request.POST['password']])
                request.session["email"] = request.POST['email']
                request.session["full_name"] = request.POST['full_name']
                request.session["type"] = 'member'
                return redirect('index')
            except IntegrityError:
                status = 'There exists a user with the same email or username'
  
    context['message'] = status
    return render(request, "register.html", context)


