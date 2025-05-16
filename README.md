# app_gereciamento_estoque
Sistema de gerenciamento de estoque

Sistema de Vendas com Flet e SQLite
Este projeto é um sistema completo de gerenciamento de vendas, desenvolvido em Python utilizando o framework de interface gráfica Flet e o banco de dados SQLite. A aplicação foi projetada para ser simples, intuitiva e eficiente, permitindo o controle de produtos, registro de vendas e geração de relatórios de maneira integrada e visualmente agradável.

Principais funcionalidades:
Cadastro e gerenciamento de produtos:

Adição de novos produtos com nome, descrição, quantidade e preço.

Edição e exclusão de produtos existentes.

Validações de entrada, como verificação de preço positivo e quantidade não negativa.

Registro de vendas:

Seleção de produtos disponíveis e definição da quantidade a ser vendida.

Atualização automática do estoque após cada venda.

Cálculo do valor total da venda com base no preço unitário e na quantidade.

Relatórios e histórico de vendas:

Exibição das últimas vendas realizadas com dados como produto, quantidade, valor total e data.

Cálculo do total geral vendido.

Visualização em tabela dinâmica com rolagem.

Interface gráfica moderna e responsiva:

Uso de AppBar, PopupMenu, DataTable, ListView, Dropdown e campos personalizados como CurrencyTextField.

Layout responsivo com rolagem automática e menus acessíveis.

Banco de dados local (SQLite):

Tabelas persistentes para produtos e vendas.

Relacionamentos entre vendas e produtos com integridade referencial.

Tecnologias utilizadas:
Python 3

Flet para interface gráfica

SQLite3 para persistência de dados

Thread-local para conexão segura com o banco em ambientes multi-thread

Locale pt-BR para formatação monetária


