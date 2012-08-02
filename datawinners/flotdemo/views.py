# Create your views here.
from django.shortcuts import render_to_response

def chart_demo(request):
    return render_to_response("project/clinicTestAnalysisChart.html")
