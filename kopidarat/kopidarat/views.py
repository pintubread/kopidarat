from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db import connection

# Create your views here.
def index(request):
    return render(request,"index.html")

def test(request):
    return HttpResponse("Test")

def greet(request,name):
    return HttpResponse(f"Hello, {name.capitalize()}!")