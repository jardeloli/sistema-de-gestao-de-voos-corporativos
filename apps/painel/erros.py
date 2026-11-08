from django.shortcuts import render


def acesso_negado(request, exception=None):
    return render(request, "erros/403.html", status=403)


def nao_encontrado(request, exception=None):
    return render(request, "erros/404.html", status=404)


def requisicao_invalida(request, exception=None):
    return render(request, "erros/400.html", status=400)


def erro_servidor(request):
    return render(request, "erros/500.html", status=500)
