"""
Popula o banco com dados fictícios para demonstração e capturas de tela.

    python manage.py popular_demo            # cria os dados (se o banco estiver vazio)
    python manage.py popular_demo --limpar   # apaga viagens/aeronaves/passageiros e recria

Usuários criados (senha de todos: voos2026):
    admin     – Administrador
    roberto   – Gestor
    carlos    – Agendador
    marcos    – Operacional
"""
import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.contas import perfis
from apps.frota.models import Aeronave
from apps.viagens.models import Abastecimento, Custo, Finalidade, Passageiro, Status, TipoCombustivel, Viagem

SENHA = "voos2026"
BASE = "Balsas – MA (SNBS)"
DESTINOS = [
    "Palmas – TO (SBPJ)", "Imperatriz – MA (SBIZ)", "Teresina – PI (SBTE)", "São Luís – MA (SBSL)",
    "Luís Eduardo Magalhães – BA (SNEM)", "Uruçuí – PI (SNUC)", "Bom Jesus – PI (SNGG)", "Brasília – DF (SBBR)",
]
PASSAGEIROS = [
    ("Ana Beatriz Moura", "Diretoria comercial"), ("João Pedro Sales", "Diretoria"), ("Larissa Coelho", "Pós-vendas"),
    ("Rafael Nunes", "Peças"), ("Juliana Ribeiro", "Financeiro"), ("Thiago Martins", "Consultor técnico"),
    ("Patrícia Lima", "Recursos humanos"), ("Eduardo Farias", "Gerência de filial"), ("Camila Rocha", "Marketing"),
]
DESCRICOES = {
    Finalidade.VISITA_FILIAL: "Visita de acompanhamento à filial: metas do trimestre e estoque.",
    Finalidade.REUNIAO_CLIENTE: "Reunião com grupo produtor para negociação de pacote de máquinas da safra.",
    Finalidade.TREINAMENTO: "Treinamento da equipe de pós-vendas sobre novos procedimentos de garantia.",
    Finalidade.EVENTO: "Participação em feira agrícola regional com estande da empresa.",
    Finalidade.VISITA_TECNICA: "Visita técnica a cliente com equipamento parado na colheita.",
    Finalidade.ACOMPANHAMENTO: "Acompanhamento da entrega técnica de frota de colheitadeiras.",
    Finalidade.REUNIAO_ADM: "Reunião administrativa com a diretoria na filial.",
}


