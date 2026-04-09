import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, date
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from dateutil.relativedelta import relativedelta

class ControleGastos:
    def __init__(self, root):
        self.root = root
        self.root.title("Controle de Gastos v3.1 - Cartões Fixo")
        self.root.geometry("1100x800")
        
        self.conn = sqlite3.connect('gastos.db')
        self.cursor = self.conn.cursor()
        self.criar_tabelas_corretas()  # CORRIGIDO
        self.carregar_cartoes_db()
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.tree_todos = self.tree_diario = self.tree_cartoes = self.tree_parcelas = self.tree_cats = None
        self.canvas_todos = self.canvas_diario = self.canvas_cartoes = self.canvas_parcelas = self.canvas_cats = None
        
        self.frame_todos = ttk.Frame(self.notebook); self.notebook.add(self.frame_todos, text="Todos"); self.carregar_todos()
        self.frame_diario = ttk.Frame(self.notebook); self.notebook.add(self.frame_diario, text="Diários"); self.carregar_diario()
        self.frame_cartoes = ttk.Frame(self.notebook); self.notebook.add(self.frame_cartoes, text="Cartões"); self.carregar_cartoes_ui()
        self.frame_parcelas = ttk.Frame(self.notebook); self.notebook.add(self.frame_parcelas, text="Parcelas"); self.carregar_parcelas()
        self.frame_categorias = ttk.Frame(self.notebook); self.notebook.add(self.frame_categorias, text="Categorias"); self.carregar_categorias()
        
        self.frame_insert = ttk.Frame(root)
        self.frame_insert.pack(fill='x', padx=10, pady=(0,10))
        self.criar_form_insert()
        
        self.notebook.bind('<<NotebookTabChanged>>', lambda e: self.atualizar_todas_abas())
        self.atualizar_todas_abas()
    
    def criar_tabelas_corretas(self):
        # CORRIGIDO: Tabela cartoes com 1 coluna apenas (nome é PK)
        self.cursor.execute('''DROP TABLE IF EXISTS cartoes''')  # Remove tabela antiga
        self.cursor.execute('''CREATE TABLE cartoes (nome TEXT PRIMARY KEY)''')
        
        # Tabela gastos
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, data DATE, cartao TEXT,
            total_parcelas INTEGER DEFAULT 1, parcela_atual INTEGER DEFAULT 1,
            juros_rate REAL DEFAULT 0, categoria TEXT DEFAULT 'Geral', status TEXT DEFAULT 'Aberta')''')
        self.conn.commit()
        print("✅ Tabelas criadas corretamente!")
    
    def carregar_cartoes_db(self):
        self.cursor.execute("SELECT nome FROM cartoes ORDER BY nome")
        self.cartoes_disponiveis = [row[0] for row in self.cursor.fetchall()]
        print(f"✅ {len(self.cartoes_disponiveis)} cartões carregados")
    
    def salvar_cartao(self, nome):
        nome = nome.strip()
        if nome and nome not in self.cartoes_disponiveis:
            try:
                self.cursor.execute("INSERT INTO cartoes (nome) VALUES (?)", (nome,))
                self.conn.commit()
                self.cartoes_disponiveis.append(nome)
                self.entry_cartao['values'] = self.cartoes_disponiveis
                print(f"✅ Cartão '{nome}' salvo!")
            except sqlite3.IntegrityError:
                print(f"ℹ️ Cartão '{nome}' já existe")
    
    # RESTO DO CÓDIGO IGUAL (criar_form_insert, adicionar_gasto, etc.)
    def criar_form_insert(self):
        labels = ['Descrição:', 'Valor:', 'Data:', 'Cartão:', 'Parcelas:', 'Juros %:', 'Categoria:']
        self.entries = {}
        for i, lbl in enumerate(labels):
            ttk.Label(self.frame_insert, text=lbl).grid(row=0, column=i*2, padx=2, sticky='e')
            if 'Cartão' in lbl:
                self.entry_cartao = ttk.Combobox(self.frame_insert, values=self.cartoes_disponiveis, width=12)
                self.entry_cartao.grid(row=0, column=i*2+1, padx=2)
                self.entry_cartao.bind('<FocusOut>', lambda e: self.salvar_cartao(self.entry_cartao.get()))
            elif 'Categoria' in lbl:
                self.entries['Categoria'] = ttk.Combobox(self.frame_insert, values=['Geral','Alimentação','Transporte','Lazer','Saúde','Moradia'], width=12)
                self.entries['Categoria'].grid(row=0, column=i*2+1, padx=2)
            else:
                e = ttk.Entry(self.frame_insert, width=10)
                e.grid(row=0, column=i*2+1, padx=2)
                self.entries[lbl.split(':')[0]] = e
        
        self.entries['Data'].insert(0, date.today().strftime('%Y-%m-%d'))
        self.entries['Parcelas'].insert(0, '1')
        
        ttk.Button(self.frame_insert, text="➕ Adicionar", command=self.adicionar_gasto).grid(row=0, column=16, padx=5)
        ttk.Button(self.frame_insert, text="✅ Pagar", command=self.marcar_parcela_paga).grid(row=0, column=17, padx=5)
    
    def adicionar_gasto(self):
        try:
            cartao = self.entry_cartao.get().strip()
            self.salvar_cartao(cartao)
            
            desc = self.entries['Descrição'].get()
            valor = float(self.entries['Valor'].get())
            data_str = self.entries['Data'].get()
            parcelas = int(self.entries['Parcelas'].get())
            juros = float(self.entries['Juros %'].get() or 0)
            cat = self.entries['Categoria'].get() or 'Geral'
            
            data0 = datetime.strptime(data_str, '%Y-%m-%d').date()
            taxa = juros / 100
            
            for i in range(1, parcelas+1):
                d = (datetime.combine(data0, datetime.min.time()) + relativedelta(months=i-1)).date().strftime('%Y-%m-%d')
                v = (valor/parcelas) * ((1+taxa)**(i-1))
                self.cursor.execute("""INSERT INTO gastos (descricao, valor, data, cartao, total_parcelas, parcela_atual, juros_rate, categoria, status)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Aberta')""",
                                     (f"{desc} ({i}/{parcelas})", v, d, cartao, parcelas, i, juros, cat))
            
            self.conn.commit()
            messagebox.showinfo("✅", f"Adicionado {parcelas} parcelas!")
            self.limpar_entries()
            self.atualizar_todas_abas()
        except Exception as e:
            messagebox.showerror("❌", str(e))
    
    def limpar_entries(self):
        for e in self.entries.values():
            if hasattr(e, 'delete'): e.delete(0, tk.END)
        self.entry_cartao.set('')
        self.entries['Data'].insert(0, date.today().strftime('%Y-%m-%d'))
        self.entries['Parcelas'].insert(0, '1')
    
    def marcar_parcela_paga(self):
        self.cursor.execute("UPDATE gastos SET status='Paga' WHERE status='Aberta' ORDER BY data LIMIT 1")
        self.conn.commit()
        self.atualizar_todas_abas()
        messagebox.showinfo("✅", "Parcela paga!")
    
    def df_gastos(self, aberta=False):
        q = "SELECT * FROM gastos WHERE status='Aberta'" if aberta else "SELECT * FROM gastos"
        return pd.read_sql_query(q, self.conn)
    
    # MÉTODOS DAS ABAS (iguais ao anterior)
    def carregar_todos(self):
        self.tree_todos = ttk.Treeview(self.frame_todos, columns=list('DVDCC'), show='headings', height=15)
        self.tree_todos.pack(side='left', fill='both', expand=1)
        for c, txt in zip('DVDCC', ['Desc','Valor','Data','Cartão','Cat']): self.tree_todos.heading(c, text=txt)
        self.canvas_todos = tk.Frame(self.frame_todos); self.canvas_todos.pack(side='right', fill='both', expand=1)
    
    def carregar_diario(self):
        self.tree_diario = ttk.Treeview(self.frame_diario, columns=list('DT'), show='headings')
        self.tree_diario.pack(side='left', fill='both', expand=1)
        self.tree_diario.heading('D', text='Data'); self.tree_diario.heading('T', text='Total')
        self.canvas_diario = tk.Frame(self.frame_diario); self.canvas_diario.pack(side='right', fill='both', expand=1)
    
    def carregar_cartoes_ui(self):
        self.tree_cartoes = ttk.Treeview(self.frame_cartoes, columns=list('CT'), show='headings')
        self.tree_cartoes.pack(side='left', fill='both', expand=1)
        self.tree_cartoes.heading('C', text='Cartão'); self.tree_cartoes.heading('T', text='Total')
        self.canvas_cartoes = tk.Frame(self.frame_cartoes); self.canvas_cartoes.pack(side='right', fill='both', expand=1)
    
    def carregar_parcelas(self):
        self.tree_parcelas = ttk.Treeview(self.frame_parcelas, columns=list('DVDSE'), show='headings')
        self.tree_parcelas.pack(side='left', fill='both', expand=1)
        for c, txt in zip('DVDSE', ['Desc','Valor','Data','Status','Juros']): self.tree_parcelas.heading(c, text=txt)
        self.canvas_parcelas = tk.Frame(self.frame_parcelas); self.canvas_parcelas.pack(side='right', fill='both', expand=1)
    
    def carregar_categorias(self):
        self.tree_cats = ttk.Treeview(self.frame_categorias, columns=list('CT'), show='headings')
        self.tree_cats.pack(side='left', fill='both', expand=1)
        self.tree_cats.heading('C', text='Categoria'); self.tree_cats.heading('T', text='Total')
        self.canvas_cats = tk.Frame(self.frame_categorias); self.canvas_cats.pack(side='right', fill='both', expand=1)
    
    def limpar_grafico(self, canvas):
        for w in canvas.winfo_children(): w.destroy()
    
    def plot_grafico(self, canvas, dfg, titulo, kind='bar'):
        self.limpar_grafico(canvas)
        if not dfg.empty:
            fig, ax = plt.subplots(figsize=(6,4))
            if kind=='pie': dfg.plot(ax=ax, kind=kind, autopct='%1.1f%%')
            else: dfg.plot(ax=ax, kind=kind)
            ax.set_title(titulo); plt.xticks(rotation=45)
            c = FigureCanvasTkAgg(fig, canvas); c.draw(); c.get_tk_widget().pack(fill='both', expand=1)
    
    def atualizar_todos(self):
        for i in self.tree_todos.get_children(): self.tree_todos.delete(i)
        df = self.df_gastos()
        for _, r in df.iterrows():
            self.tree_todos.insert('', 'end', values=(r['descricao'][:15], f"R${r['valor']:.1f}", r['data'], r['cartao'], r['categoria']))
        self.plot_grafico(self.canvas_todos, df.groupby('categoria')['valor'].sum(), 'Por Categoria', 'pie')
    
    def atualizar_diario(self):
        for i in self.tree_diario.get_children(): self.tree_diario.delete(i)
        dfg = self.df_gastos().groupby('data')['valor'].sum().reset_index()
        for _, r in dfg.iterrows(): self.tree_diario.insert('', 'end', values=(r['data'], f"R${r['valor']:.1f}"))
        self.plot_grafico(self.canvas_diario, dfg.set_index('data'), 'Gastos Diários')
    
    def atualizar_cartoes(self):
        for i in self.tree_cartoes.get_children(): self.tree_cartoes.delete(i)
        dfg = self.df_gastos().groupby('cartao')['valor'].sum().reset_index()
        for _, r in dfg.iterrows(): self.tree_cartoes.insert('', 'end', values=(r['cartao'], f"R${r['valor']:.1f}"))
        self.plot_grafico(self.canvas_cartoes, dfg.set_index('cartao'), 'Por Cartão')
    
    def atualizar_parcelas(self):
        for i in self.tree_parcelas.get_children(): self.tree_parcelas.delete(i)
        df = self.df_gastos(True)
        if not df.empty:
            df['juros_est'] = df['juros_rate'] * df['valor']
            ttk.Label(self.frame_parcelas, text=f"Juros Pendentes: R${df['juros_est'].sum():.1f}", font=('bold', 11)).pack(pady=5)
            for _, r in df.iterrows():
                self.tree_parcelas.insert('', 'end', values=(r['descricao'][:20], f"R${r['valor']:.1f}", r['data'], r['status'], f"R${r['juros_est']:.1f}"))
        self.plot_grafico(self.canvas_parcelas, df.groupby('cartao')['valor'].sum(), 'Parcelas por Cartão')
    
    def atualizar_categorias(self):
        for i in self.tree_cats.get_children(): self.tree_cats.delete(i)
        dfg = self.df_gastos().groupby('categoria')['valor'].sum().reset_index()
        for _, r in dfg.iterrows(): self.tree_cats.insert('', 'end', values=(r['categoria'], f"R${r['valor']:.1f}"))
        self.plot_grafico(self.canvas_cats, dfg.set_index('categoria'), 'Por Categoria')
    
    def atualizar_todas_abas(self):
        self.atualizar_todos(); self.atualizar_diario(); self.atualizar_cartoes()
        self.atualizar_parcelas(); self.atualizar_categorias()
    
    def __del__(self):
        self.conn.close()

root = tk.Tk()
app = ControleGastos(root)
root.mainloop()