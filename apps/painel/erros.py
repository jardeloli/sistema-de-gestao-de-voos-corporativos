from django.shortcuts import render


def acesso_negado(request, exception=None):
    return render(request, "erros/403.html", status=403)


def nao_encontrado(request, exception=None):
    return render(request, "erros/404.html", status=404)
