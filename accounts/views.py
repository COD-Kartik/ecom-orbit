from django.shortcuts import render


def loading_page(request):
    return render(request, 'loading.html')
