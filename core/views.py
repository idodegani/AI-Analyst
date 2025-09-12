from django.shortcuts import render

def index(request):
    """Main chat interface view"""
    return render(request, 'index.html')
