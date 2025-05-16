import flet as ft
from datetime import datetime
import sqlite3
import threading
import locale
from decimal import Decimal

# Configurar locale para formato brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')

class Database:
    _local = threading.local()
    
    def __init__(self, db_name='sistema_vendas.db'):
        self.db_name = db_name
    
    def get_conn(self):
        if not hasattr(Database._local, 'conn'):
            Database._local.conn = sqlite3.connect(self.db_name)
            Database._local.cursor = Database._local.conn.cursor()
            self.create_tables()
        return Database._local.conn, Database._local.cursor
    
    def create_tables(self):
        conn, cursor = self.get_conn()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT,
                quantidade INTEGER NOT NULL CHECK(quantidade >= 0),
                preco REAL NOT NULL CHECK(preco > 0)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                quantidade INTEGER NOT NULL CHECK(quantidade > 0),
                data_venda TEXT NOT NULL,
                valor_total REAL NOT NULL,
                FOREIGN KEY (produto_id) REFERENCES produtos (id) ON DELETE RESTRICT
            )
        ''')
        conn.commit()
    
    def close(self):
        if hasattr(Database._local, 'conn'):
            Database._local.conn.close()
            del Database._local.conn
            del Database._local.cursor

class Produto:
    def __init__(self, id=None, nome='', descricao='', quantidade=0, preco=0.0):
        self.id = id
        self.nome = nome
        self.descricao = descricao
        self.quantidade = quantidade
        self.preco = preco
    
    def salvar(self, db):
        conn, cursor = db.get_conn()
        try:
            if self.id is None:
                cursor.execute('''
                    INSERT INTO produtos (nome, descricao, quantidade, preco)
                    VALUES (?, ?, ?, ?)
                ''', (self.nome, self.descricao, self.quantidade, float(self.preco)))
                self.id = cursor.lastrowid
            else:
                cursor.execute('''
                    UPDATE produtos 
                    SET nome=?, descricao=?, quantidade=?, preco=?
                    WHERE id=?
                ''', (self.nome, self.descricao, self.quantidade, float(self.preco), self.id))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
    
    def remover(self, db):
        if self.id is not None:
            conn, cursor = db.get_conn()
            try:
                cursor.execute('DELETE FROM produtos WHERE id=?', (self.id,))
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                raise ValueError(f"Erro ao remover produto: {str(e)}")
    
    @staticmethod
    def buscar_todos(db):
        _, cursor = db.get_conn()
        cursor.execute('SELECT * FROM produtos ORDER BY nome')
        return [Produto(id=row[0], nome=row[1], descricao=row[2], quantidade=row[3], preco=row[4]) 
                for row in cursor.fetchall()]
    
    @staticmethod
    def buscar_por_id(db, id):
        _, cursor = db.get_conn()
        cursor.execute('SELECT * FROM produtos WHERE id=?', (id,))
        row = cursor.fetchone()
        if row:
            return Produto(id=row[0], nome=row[1], descricao=row[2], quantidade=row[3], preco=row[4])
        return None
    
    @staticmethod
    def buscar_por_nome(db, nome):
        _, cursor = db.get_conn()
        cursor.execute('SELECT * FROM produtos WHERE nome LIKE ?', (f"%{nome}%",))
        row = cursor.fetchone()
        if row:
            return Produto(id=row[0], nome=row[1], descricao=row[2], quantidade=row[3], preco=row[4])
        return None

class Venda:
    def __init__(self, id=None, produto_id=None, quantidade=0, data_venda=None, valor_total=0.0):
        self.id = id
        self.produto_id = produto_id
        self.quantidade = quantidade
        self.data_venda = data_venda or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.valor_total = valor_total
    
    def registrar(self, db):
        produto = Produto.buscar_por_id(db, self.produto_id)
        if not produto:
            raise ValueError("Produto não encontrado")
        if produto.quantidade < self.quantidade:
            raise ValueError(f"Estoque insuficiente. Disponível: {produto.quantidade}")
        
        # Corrigido o cálculo do valor total
        self.valor_total = float(Decimal(str(produto.preco)) * self.quantidade)
        
        conn, cursor = db.get_conn()
        try:
            cursor.execute('''
                INSERT INTO vendas (produto_id, quantidade, data_venda, valor_total)
                VALUES (?, ?, ?, ?)
            ''', (self.produto_id, self.quantidade, self.data_venda, self.valor_total))
            self.id = cursor.lastrowid
            
            produto.quantidade -= self.quantidade
            produto.salvar(db)
            
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise ValueError(f"Erro ao registrar venda: {str(e)}")
    
    @staticmethod
    def buscar_todas(db):
        _, cursor = db.get_conn()
        cursor.execute('''
            SELECT v.id, v.produto_id, v.quantidade, v.data_venda, v.valor_total, 
                   p.nome, p.descricao
            FROM vendas v
            JOIN produtos p ON v.produto_id = p.id
            ORDER BY v.data_venda DESC
        ''')
        vendas = []
        for row in cursor.fetchall():
            venda = Venda(
                id=row[0], 
                produto_id=row[1], 
                quantidade=row[2], 
                data_venda=row[3],
                valor_total=row[4]
            )
            venda.nome_produto = row[5]
            venda.descricao_produto = row[6]
            vendas.append(venda)
        return vendas
    
    @staticmethod
    def calcular_total_vendas(db):
        _, cursor = db.get_conn()
        cursor.execute('SELECT SUM(valor_total) FROM vendas')
        total = cursor.fetchone()[0]
        return total or 0.0

class CurrencyTextField(ft.TextField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prefix_text = "R$ "  # Exibe "R$ " antes do número
        self.on_change = self.format_currency  # Chama a formatação ao alterar o valor

    def format_currency(self, e):
        value = e.control.value.replace("R$ ", "").strip()  # Remove "R$ " e espaços extras

        if not value:  
            return  # Se o campo estiver vazio, não faz nada (permite limpar)

        value = value.replace(".", "").replace(",", ".")  # Converte para o formato numérico

class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.db = Database()
        self.setup_page()
        self.setup_routes()
        self.page.go("/")
    
    def setup_page(self):
        self.page.title = "Sistema de Vendas"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window_width = 1100
        self.page.window_height = 750
        self.page.padding = 20
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    def setup_routes(self):
        self.routes = {
            "/": self.home_page,
            "/adicionar": self.adicionar_page,
            "/crud": self.crud_page,
            "/vendas": self.vendas_page,
            "/configurar": self.configurar_produtos_page
        }
        self.page.on_route_change = self.route_change
    
    def route_change(self, e):
        self.page.views.clear()
        self.routes[self.page.route]()
        self.page.update()
    
    def create_nav_bar(self):
        return ft.AppBar(
            title=ft.Text("Sistema de Vendas"),
            center_title=True,
            bgcolor=ft.Colors.BLUE_700,
            actions=[
                ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(text="Início", on_click=lambda _: self.page.go("/")),
                        ft.PopupMenuItem(text="Adicionar Produto", on_click=lambda _: self.page.go("/adicionar")),
                        ft.PopupMenuItem(text="Gerenciar Produtos", on_click=lambda _: self.page.go("/crud")),
                        ft.PopupMenuItem(text="Registrar Vendas", on_click=lambda _: self.page.go("/vendas")),
                        ft.PopupMenuItem(text="Configurar Produtos", on_click=lambda _: self.page.go("/configurar")),
                    ]
                ),
            ],
        )
    
    def home_page(self):
        content = ft.Column(
            controls=[
                ft.Text("Bem-vindo ao Sistema de Vendas", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Selecione uma opção no menu superior para começar."),
                ft.Image(
                    src="https://cdn-icons-png.flaticon.com/512/3144/3144456.png",
                    width=200,
                    height=200,
                    fit=ft.ImageFit.CONTAIN,
                ),
                ft.ElevatedButton(
                    "Ver Relatório de Vendas",
                    on_click=lambda _: self.page.go("/vendas"),
                    icon=ft.Icons.BAR_CHART,
                ),
            ],
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
        
        self.page.views.append(
            ft.View(
                "/",
                [self.create_nav_bar(), content],
                padding=20,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        self.page.update()
    
    def adicionar_page(self):
        self.nome_field = ft.TextField(label="Nome do Produto", width=400)
        self.descricao_field = ft.TextField(label="Descrição", multiline=True, width=400)
        self.quantidade_field = ft.TextField(
            label="Quantidade", 
            input_filter=ft.NumbersOnlyInputFilter(),
            width=400
        )
        self.preco_field = CurrencyTextField(label="Preço", width=400)
        self.status_message = ft.Text("", color=ft.Colors.RED_500)
        
        form = ft.Column(
            controls=[
                ft.Text("Adicionar Novo Produto", size=25, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                self.nome_field,
                self.descricao_field,
                self.quantidade_field,
                self.preco_field,
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Salvar",
                            on_click=self.salvar_produto,
                            icon=ft.Icons.SAVE,
                        ),
                        ft.ElevatedButton(
                            "Cancelar",
                            on_click=lambda _: self.page.go("/"),
                            icon=ft.Icons.CANCEL,
                        ),
                    ],
                    spacing=20,
                ),
                self.status_message,
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
        
        self.page.views.append(
            ft.View(
                "/adicionar",
                [self.create_nav_bar(), form],
                padding=20,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        self.page.update()
    
    def salvar_produto(self, e):
        try:
            # Converter o preço para float
            preco_str = self.preco_field.value.replace("R$ ", "").replace(".", "").replace(",", ".")
            preco = float(preco_str) if preco_str else 0.0
            
            produto = Produto(
                nome=self.nome_field.value.strip(),
                descricao=self.descricao_field.value.strip(),
                quantidade=int(self.quantidade_field.value) if self.quantidade_field.value else 0,
                preco=preco
            )
            
            if not produto.nome:
                raise ValueError("O nome do produto é obrigatório")
            if produto.quantidade < 0:
                raise ValueError("A quantidade não pode ser negativa")
            if produto.preco <= 0:
                raise ValueError("O preço deve ser maior que zero")
            
            produto.salvar(self.db)
            self.status_message.value = "✅ Produto salvo com sucesso!"
            self.status_message.color = ft.Colors.GREEN
            self.clear_form()
        except ValueError as e:
            self.status_message.value = f"❌ Erro: {str(e)}"
            self.status_message.color = ft.Colors.RED
        except Exception as e:
            self.status_message.value = f"❌ Erro inesperado: {str(e)}"
            self.status_message.color = ft.Colors.RED
        
        self.status_message.update()
    
    def clear_form(self):
        self.nome_field.value = ""
        self.descricao_field.value = ""
        self.quantidade_field.value = ""
        self.preco_field.value = ""
        self.page.update()
    
    def crud_page(self):
        produtos = Produto.buscar_todos(self.db)
        
        self.search_field = ft.TextField(
            label="Buscar produto",
            on_change=self.buscar_produtos,
            width=400,
            suffix_icon=ft.Icons.SEARCH,
        )
        
        self.produtos_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Nome")),
                ft.DataColumn(ft.Text("Descrição")),
                ft.DataColumn(ft.Text("Quantidade")),
                ft.DataColumn(ft.Text("Preço")),
            ],
            rows=self.get_produto_rows(produtos),
            width=900,
        )
        
        content = ft.Column(
            controls=[
                ft.Text("Gerenciar Produtos", size=25, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row(
                    controls=[
                        self.search_field,
                        ft.ElevatedButton(
                            "Adicionar Novo",
                            on_click=lambda _: self.page.go("/adicionar"),
                            icon=ft.Icons.ADD,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=ft.ListView(
                        controls=[self.produtos_table],
                        height=400,
                    ),
                    padding=10,
                ),
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
        )
        
        self.page.views.append(
            ft.View(
                "/crud",
                [self.create_nav_bar(), content],
                padding=20,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        self.page.update()
    
    def get_produto_rows(self, produtos):
        rows = []
        for produto in produtos:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(produto.nome)),
                        ft.DataCell(ft.Text(produto.descricao[:50] + ("..." if len(produto.descricao) > 50 else ""))),
                        ft.DataCell(ft.Text(str(produto.quantidade))),
                        ft.DataCell(ft.Text(locale.currency(produto.preco, grouping=True, symbol=False))),
                    ]
                )
            )
        return rows
    
    def buscar_produtos(self, e):
        termo = self.search_field.value.strip()
        if termo:
            produtos = [p for p in Produto.buscar_todos(self.db) if termo.lower() in p.nome.lower()]
        else:
            produtos = Produto.buscar_todos(self.db)
        
        self.produtos_table.rows = self.get_produto_rows(produtos)
        self.produtos_table.update()
    
    def vendas_page(self):
        produtos = Produto.buscar_todos(self.db)
        self.produto_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(key=p.id, text=p.nome) for p in produtos],
            label="Selecione o Produto",
            width=400,
        )
        self.quantidade_venda = ft.TextField(
            label="Quantidade",
            input_filter=ft.NumbersOnlyInputFilter(),
            width=400,
        )
        self.venda_status = ft.Text("", color=ft.Colors.RED_500)
        
        # Tabela de vendas recentes
        vendas = Venda.buscar_todas(self.db)[:10]
        vendas_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Produto")),
                ft.DataColumn(ft.Text("Quantidade")),
                ft.DataColumn(ft.Text("Total")),
                ft.DataColumn(ft.Text("Data")),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(v.nome_produto)),
                        ft.DataCell(ft.Text(str(v.quantidade))),
                        ft.DataCell(ft.Text(locale.currency(v.valor_total, grouping=True))),
                        ft.DataCell(ft.Text(v.data_venda)),
                    ]
                ) for v in vendas
            ],
            width=900,
        )
        
        # Relatório de vendas
        total_vendas = Venda.calcular_total_vendas(self.db)
        relatorio = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Relatório de Vendas", size=20, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Text(f"Total de Vendas: {locale.currency(total_vendas, grouping=True)}", size=16),
                    ],
                    spacing=10,
                ),
                padding=15,
            ),
            width=900,
        )
        
        content = ft.Column(
            controls=[
                ft.Text("Registrar Venda", size=25, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row(
                    controls=[
                        self.produto_dropdown,
                        self.quantidade_venda,
                    ],
                    spacing=20,
                ),
                ft.ElevatedButton(
                    "Registrar Venda",
                    on_click=self.registrar_venda,
                    icon=ft.Icons.SHOPPING_CART,
                ),
                self.venda_status,
                ft.Divider(),
                relatorio,
                ft.Text("Últimas Vendas", size=20),
                ft.Container(
                    content=ft.ListView(
                        controls=[vendas_table],
                        height=300,
                    ),
                    padding=10,
                ),
            ],
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
        
        self.page.views.append(
            ft.View(
                "/vendas",
                [self.create_nav_bar(), content],
                padding=20,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        self.page.update()
    
    def registrar_venda(self, e):
        if not self.produto_dropdown.value:
            self.venda_status.value = "❌ Selecione um produto"
            self.venda_status.update()
            return
        
        if not self.quantidade_venda.value or int(self.quantidade_venda.value) <= 0:
            self.venda_status.value = "❌ Informe uma quantidade válida"
            self.venda_status.update()
            return
        
        try:
            venda = Venda(
                produto_id=int(self.produto_dropdown.value),
                quantidade=int(self.quantidade_venda.value),
            )
            
            venda.registrar(self.db)
            self.venda_status.value = "✅ Venda registrada com sucesso!"
            self.venda_status.color = ft.Colors.GREEN
            self.quantidade_venda.value = ""
            self.page.go("/vendas") 
            self.venda_status.update() # Recarrega a página para atualizar os dados  
        except ValueError as e:
            self.venda_status.value = f"❌ {str(e)}"
            self.venda_status.color = ft.Colors.RED
            self.venda_status.update()

    def configurar_produtos_page(self):
        produtos = Produto.buscar_todos(self.db)
        
        self.produto_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(key=p.id, text=p.nome) for p in produtos],
            label="Selecione o Produto",
            width=400,
            on_change=self.on_produto_selecionado
        )
        
        self.edit_nome = ft.TextField(label="Nome", width=400)
        self.edit_descricao = ft.TextField(label="Descrição", multiline=True, width=400)
        self.edit_quantidade = ft.TextField(label="Quantidade", width=400, input_filter=ft.NumbersOnlyInputFilter())
        self.edit_preco = CurrencyTextField(label="Preço", width=400)
        
        self.status_message = ft.Text("", color=ft.Colors.RED_500)
        
        form = ft.Column(
            controls=[
                ft.Text("Configurar Produto", size=25, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                self.produto_dropdown,
                self.edit_nome,
                self.edit_descricao,
                self.edit_quantidade,
                self.edit_preco,
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Salvar Alterações",
                            on_click=self.salvar_alteracoes,
                            icon=ft.Icons.SAVE,
                        ),
                        ft.ElevatedButton(
                            "Excluir Produto",
                            on_click=self.excluir_produto,
                            icon=ft.Icons.DELETE,
                            icon_color=ft.Colors.RED,
                        ),
                    ],
                    spacing=20,
                ),
                self.status_message,
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
        
        self.page.views.append(
            ft.View(
                "/configurar",
                [self.create_nav_bar(), form],
                padding=20,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        self.page.update()
    
    def on_produto_selecionado(self, e):
        produto_id = self.produto_dropdown.value
        if produto_id:
            produto = Produto.buscar_por_id(self.db, produto_id)
            if produto:
                self.edit_nome.value = produto.nome
                self.edit_descricao.value = produto.descricao
                self.edit_quantidade.value = str(produto.quantidade)
                self.edit_preco.value = locale.currency(produto.preco, grouping=True, symbol=False)
                self.page.update()
    
    def salvar_alteracoes(self, e):
        try:
            produto_id = self.produto_dropdown.value
            if not produto_id:
                raise ValueError("Selecione um produto para editar.")
            
            produto = Produto.buscar_por_id(self.db, produto_id)
            if not produto:
                raise ValueError("Produto não encontrado.")
            
            produto.nome = self.edit_nome.value.strip()
            produto.descricao = self.edit_descricao.value.strip()
            produto.quantidade = int(self.edit_quantidade.value)
            preco_str = self.edit_preco.value.replace("R$ ", "").replace(".", "").replace(",", ".")
            produto.preco = float(preco_str) if preco_str else 0.0
            
            if not produto.nome:
                raise ValueError("O nome do produto é obrigatório.")
            if produto.quantidade < 0:
                raise ValueError("A quantidade não pode ser negativa.")
            if produto.preco <= 0:
                raise ValueError("O preço deve ser maior que zero.")
            
            produto.salvar(self.db)
            self.status_message.value = "✅ Produto atualizado com sucesso!"
            self.status_message.color = ft.Colors.GREEN
            self.page.update()
        except ValueError as e:
            self.status_message.value = f"❌ Erro: {str(e)}"
            self.status_message.color = ft.Colors.RED
            self.page.update()
    
    def excluir_produto(self, e):
        produto_id = self.produto_dropdown.value
        if not produto_id:
            self.status_message.value = "❌ Selecione um produto para excluir."
            self.status_message.color = ft.Colors.RED
            self.page.update()
            return
        
        produto = Produto.buscar_por_id(self.db, produto_id)
        if not produto:
            self.status_message.value = "❌ Produto não encontrado."
            self.status_message.color = ft.Colors.RED
            self.page.update()
            return
        
        def confirmar_remocao(e):
            try:
                produto.remover(self.db)
                self.status_message.value = "✅ Produto removido com sucesso!"
                self.status_message.color = ft.Colors.GREEN
                
                # Atualiza o dropdown de produtos
                self.produto_dropdown.options = [ft.dropdown.Option(key=p.id, text=p.nome) for p in Produto.buscar_todos(self.db)]
                self.produto_dropdown.value = None  # Limpa a seleção do dropdown
                
                # Limpa os campos de edição
                self.edit_nome.value = ""
                self.edit_descricao.value = ""
                self.edit_quantidade.value = ""
                self.edit_preco.value = ""
                self.page.update()
            except ValueError as e:
                self.status_message.value = f"❌ Não foi possível remover: {str(e)}"
                self.status_message.color = ft.Colors.RED
                self.page.update()
        
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Confirmar remoção"),
            content=ft.Text(f"Deseja realmente remover o produto {produto.nome}?"),
            actions=[
                ft.TextButton("Cancelar", on_click=self.fechar_dialog),
                ft.TextButton("Confirmar", on_click=confirmar_remocao),
            ],
        )
        self.page.dialog.open = True
        self.page.update()
    
    def fechar_dialog(self, e=None):
        self.page.dialog.open = False
        self.page.update()

def main(page: ft.Page):
    app = App(page)

if __name__ == "__main__":
    ft.app(target=main)

