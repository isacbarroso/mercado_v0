"""
main.py - mercado_v0 (versão Android, feita com Kivy)

Duas abas:
 - Nova Compra: cole o link da nota (copiado do QR code), busque os dados,
   confira/adicione produtos e salve.
 - Histórico: compras salvas e sequência de dias usando o app.
"""

import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.textinput import TextInput

import db
import scanner

Window.softinput_mode = "below_target"  # teclado não cobre o campo digitado


def aviso(titulo, mensagem):
    caixa = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12))
    texto = Label(text=mensagem, halign="center", valign="middle")
    texto.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
    botao = Button(text="OK", size_hint_y=None, height=dp(44))
    caixa.add_widget(texto)
    caixa.add_widget(botao)
    popup = Popup(title=titulo, content=caixa, size_hint=(0.9, 0.5))
    botao.bind(on_release=popup.dismiss)
    popup.open()


def lista_rolavel():
    rolagem = ScrollView()
    grade = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
    grade.bind(minimum_height=grade.setter("height"))
    rolagem.add_widget(grade)
    return rolagem, grade


class AbaNovaCompra(BoxLayout):
    def __init__(self, ao_salvar, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(8), **kwargs)
        self.ao_salvar = ao_salvar
        self.itens = []

        self.add_widget(Label(text="Nova compra", size_hint_y=None, height=dp(30), bold=True))

        linha_url = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.campo_url = TextInput(hint_text="Link da nota", multiline=False)
        botao_colar = Button(text="Colar", size_hint_x=None, width=dp(80))
        botao_colar.bind(on_release=self.colar)
        linha_url.add_widget(self.campo_url)
        linha_url.add_widget(botao_colar)
        self.add_widget(linha_url)

        self.botao_buscar = Button(text="Buscar dados do link", size_hint_y=None, height=dp(44))
        self.botao_buscar.bind(on_release=self.buscar)
        self.add_widget(self.botao_buscar)

        self.campo_mercado = TextInput(hint_text="Mercado", multiline=False, size_hint_y=None, height=dp(44))
        self.add_widget(self.campo_mercado)

        linha_item = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.campo_produto = TextInput(hint_text="Produto", multiline=False)
        self.campo_preco = TextInput(hint_text="Preço", multiline=False, size_hint_x=None, width=dp(90))
        botao_add = Button(text="+", size_hint_x=None, width=dp(50))
        botao_add.bind(on_release=self.adicionar_manual)
        linha_item.add_widget(self.campo_produto)
        linha_item.add_widget(self.campo_preco)
        linha_item.add_widget(botao_add)
        self.add_widget(linha_item)

        self.rolagem, self.grade_itens = lista_rolavel()
        self.add_widget(self.rolagem)

        botao_salvar = Button(text="Salvar compra", size_hint_y=None, height=dp(52))
        botao_salvar.bind(on_release=self.salvar)
        self.add_widget(botao_salvar)

    def colar(self, *_):
        texto = (Clipboard.paste() or "").strip()
        if texto:
            self.campo_url.text = texto
        else:
            aviso("Área de transferência vazia", "Copie o link da nota primeiro.")

    def buscar(self, *_):
        url = self.campo_url.text.strip()
        if not url:
            aviso("Link vazio", "Cole o link da nota antes de buscar.")
            return
        self.botao_buscar.text = "Buscando..."
        self.botao_buscar.disabled = True
        threading.Thread(target=self._buscar_em_segundo_plano, args=(url,), daemon=True).start()

    def _buscar_em_segundo_plano(self, url):
        dados = scanner.extrair_dados_da_nota(url)
        Clock.schedule_once(lambda dt: self._depois_da_busca(dados), 0)

    def _depois_da_busca(self, dados):
        self.botao_buscar.text = "Buscar dados do link"
        self.botao_buscar.disabled = False

        if dados["mercado"]:
            self.campo_mercado.text = dados["mercado"]

        if dados["itens"]:
            self.itens.extend(dados["itens"])
            self.redesenhar()
            aviso("Encontrado", f"{len(dados['itens'])} produto(s) identificado(s).")
        else:
            aviso(
                "Não consegui ler os produtos",
                "Não reconheci essa página (ou ela está fora do ar).\n"
                "Preencha o mercado e adicione os produtos manualmente.",
            )

    def adicionar_manual(self, *_):
        produto = self.campo_produto.text.strip()
        try:
            preco = float(self.campo_preco.text.strip().replace(",", "."))
        except ValueError:
            aviso("Preço inválido", "Digite um preço válido, ex: 5,99")
            return
        if not produto:
            aviso("Falta o produto", "Digite o nome do produto.")
            return
        self.itens.append({"produto": produto, "preco": preco, "quantidade": 1})
        self.campo_produto.text = ""
        self.campo_preco.text = ""
        self.redesenhar()

    def remover(self, indice):
        del self.itens[indice]
        self.redesenhar()

    def redesenhar(self):
        self.grade_itens.clear_widgets()
        for i, item in enumerate(self.itens):
            linha = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            texto = Label(text=f"{item['produto']} - R$ {item['preco']:.2f}", halign="left", valign="middle")
            texto.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], val[1])))
            botao = Button(text="X", size_hint_x=None, width=dp(44))
            botao.bind(on_release=lambda _b, i=i: self.remover(i))
            linha.add_widget(texto)
            linha.add_widget(botao)
            self.grade_itens.add_widget(linha)

    def salvar(self, *_):
        mercado = self.campo_mercado.text.strip()
        if not mercado:
            aviso("Falta o mercado", "Digite o nome do mercado.")
            return
        if not self.itens:
            aviso("Sem produtos", "Adicione pelo menos um produto.")
            return

        db.salvar_compra(mercado, self.itens, url_nota=self.campo_url.text.strip() or None)

        self.itens = []
        self.redesenhar()
        self.campo_mercado.text = ""
        self.campo_url.text = ""
        self.ao_salvar()
        aviso("Compra salva!", "Sua compra foi registrada.")