class Command(BaseCommand):
    help = "Cria dados fictícios de demonstração (usuários, aeronaves, passageiros e viagens)."

    def add_arguments(self, parser):
        parser.add_argument("--limpar", action="store_true", help="Apaga os dados de voo antes de recriar.")

    @transaction.atomic
    def handle(self, *args, limpar=False, **opts):
        random.seed(42)
        if limpar:
            Abastecimento.objects.all().delete()
            Viagem.objects.all().delete()
            Passageiro.objects.all().delete()
            Aeronave.objects.all().delete()
        elif Viagem.objects.exists():
            self.stdout.write(self.style.WARNING("Já existem viagens. Use --limpar para recriar."))
            return

        usuarios = {}
        for login, nome, sobrenome, perfil in [
            ("admin", "Gustavo", "Noleto", perfis.ADMINISTRADOR),
            ("roberto", "Roberto", "Alves", perfis.GESTOR),
            ("carlos", "Carlos", "Souza", perfis.AGENDADOR),
            ("marcos", "Marcos", "Pereira", perfis.OPERACIONAL),
        ]:
            u, _ = User.objects.get_or_create(username=login, defaults={"first_name": nome, "last_name": sobrenome})
            u.set_password(SENHA)
            u.is_staff = login == "admin"
            u.is_superuser = login == "admin"
            u.save()
            u.groups.set([Group.objects.get(name=perfil)])
            usuarios[login] = u

        king = Aeronave.objects.create(
            identificacao="Bimotor da diretoria", fabricante="Beechcraft", modelo="King Air C90GTx",
            prefixo="PR-LVN", capacidade_passageiros=6,
        )
        Aeronave.objects.create(
            identificacao="Monomotor de apoio", fabricante="Cessna", modelo="182 Skylane",
            prefixo="PT-LNB", capacidade_passageiros=3, ativa=False,
        )
        pax = [Passageiro.objects.create(nome=n, setor=s) for n, s in PASSAGEIROS]

        hoje = timezone.localdate()
        finalidades = list(DESCRICOES)
        # Histórico: ~11 meses de voos realizados
        dia = hoje - timedelta(days=330)
        while dia < hoje - timedelta(days=2):
            destino = random.choice(DESTINOS)
            fin = random.choice(finalidades)
            v = self._viagem(king, dia, destino, fin, usuarios["carlos"], pax)
            if random.random() < 0.08:
                v.status = Status.CANCELADA
                v.motivo_cancelamento = random.choice(["Condições meteorológicas no destino", "Reunião remarcada pelo cliente"])
                v.cancelada_em = timezone.now()
                v.cancelada_por = usuarios["carlos"]
                v.save()
            else:
                horas = Decimal(random.choice(["0.9", "1.2", "1.4", "1.6", "1.8", "2.1", "2.5"]))
                v.status = Status.REALIZADA
                v.horas_voo = horas
                v.combustivel_consumido = (horas * Decimal(random.randint(240, 275))).quantize(Decimal("0.1"))
                v.save()
                litros = (v.combustivel_consumido + Decimal(random.randint(-40, 60))).quantize(Decimal("0.1"))
                Abastecimento.objects.create(
                    aeronave=king, viagem=v, data=dia, quantidade_litros=litros, tipo_combustivel=TipoCombustivel.QAV,
                    valor_litro=Decimal(random.choice(["8.450", "8.790", "9.120", "9.380"])),
                    local=random.choice([BASE, destino]), registrado_por=usuarios["marcos"],
                )
                Custo.objects.create(viagem=v, tipo="taxas", valor=Decimal(random.randint(180, 520)),
                                     descricao=f"Taxas de pouso e permanência em {destino.split(' (')[0]}",
                                     data=dia, registrado_por=usuarios["marcos"])
                if random.random() < 0.45:
                    Custo.objects.create(viagem=v, tipo="alimentacao", valor=Decimal(random.randint(120, 380)),
                                         descricao="Alimentação da tripulação", data=dia, registrado_por=usuarios["roberto"])
                if random.random() < 0.2:
                    Custo.objects.create(viagem=v, tipo="hospedagem", valor=Decimal(random.randint(380, 900)),
                                         descricao="Pernoite da tripulação", data=dia, registrado_por=usuarios["roberto"])
            dia += timedelta(days=random.randint(4, 9))

        # Voo realizado no início do mês corrente (alimenta os indicadores do mês)
        recente = self._viagem(king, hoje - timedelta(days=3), "São Luís – MA (SBSL)", Finalidade.REUNIAO_CLIENTE,
                               usuarios["carlos"], pax, hora=time(7, 0), ida=True)
        recente.status, recente.horas_voo, recente.combustivel_consumido = Status.REALIZADA, Decimal("1.7"), Decimal("438.0")
        recente.save()
        Abastecimento.objects.create(aeronave=king, viagem=recente, data=recente.data, quantidade_litros=Decimal("460"),
                                     tipo_combustivel=TipoCombustivel.QAV, valor_litro=Decimal("8.790"),
                                     local=BASE, registrado_por=usuarios["marcos"])
        Custo.objects.create(viagem=recente, tipo="taxas", valor=Decimal("412"), descricao="Taxas de pouso em São Luís",
                             data=recente.data, registrado_por=usuarios["marcos"])
        # Um voo de ontem ainda sem registro (aparece como "Aguardando registro")
        self._viagem(king, hoje - timedelta(days=1), "Imperatriz – MA (SBIZ)", Finalidade.VISITA_FILIAL,
                     usuarios["carlos"], pax, hora=time(8, 30), ida=True)
        # Agenda futura
        for offset, hora, destino, fin in [
            (1, time(7, 0), "Palmas – TO (SBPJ)", Finalidade.REUNIAO_CLIENTE),
            (3, time(6, 30), "Luís Eduardo Magalhães – BA (SNEM)", Finalidade.EVENTO),
            (6, time(9, 0), "Teresina – PI (SBTE)", Finalidade.TREINAMENTO),
            (9, time(13, 30), "Uruçuí – PI (SNUC)", Finalidade.VISITA_TECNICA),
            (14, time(8, 0), "Brasília – DF (SBBR)", Finalidade.REUNIAO_ADM),
        ]:
            self._viagem(king, hoje + timedelta(days=offset), destino, fin, usuarios["carlos"], pax, hora=hora, ida=True)

        self.stdout.write(self.style.SUCCESS(
            f"Dados criados: {Viagem.objects.count()} viagens. Usuários admin, roberto, carlos e marcos (senha: {SENHA})."
        ))

    def _viagem(self, aeronave, dia, destino, finalidade, responsavel, pax, hora=None, ida=None):
        ida = random.random() < 0.85 if ida is None else ida
        hora = hora or time(random.choice([6, 7, 8, 9, 13, 14]), random.choice([0, 30]))
        v = Viagem.objects.create(
            aeronave=aeronave, data=dia, horario_previsto=hora,
            origem=BASE if ida else destino, destino=destino if ida else BASE,
            responsavel=responsavel, finalidade=finalidade, descricao=DESCRICOES[finalidade],
        )
        v.passageiros.set(random.sample(pax, random.randint(1, min(5, aeronave.capacidade_passageiros))))
        return v
