"""kopidarat URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Main Page
    path('', views.index, name='index'),
    path('index_admin', views.index_admin, name='index_admin'),
    
    # Authentication pages 
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("forget_password",views.forget_password,name="forget_password"),
    path("reset_password", views.reset_password, name="reset_password"),
  
    # Joining Activity page
    path("create_activity", views.create_activity, name='create_activity'),
    path("join/<int:activity_id>", views.join, name="join"), 

    # Current User Activity Page 
    path("user_activity",views.user_activity, name='user_activity'),
    path("update_activity/<int:activity_id>",views.update_activity, name='update_activity'),
    path("delete_activity/<int:activity_id>", views.delete_activity, name = 'delete_activity'),
    path("participants/<int:activity_id>", views.participants, name = 'participants'),

    # Create review page
    path("review", views.create_review, name='review'),

    # Create report page
    path("report", views.create_report, name='report')
]


