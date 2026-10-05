"""Testes das regras de negócio e de acesso (RF03–RF08, RNF01, RNF02)."""
from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.contas import perfis
from apps.frota.models import Aeronave
from apps.viagens.forms import ViagemForm
from apps.viagens.models import Abastecimento, Finalidade, Passageiro, Status, Viagem


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aeronave = Aeronave.objects.create(identificacao="Teste", modelo="C90", prefixo="PR-TST", capacidade_passageiros=2)
        cls.pax = [Passageiro.objects.create(nome=f"Passageiro {i}") for i in range(3)]
        cls.usuarios = {}
        for nome in perfis.TODOS:
            u = User.objects.create_user(nome.lower(), password="senha-forte-123")
            u.groups.add(Group.objects.get(name=nome))
            cls.usuarios[nome] = u
        cls.amanha = timezone.localdate() + timedelta(days=1)

    def dados_viagem(self, **extra):
        dados = {
            "aeronave": self.aeronave.pk, "data": self.amanha.isoformat(), "horario_previsto": "08:00",
            "origem": "Balsas – MA", "destino": "Palmas – TO", "passageiros": [self.pax[0].pk],
            "finalidade": Finalidade.REUNIAO_CLIENTE, "descricao": "Reunião de negociação com cliente",
        }
        dados.update(extra)
        return dados

    def criar_viagem(self, **extra):
        v = Viagem.objects.create(
            aeronave=self.aeronave, data=extra.pop("data", self.amanha), horario_previsto=extra.pop("hora", time(8)),
            origem="Balsas", destino="Palmas", finalidade=Finalidade.VISITA_FILIAL,
            descricao="Visita de rotina à filial", responsavel=self.usuarios[perfis.AGENDADOR], **extra,
        )
        v.passageiros.add(self.pax[0])
        return v


class RegrasDoAgendamento(Base):
    def test_finalidade_e_descricao_sao_obrigatorias(self):
        form = ViagemForm(data=self.dados_viagem(finalidade="", descricao=""))
        self.assertFalse(form.is_valid())
        self.assertIn("finalidade", form.errors)
        self.assertIn("descricao", form.errors)

    def test_nao_permite_exceder_capacidade(self):
        form = ViagemForm(data=self.dados_viagem(passageiros=[p.pk for p in self.pax]))
        self.assertFalse(form.is_valid())
        self.assertIn("passageiros", form.errors)

    def test_nao_permite_data_passada(self):
        ontem = timezone.localdate() - timedelta(days=1)
        form = ViagemForm(data=self.dados_viagem(data=ontem.isoformat()))
        self.assertIn("data", form.errors)

    def test_origem_igual_destino(self):
        form = ViagemForm(data=self.dados_viagem(destino="balsas – ma"))
        self.assertIn("destino", form.errors)

    def test_conflito_de_horario_da_aeronave(self):
        self.criar_viagem(hora=time(8))
        form = ViagemForm(data=self.dados_viagem(horario_previsto="09:00"))
        self.assertIn("horario_previsto", form.errors)
        form_ok = ViagemForm(data=self.dados_viagem(horario_previsto="11:00"))
        self.assertTrue(form_ok.is_valid(), form_ok.errors)


class CancelamentoMantemHistorico(Base):
    def test_cancelar_mantem_registro(self):
        v = self.criar_viagem()
        self.client.force_login(self.usuarios[perfis.AGENDADOR])
        r = self.client.post(reverse("viagens:cancelar", args=[v.pk]), {"motivo": "Cliente remarcou"})
        self.assertRedirects(r, reverse("viagens:detalhe", args=[v.pk]))
        v.refresh_from_db()
        self.assertEqual(v.status, Status.CANCELADA)
        self.assertEqual(v.motivo_cancelamento, "Cliente remarcou")
        self.assertTrue(Viagem.objects.filter(pk=v.pk).exists())

    def test_viagem_cancelada_nao_pode_ser_alterada(self):
        v = self.criar_viagem(status=Status.CANCELADA)
        self.client.force_login(self.usuarios[perfis.AGENDADOR])
        r = self.client.get(reverse("viagens:editar", args=[v.pk]))
        self.assertRedirects(r, reverse("viagens:detalhe", args=[v.pk]))