class AbaHistorico(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(8), **kwargs)
        self.label_streak = Label(text="", size_hint_y=None, height=dp(40), bold=True)
        self.add_widget(self.label_streak)
        self.rolagem, self.grade = lista_rolavel()
        self.add_widget(self.rolagem)
        self.atualizar()

    def atualizar(self):
        streak = db.contar_streak_dias()
        if streak > 0:
            self.label_streak.text = f"Sequência: {streak} dia(s) seguido(s)"
        else:
            self.label_streak.text = "Registre uma compra hoje para começar sua sequência!"

        self.grade.clear_widgets()
        for compra_id, mercado, data in db.listar_compras():
            botao = Button(text=f"{data} - {mercado}", size_hint_y=None, height=dp(48))
            botao.bind(on_release=lambda _b, cid=compra_id, m=mercado: self.mostrar(cid, m))
            self.grade.add_widget(botao)

    def mostrar(self, compra_id, mercado):
        itens = db.listar_itens_da_compra(compra_id)
        texto = "\n".join(f"{p} - R$ {preco:.2f}" for p, preco, _q in itens) or "Sem itens."
        aviso(mercado, texto)


class MercadoApp(App):
    title = "mercado_v0"

    def build(self):
        db.CAMINHO_BANCO = os.path.join(self.user_data_dir, "mercado.db")
        db.criar_tabelas()

        painel = TabbedPanel(do_default_tab=False, tab_width=dp(140))

        historico = AbaHistorico()
        nova = AbaNovaCompra(ao_salvar=historico.atualizar)

        aba1 = TabbedPanelItem(text="Nova Compra")
        aba1.add_widget(nova)
        aba2 = TabbedPanelItem(text="Histórico")
        aba2.add_widget(historico)

        painel.add_widget(aba1)
        painel.add_widget(aba2)
        painel.default_tab = aba1
        return painel


if __name__ == "__main__":
    MercadoApp().run()