class Custos(Base):
    def test_valor_total_do_abastecimento_e_calculado(self):
        a = Abastecimento.objects.create(
            aeronave=self.aeronave, quantidade_litros=Decimal("300"), tipo_combustivel="qav1",
            valor_litro=Decimal("8.455"), local="SNBS", registrado_por=self.usuarios[perfis.OPERACIONAL],
        )
        self.assertEqual(a.valor_total, Decimal("2536.50"))

    def test_custo_total_soma_despesas_e_combustivel_sem_duplicar(self):
        v = self.criar_viagem()
        op = self.usuarios[perfis.OPERACIONAL]
        for valor in ("100", "50"):
            v.custos.create(tipo="taxas", valor=Decimal(valor), descricao="Taxa", registrado_por=op)
        for litros in ("10", "20"):
            Abastecimento.objects.create(aeronave=self.aeronave, viagem=v, quantidade_litros=Decimal(litros),
                                         tipo_combustivel="qav1", valor_litro=Decimal("10"), local="X", registrado_por=op)
        anotada = Viagem.objects.com_totais().get(pk=v.pk)
        self.assertEqual(anotada.custo_despesas, Decimal("150"))
        self.assertEqual(anotada.custo_combustivel, Decimal("300"))
        self.assertEqual(anotada.custo_total, Decimal("450"))


class ControleDeAcesso(Base):
    def test_anonimo_vai_para_login(self):
        r = self.client.get(reverse("viagens:lista"))
        self.assertRedirects(r, f"{reverse('contas:login')}?next={reverse('viagens:lista')}")

    def test_operacional_nao_agenda_e_nao_ve_indicadores(self):
        self.client.force_login(self.usuarios[perfis.OPERACIONAL])
        self.assertEqual(self.client.get(reverse("viagens:criar")).status_code, 403)
        self.assertEqual(self.client.get(reverse("painel:dashboard")).status_code, 403)

    def test_gestor_ve_indicadores(self):
        self.client.force_login(self.usuarios[perfis.GESTOR])
        self.assertEqual(self.client.get(reverse("painel:dashboard")).status_code, 200)

    def test_agendador_cria_viagem_como_responsavel(self):
        agendador = self.usuarios[perfis.AGENDADOR]
        self.client.force_login(agendador)
        r = self.client.post(reverse("viagens:criar"), self.dados_viagem())
        v = Viagem.objects.get()
        self.assertRedirects(r, reverse("viagens:detalhe", args=[v.pk]))
        self.assertEqual(v.responsavel, agendador)

    def test_somente_administrador_gerencia_usuarios(self):
        self.client.force_login(self.usuarios[perfis.GESTOR])
        self.assertEqual(self.client.get(reverse("contas:usuarios")).status_code, 403)
        self.client.force_login(self.usuarios[perfis.ADMINISTRADOR])
        self.assertEqual(self.client.get(reverse("contas:usuarios")).status_code, 200)


class TelasRenderizam(Base):
    """Smoke test: todas as telas principais abrem sem erro para o administrador."""

    def test_telas(self):
        v = self.criar_viagem()
        self.client.force_login(self.usuarios[perfis.ADMINISTRADOR])
        urls = [
            reverse("painel:inicio"), reverse("painel:dashboard"), reverse("viagens:lista"),
            reverse("viagens:lista") + "?aba=historico&finalidade=visita_filial", reverse("viagens:criar"),
            reverse("viagens:detalhe", args=[v.pk]), reverse("viagens:editar", args=[v.pk]),
            reverse("viagens:cancelar", args=[v.pk]), reverse("viagens:custo_criar", args=[v.pk]),
            reverse("viagens:abastecimentos"), reverse("viagens:abastecimento_criar"),
            reverse("viagens:passageiros"), reverse("viagens:passageiro_criar"),
            reverse("frota:aeronaves"), reverse("frota:aeronave_criar"),
            reverse("contas:usuarios"), reverse("contas:usuario_criar"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
