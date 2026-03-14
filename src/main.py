#pyinstaller --onefile --noconsole --add-data "assets:assets" --name "v1.0" src/main.py

import sqlite3
import customtkinter as ctk
from PIL import Image
from datetime import datetime
import re
import os

DB_PATH = "database.db"

def db_exec(query, params=(), fetchone=False, fetchall=False, commit=False):
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()
    cur.execute(query, params)
    result = None
    if fetchone:
        result = cur.fetchone()
    elif fetchall:
        result = cur.fetchall()
    if commit:
        con.commit()
    con.close()
    return result


def criar_banco():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            nome  TEXT NOT NULL,
            senha TEXT NOT NULL
        )""")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo    TEXT    NOT NULL,
            data_nascimento  TEXT    NOT NULL,
            cpf              TEXT    NOT NULL UNIQUE,
            rg               TEXT    NOT NULL,
            endereco         TEXT    NOT NULL,
            complemento      TEXT,
            medicacoes       TEXT,
            estado_civil     TEXT    NOT NULL,
            tem_filhos       INTEGER NOT NULL DEFAULT 0,
            qtd_filhos       INTEGER          DEFAULT 0,
            data_cadastro    TEXT    NOT NULL
        )""")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS relatorios (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id  INTEGER NOT NULL,
            titulo       TEXT    NOT NULL,
            conteudo     TEXT    NOT NULL,
            data_criacao TEXT    NOT NULL,
            criado_por   TEXT    NOT NULL,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        )""")

    cur.execute("SELECT id FROM usuarios WHERE nome = ?", ("Tereza C",))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO usuarios (nome, senha) VALUES (?, ?)", ("Tereza C", "admin"))

    con.commit()
    con.close()

def _only_digits(text, max_len):
    return re.sub(r'\D', '', text)[:max_len]

def mask_cpf(digits):
    d = _only_digits(digits, 11)
    n = len(d)
    if n <= 3:  return d
    if n <= 6:  return f"{d[:3]}.{d[3:]}"
    if n <= 9:  return f"{d[:3]}.{d[3:6]}.{d[6:]}"
    return          f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"

def mask_rg(digits):
    d = _only_digits(digits, 9)
    n = len(d)
    if n <= 2:  return d
    if n <= 5:  return f"{d[:2]}.{d[2:]}"
    if n <= 8:  return f"{d[:2]}.{d[2:5]}.{d[5:]}"
    return          f"{d[:2]}.{d[2:5]}.{d[5:8]}-{d[8:]}"

def mask_date(digits):
    d = _only_digits(digits, 8)
    n = len(d)
    if n <= 2:  return d
    if n <= 4:  return f"{d[:2]}/{d[2:]}"
    return          f"{d[:2]}/{d[2:4]}/{d[4:]}"

def bind_mask(entry, var, fn):
    _updating = [False]

    def on_change(*_):
        if _updating[0]:
            return
        texto = var.get()
        if entry.index("insert") != len(texto):
            return
        digits = re.sub(r"\D","",texto)
        masked = fn(digits)
        if masked != texto:
            _updating[0] = True
            var.set(masked)
            entry.icursor(len(masked))
            _updating[0] = False

    var.trace_add("write", on_change)

def validar_cpf(v):
    return bool(re.fullmatch(r'\d{3}\.\d{3}\.\d{3}-\d{2}', v))

def validar_rg(v):
    return bool(re.fullmatch(r'\d{2}\.\d{3}\.\d{3}-\d{1}', v))

def validar_data(v):
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            datetime.strptime(v, fmt)
            return True
        except ValueError:
            pass
    return False

FG   = "#f7f7f7"
FONT = lambda size=13, bold=False: ctk.CTkFont(
    family="Segoe UI", size=size, weight="bold" if bold else "normal")

def entry_kwargs():
    return dict(height=32, corner_radius=4, border_color="#bdbdbd",
                fg_color="#fdfdfd", font=FONT())

def lbl(parent, text, size=13, bold=False, **kw):
    return ctk.CTkLabel(parent, text=text, font=FONT(size, bold), **kw)

def section_title(parent, text):
    lbl(parent, text, 15, True).pack(anchor="w", padx=20, pady=(14, 4))

def aviso(parent, msg, title="Aviso"):
    w = ctk.CTkToplevel(parent)
    w.title(title)
    w.geometry("360x150")
    w.resizable(False, False)
    w.configure(fg_color=FG)
    w.grab_set()
    lbl(w, msg, justify="center").pack(pady=30, padx=20)
    ctk.CTkButton(w, text="OK", command=w.destroy,
                fg_color="#7f8c8d", hover_color="#566573",
                corner_radius=4, width=80, height=30).pack()


def visualizar_paciente(parent, pid):
    row = db_exec("""
        SELECT nome_completo, data_nascimento, cpf, rg, endereco, complemento,
        medicacoes, estado_civil, tem_filhos, qtd_filhos, data_cadastro
        FROM pacientes WHERE id=?
    """, (pid,), fetchone=True)

    if not row:
        return

    (nome, dn, cpf, rg, endereco, complemento,
    medicacoes, estado_civil, tem_filhos, qtd_filhos, data_cadastro) = row

    win = ctk.CTkToplevel(parent)
    win.title(f"Dados do Paciente — {nome}")
    win.geometry("520x560")
    win.resizable(False, False)
    win.configure(fg_color=FG)
    win.grab_set()
    win.focus_force()

    scroll = ctk.CTkScrollableFrame(win, fg_color=FG)
    scroll.pack(fill="both", expand=True, padx=0, pady=0)

    lbl(scroll, "DADOS DO PACIENTE", 16, True).pack(pady=(18, 10))
    ctk.CTkFrame(scroll, height=1, fg_color="#cccccc").pack(fill="x", padx=26, pady=(0, 10))

    PAD = dict(padx=26, pady=(8, 0))

    def campo(titulo, valor):
        frm = ctk.CTkFrame(scroll, fg_color="#efefef", corner_radius=6,
                            border_color="#dddddd", border_width=1)
        frm.pack(fill="x", padx=26, pady=(0, 6))
        lbl(frm, titulo, 11, bold=True, text_color="#555555").pack(anchor="w", padx=12, pady=(6, 0))
        lbl(frm, valor if valor else "—", 13).pack(anchor="w", padx=12, pady=(2, 6))

    campo("Nome Completo", nome)
    campo("Data de Nascimento", dn)
    campo("CPF", cpf)
    campo("RG", rg)
    campo("Endereço", endereco)

    if complemento:
        campo("Complemento", complemento)

    campo("Medicações", medicacoes if medicacoes else "Nenhuma")
    campo("Estado Civil", estado_civil)

    filhos_txt = f"Sim — {qtd_filhos} filho(s)" if tem_filhos else "Não"
    campo("Filhos", filhos_txt)
    campo("Data de Cadastro", data_cadastro)

    ctk.CTkButton(scroll, text="Fechar", command=win.destroy,
                fg_color="#7f8c8d", hover_color="#566573",
                corner_radius=4, height=32, width=100).pack(pady=(10, 20))


def abrir_cadastro_paciente(parent, callback):
    win = ctk.CTkToplevel(parent)
    win.title("Novo Paciente")
    win.geometry("560x680")
    win.resizable(False, False)
    win.configure(fg_color=FG)
    win.grab_set()
    win.focus_force()

    scroll = ctk.CTkScrollableFrame(win, fg_color=FG)
    scroll.pack(fill="both", expand=True, padx=0, pady=0)

    PAD = dict(padx=24, pady=(6, 0))

    lbl(scroll, "CADASTRO DE PACIENTE", 16, True).pack(pady=(18, 10))

    def field(label_text, required=True):
        lbl(scroll, label_text, anchor="w").pack(fill="x", **PAD)
        e = ctk.CTkEntry(scroll, **entry_kwargs())
        e.pack(fill="x", padx=24, pady=(2, 0))
        return e

    e_nome = field("Nome Completo *")

    lbl(scroll, "Data de Nascimento * (dd/mm/aa)", anchor="w").pack(fill="x", **PAD)
    var_dn = ctk.StringVar()
    e_dn   = ctk.CTkEntry(scroll, textvariable=var_dn, **entry_kwargs())
    e_dn.pack(fill="x", padx=24, pady=(2, 0))
    bind_mask(e_dn, var_dn, mask_date)

    lbl(scroll, "CPF * (xxx.xxx.xxx-xx)", anchor="w").pack(fill="x", **PAD)
    var_cpf = ctk.StringVar()
    e_cpf   = ctk.CTkEntry(scroll, textvariable=var_cpf, **entry_kwargs())
    e_cpf.pack(fill="x", padx=24, pady=(2, 0))
    bind_mask(e_cpf, var_cpf, mask_cpf)

    lbl(scroll, "RG * (xx.xxx.xxx-x)", anchor="w").pack(fill="x", **PAD)
    var_rg = ctk.StringVar()
    e_rg   = ctk.CTkEntry(scroll, textvariable=var_rg, **entry_kwargs())
    e_rg.pack(fill="x", padx=24, pady=(2, 0))
    bind_mask(e_rg, var_rg, mask_rg)

    e_end = field("Endereço *")

    var_comp = ctk.BooleanVar()

    frm_comp = ctk.CTkFrame(scroll, fg_color=FG)

    lbl(frm_comp, "Complemento").pack(anchor="w", padx=24)
    e_comp = ctk.CTkEntry(frm_comp, placeholder_text="Ex: Apto 42, Bloco B", **entry_kwargs())
    e_comp.pack(fill="x", padx=24, pady=(2,5))

    chk_comp = ctk.CTkCheckBox(
        scroll,
        text="Possui complemento no endereço",
        variable=var_comp,
        font=FONT()
    )
    chk_comp.pack(anchor="w", padx=24, pady=(8,0))

    def toggle_comp(*_):
        if var_comp.get():
            frm_comp.pack(fill="x", pady=(4,0), before=chk_comp)
        else:
            frm_comp.pack_forget()
            e_comp.delete(0,"end")

    var_comp.trace_add("write", toggle_comp)

    e_med = field("Medicações (separe por vírgula, deixe em branco se não houver)", required=False)

    lbl(scroll, "Estado Civil *", anchor="w").pack(fill="x", **PAD)
    var_ec = ctk.StringVar(value="Solteiro(a)")
    cmb_ec = ctk.CTkComboBox(scroll,
        values=["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"],
        variable=var_ec, height=32, corner_radius=4,
        border_color="#bdbdbd", fg_color="#fdfdfd",
        button_color="#bdbdbd", font=FONT())
    cmb_ec.pack(fill="x", padx=24, pady=(2, 0))

    var_filhos = ctk.BooleanVar()

    frm_qtd = ctk.CTkFrame(scroll, fg_color=FG)

    lbl(frm_qtd, "Quantos filhos? *", anchor="w").pack(anchor="w", padx=24)
    e_qtd = ctk.CTkEntry(frm_qtd, width=100, **entry_kwargs())
    e_qtd.pack(anchor="w", padx=24, pady=(2,5))

    chk_filhos = ctk.CTkCheckBox(
        scroll,
        text="Tem filhos",
        variable=var_filhos,
        font=FONT()
    )
    chk_filhos.pack(anchor="w", padx=24, pady=(8,0))

    def toggle_filhos(*_):
        if var_filhos.get():
            frm_qtd.pack(fill="x", pady=(4,0), before=chk_filhos)
        else:
            frm_qtd.pack_forget()
            e_qtd.delete(0,"end")

    var_filhos.trace_add("write", toggle_filhos)

    lbl_err = ctk.CTkLabel(scroll, text="", text_color="red", font=FONT(12, True),
                            justify="center", wraplength=480)
    lbl_err.pack(pady=(8, 0))

    def salvar():
        lbl_err.configure(text="")
        erros = []
        nome  = e_nome.get().strip()
        dn    = var_dn.get().strip()
        cpf_  = var_cpf.get().strip()
        rg_   = var_rg.get().strip()
        end_  = e_end.get().strip()
        comp_ = e_comp.get().strip() if var_comp.get() else ""
        med_  = e_med.get().strip()
        ec_   = var_ec.get().strip()
        filhos_bool = var_filhos.get()
        qtd_raw     = e_qtd.get().strip()

        if not nome:                          erros.append("• Nome completo é obrigatório.")
        if not dn or not validar_data(dn):    erros.append("• Data de nascimento inválida (use dd/mm/aa).")
        if not cpf_ or not validar_cpf(cpf_): erros.append("• CPF inválido (use xxx.xxx.xxx-xx).")
        if not rg_ or not validar_rg(rg_):    erros.append("• RG inválido (use xx.xxx.xxx-x).")
        if not end_:                          erros.append("• Endereço é obrigatório.")
        if filhos_bool:
            if not qtd_raw.isdigit() or int(qtd_raw) < 1:
                erros.append("• Informe a quantidade de filhos (número > 0).")

        if erros:
            lbl_err.configure(text="\n".join(erros))
            return

        qtd = int(qtd_raw) if filhos_bool else 0
        try:
            db_exec("""
                INSERT INTO pacientes
                (nome_completo,data_nascimento,cpf,rg,endereco,complemento,
                medicacoes,estado_civil,tem_filhos,qtd_filhos,data_cadastro)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (nome, dn, cpf_, rg_, end_, comp_, med_, ec_,
                1 if filhos_bool else 0, qtd,
                datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
                commit=True)
            callback()
            win.destroy()
        except sqlite3.IntegrityError:
            lbl_err.configure(text="• CPF já cadastrado no sistema.")

    frm_btns = ctk.CTkFrame(scroll, fg_color=FG)
    frm_btns.pack(padx=24, pady=(12, 24), anchor="w")
    ctk.CTkButton(frm_btns, text="💾  Salvar", command=salvar,
                fg_color="#2d6a4f", hover_color="#1b4332",
                corner_radius=4, height=36, width=130).pack(side="left", padx=(0, 10))
    ctk.CTkButton(frm_btns, text="✕  Cancelar", command=win.destroy,
                fg_color="#c0392b", hover_color="#922b21",
                corner_radius=4, height=36, width=130).pack(side="left")


def confirmar_exclusao(parent, pid, nome, callback):
    w = ctk.CTkToplevel(parent)
    w.title("Confirmar Exclusão")
    w.geometry("420x210")
    w.resizable(False, False)
    w.configure(fg_color=FG)
    w.grab_set()
    w.focus_force()

    lbl(w, "⚠  Atenção", 16, True, text_color="#c0392b").pack(pady=(22, 6))
    lbl(w, f'Tem certeza que deseja remover:\n\n"{nome}"\n\nEsta ação não pode ser desfeita.',
        justify="center").pack(pady=(0, 18))

    frm = ctk.CTkFrame(w, fg_color=FG)
    frm.pack()

    def excluir():
        db_exec("DELETE FROM pacientes WHERE id=?", (pid,), commit=True)
        callback()
        w.destroy()

    ctk.CTkButton(frm, text="🗑  Sim, remover", command=excluir,
                fg_color="#c0392b", hover_color="#922b21",
                corner_radius=4, height=34, width=140).pack(side="left", padx=(0, 10))
    ctk.CTkButton(frm, text="✕  Cancelar", command=w.destroy,
                fg_color="#7f8c8d", hover_color="#566573",
                corner_radius=4, height=34, width=120).pack(side="left")


def abrir_editar_paciente(parent, pid, callback):
    row = db_exec("""
        SELECT nome_completo, data_nascimento, cpf, rg, endereco, complemento,
        medicacoes, estado_civil, tem_filhos, qtd_filhos
        FROM pacientes WHERE id=?
    """, (pid,), fetchone=True)

    if not row:
        return

    (nome_db, dn_db, cpf_db, rg_db, end_db, comp_db,
    med_db, ec_db, tf_db, qf_db) = row

    win = ctk.CTkToplevel(parent)
    win.title("Editar Paciente")
    win.geometry("560x680")
    win.resizable(False, False)
    win.configure(fg_color=FG)
    win.grab_set()
    win.focus_force()

    scroll = ctk.CTkScrollableFrame(win, fg_color=FG)
    scroll.pack(fill="both", expand=True, padx=0, pady=0)

    PAD = dict(padx=24, pady=(6, 0))

    lbl(scroll, "EDITAR PACIENTE", 16, True).pack(pady=(18, 10))

    def field(label_text, valor_inicial=""):
        lbl(scroll, label_text, anchor="w").pack(fill="x", **PAD)
        e = ctk.CTkEntry(scroll, **entry_kwargs())
        e.pack(fill="x", padx=24, pady=(2, 0))
        if valor_inicial:
            e.insert(0, valor_inicial)
        return e

    e_nome = field("Nome Completo *", nome_db)

    lbl(scroll, "Data de Nascimento * (dd/mm/aa)", anchor="w").pack(fill="x", **PAD)
    var_dn = ctk.StringVar(value=dn_db)
    e_dn   = ctk.CTkEntry(scroll, textvariable=var_dn, **entry_kwargs())
    e_dn.pack(fill="x", padx=24, pady=(2, 0))
    bind_mask(e_dn, var_dn, mask_date)

    lbl(scroll, "CPF * (xxx.xxx.xxx-xx)", anchor="w").pack(fill="x", **PAD)
    var_cpf = ctk.StringVar(value=cpf_db)
    e_cpf   = ctk.CTkEntry(scroll, textvariable=var_cpf, **entry_kwargs())
    e_cpf.pack(fill="x", padx=24, pady=(2, 0))
    bind_mask(e_cpf, var_cpf, mask_cpf)

    lbl(scroll, "RG * (xx.xxx.xxx-x)", anchor="w").pack(fill="x", **PAD)
    var_rg = ctk.StringVar(value=rg_db)
    e_rg   = ctk.CTkEntry(scroll, textvariable=var_rg, **entry_kwargs())
    e_rg.pack(fill="x", padx=24, pady=(2, 0))
    bind_mask(e_rg, var_rg, mask_rg)

    e_end = field("Endereço *", end_db)

    var_comp = ctk.BooleanVar(value=bool(comp_db))

    frm_comp = ctk.CTkFrame(scroll, fg_color=FG)
    lbl(frm_comp, "Complemento").pack(anchor="w", padx=24)
    e_comp = ctk.CTkEntry(frm_comp, placeholder_text="Ex: Apto 42, Bloco B", **entry_kwargs())
    e_comp.pack(fill="x", padx=24, pady=(2, 5))
    if comp_db:
        e_comp.insert(0, comp_db)

    chk_comp = ctk.CTkCheckBox(scroll, text="Possui complemento no endereço",
                                variable=var_comp, font=FONT())
    chk_comp.pack(anchor="w", padx=24, pady=(8, 0))

    def toggle_comp(*_):
        if var_comp.get():
            frm_comp.pack(fill="x", pady=(4, 0), before=chk_comp)
        else:
            frm_comp.pack_forget()
            e_comp.delete(0, "end")

    var_comp.trace_add("write", toggle_comp)
    if comp_db:
        frm_comp.pack(fill="x", pady=(4, 0), before=chk_comp)

    e_med = field("Medicações (separe por vírgula, deixe em branco se não houver)", med_db or "")

    lbl(scroll, "Estado Civil *", anchor="w").pack(fill="x", **PAD)
    var_ec = ctk.StringVar(value=ec_db)
    cmb_ec = ctk.CTkComboBox(scroll,
        values=["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"],
        variable=var_ec, height=32, corner_radius=4,
        border_color="#bdbdbd", fg_color="#fdfdfd",
        button_color="#bdbdbd", font=FONT())
    cmb_ec.pack(fill="x", padx=24, pady=(2, 0))

    var_filhos = ctk.BooleanVar(value=bool(tf_db))

    frm_qtd = ctk.CTkFrame(scroll, fg_color=FG)
    lbl(frm_qtd, "Quantos filhos? *", anchor="w").pack(anchor="w", padx=24)
    e_qtd = ctk.CTkEntry(frm_qtd, width=100, **entry_kwargs())
    e_qtd.pack(anchor="w", padx=24, pady=(2, 5))
    if tf_db and qf_db:
        e_qtd.insert(0, str(qf_db))

    chk_filhos = ctk.CTkCheckBox(scroll, text="Tem filhos",
                                variable=var_filhos, font=FONT())
    chk_filhos.pack(anchor="w", padx=24, pady=(8, 0))

    def toggle_filhos(*_):
        if var_filhos.get():
            frm_qtd.pack(fill="x", pady=(4, 0), before=chk_filhos)
        else:
            frm_qtd.pack_forget()
            e_qtd.delete(0, "end")

    var_filhos.trace_add("write", toggle_filhos)
    if tf_db:
        frm_qtd.pack(fill="x", pady=(4, 0), before=chk_filhos)

    lbl_err = ctk.CTkLabel(scroll, text="", text_color="red", font=FONT(12, True),
                            justify="center", wraplength=480)
    lbl_err.pack(pady=(8, 0))

    def salvar():
        lbl_err.configure(text="")
        erros = []
        nome  = e_nome.get().strip()
        dn    = var_dn.get().strip()
        cpf_  = var_cpf.get().strip()
        rg_   = var_rg.get().strip()
        end_  = e_end.get().strip()
        comp_ = e_comp.get().strip() if var_comp.get() else ""
        med_  = e_med.get().strip()
        ec_   = var_ec.get().strip()
        filhos_bool = var_filhos.get()
        qtd_raw     = e_qtd.get().strip()

        if not nome:                           erros.append("• Nome completo é obrigatório.")
        if not dn or not validar_data(dn):     erros.append("• Data de nascimento inválida (use dd/mm/aa).")
        if not cpf_ or not validar_cpf(cpf_):  erros.append("• CPF inválido (use xxx.xxx.xxx-xx).")
        if not rg_ or not validar_rg(rg_):     erros.append("• RG inválido (use xx.xxx.xxx-x).")
        if not end_:                           erros.append("• Endereço é obrigatório.")
        if filhos_bool:
            if not qtd_raw.isdigit() or int(qtd_raw) < 1:
                erros.append("• Informe a quantidade de filhos (número > 0).")

        if erros:
            lbl_err.configure(text="\n".join(erros))
            return

        qtd = int(qtd_raw) if filhos_bool else 0
        try:
            db_exec("""
                UPDATE pacientes SET
                    nome_completo=?, data_nascimento=?, cpf=?, rg=?, endereco=?,
                    complemento=?, medicacoes=?, estado_civil=?, tem_filhos=?, qtd_filhos=?
                WHERE id=?
            """, (nome, dn, cpf_, rg_, end_, comp_, med_, ec_,
                1 if filhos_bool else 0, qtd, pid),
                commit=True)
            callback()
            win.destroy()
        except sqlite3.IntegrityError:
            lbl_err.configure(text="• CPF já cadastrado para outro paciente.")

    frm_btns = ctk.CTkFrame(scroll, fg_color=FG)
    frm_btns.pack(padx=24, pady=(12, 24), anchor="w")
    ctk.CTkButton(frm_btns, text="💾  Salvar Alterações", command=salvar,
                fg_color="#1a5276", hover_color="#154360",
                corner_radius=4, height=36, width=160).pack(side="left", padx=(0, 10))
    ctk.CTkButton(frm_btns, text="✕  Cancelar", command=win.destroy,
                fg_color="#c0392b", hover_color="#922b21",
                corner_radius=4, height=36, width=130).pack(side="left")


def montar_aba_cadastros(parent, main_win):
    frm_top = ctk.CTkFrame(parent, fg_color=FG)
    frm_top.pack(fill="x", padx=20, pady=(14, 4))

    lbl(frm_top, "Pacientes Cadastrados", 15, True).pack(side="left")

    btn_rem = ctk.CTkButton(frm_top, text="－  Remover",
                            fg_color="#c0392b", hover_color="#922b21",
                            corner_radius=4, height=30, width=130, font=FONT())
    btn_rem.pack(side="right", padx=(6, 0))

    btn_edit = ctk.CTkButton(frm_top, text="✏  Editar",
                            fg_color="#7d6608", hover_color="#5d4e08",
                            corner_radius=4, height=30, width=130, font=FONT())
    btn_edit.pack(side="right", padx=(6, 0))

    btn_add = ctk.CTkButton(frm_top, text="＋  Adicionar",
                            fg_color="#2d6a4f", hover_color="#1b4332",
                            corner_radius=4, height=30, width=130, font=FONT())
    btn_add.pack(side="right")

    frm_busca = ctk.CTkFrame(parent, fg_color=FG)
    frm_busca.pack(fill="x", padx=20, pady=(0, 6))
    lbl(frm_busca, "🔍  Buscar:").pack(side="left")
    var_busca = ctk.StringVar()
    ctk.CTkEntry(frm_busca, textvariable=var_busca, height=28, width=300,
                corner_radius=4, border_color="#bdbdbd",
                fg_color="#fdfdfd", font=FONT()).pack(side="left", padx=(8, 0))

    lbl_hint = lbl(frm_busca, "  💡 Clique duplo para ver detalhes do paciente",
                11, text_color="#888888")
    lbl_hint.pack(side="left", padx=(16, 0))

    COLS   = ["ID", "Nome Completo", "Dt. Nasc.", "CPF", "Estado Civil", "Filhos", "Cadastrado em"]
    WIDTHS = [45, 215, 85, 135, 110, 55, 150]
    FONT_H = FONT(12, True)
    FONT_R = FONT(12)

    frm_head = ctk.CTkFrame(parent, fg_color="#d9d9d9", corner_radius=0, height=28)
    frm_head.pack(fill="x", padx=20)
    frm_head.pack_propagate(False)
    for c, w in zip(COLS, WIDTHS):
        ctk.CTkLabel(frm_head, text=c, font=FONT_H, width=w,
                    anchor="w", padx=5, fg_color="#d9d9d9").pack(side="left")

    frm_body = ctk.CTkScrollableFrame(parent, fg_color="#fafafa",
                                    border_color="#cccccc", border_width=1)
    frm_body.pack(fill="both", expand=True, padx=20, pady=(0, 14))

    selected = {"id": None, "nome": None, "frame": None}

    def deselect():
        if selected["frame"]:
            try:
                bg = selected["frame"]._bg
                selected["frame"].configure(fg_color=bg)
                for c in selected["frame"].winfo_children():
                    c.configure(fg_color=bg)
            except Exception:
                pass
        selected.update(id=None, nome=None, frame=None)

    def carregar(filtro=""):
        deselect()
        for w in frm_body.winfo_children():
            w.destroy()

        rows = db_exec("""
            SELECT id,nome_completo,data_nascimento,cpf,
            estado_civil,tem_filhos,qtd_filhos,data_cadastro
            FROM pacientes
            WHERE nome_completo LIKE ? OR cpf LIKE ?
            ORDER BY nome_completo
        """, (f"%{filtro}%", f"%{filtro}%"), fetchall=True)

        if not rows:
            lbl(frm_body, "Nenhum paciente encontrado.", text_color="#888").pack(pady=20)
            return

        for i, row in enumerate(rows):
            pid, nome, dn, cpf, ec, tf, qf, dc = row
            filhos = str(qf) if tf else "Não"
            dados  = [str(pid), nome, dn, cpf, ec, filhos, dc]
            bg     = "#ffffff" if i % 2 == 0 else "#f0f0f0"

            frm_row = ctk.CTkFrame(frm_body, fg_color=bg, corner_radius=0, cursor="hand2")
            frm_row.pack(fill="x")
            frm_row._bg = bg

            for d, w in zip(dados, WIDTHS):
                ctk.CTkLabel(frm_row, text=d, font=FONT_R,
                            width=w, anchor="w", padx=5, fg_color=bg).pack(side="left")

            def mk_sel(fr, pid_=pid, nome_=nome):
                def sel(e=None):
                    deselect()
                    fr.configure(fg_color="#cce5ff")
                    for c in fr.winfo_children():
                        try: c.configure(fg_color="#cce5ff")
                        except: pass
                    selected.update(id=pid_, nome=nome_, frame=fr)
                return sel

            def mk_dbl(pid_=pid):
                def dbl(e=None):
                    visualizar_paciente(main_win, pid_)
                return dbl

            cb  = mk_sel(frm_row)
            dbl = mk_dbl()

            frm_row.bind("<Button-1>",        cb)
            frm_row.bind("<Double-Button-1>",  dbl)
            for child in frm_row.winfo_children():
                child.bind("<Button-1>",       cb)
                child.bind("<Double-Button-1>", dbl)

    var_busca.trace_add("write", lambda *_: carregar(var_busca.get()))

    btn_add.configure(command=lambda: abrir_cadastro_paciente(
        main_win, lambda: carregar(var_busca.get())))

    def rm():
        if selected["id"] is None:
            aviso(main_win, "Selecione um paciente na lista antes de remover.")
            return
        confirmar_exclusao(main_win, selected["id"], selected["nome"],
                        lambda: carregar(var_busca.get()))

    btn_rem.configure(command=rm)

    def edit():
        if selected["id"] is None:
            aviso(main_win, "Selecione um paciente na lista antes de editar.")
            return
        abrir_editar_paciente(main_win, selected["id"], lambda: carregar(var_busca.get()))

    btn_edit.configure(command=edit)
    carregar()


def abrir_criar_relatorio(parent, usuario, callback):
    pacs = db_exec(
        "SELECT id,nome_completo FROM pacientes ORDER BY nome_completo",
        fetchall=True)

    if not pacs:
        aviso(parent, "Nenhum paciente cadastrado.\nCadastre um paciente primeiro.")
        return

    win = ctk.CTkToplevel(parent)
    win.title("Novo Relatório")
    win.geometry("560x500")
    win.resizable(False, False)
    win.configure(fg_color=FG)
    win.grab_set()
    win.focus_force()

    lbl(win, "NOVO RELATÓRIO", 16, True).pack(pady=(20, 10))

    nomes   = [p[1] for p in pacs]
    id_map  = {p[1]: p[0] for p in pacs}
    var_pac = ctk.StringVar(value=nomes[0])

    PAD = dict(padx=26, pady=(6, 0))
    lbl(win, "Paciente *", anchor="w").pack(fill="x", **PAD)
    ctk.CTkComboBox(win, values=nomes, variable=var_pac, height=32,
                    corner_radius=4, border_color="#bdbdbd",
                    fg_color="#fdfdfd", button_color="#bdbdbd",
                    font=FONT()).pack(fill="x", padx=26, pady=(2, 0))

    lbl(win, "Título *", anchor="w").pack(fill="x", **PAD)
    e_titulo = ctk.CTkEntry(win, **entry_kwargs())
    e_titulo.pack(fill="x", padx=26, pady=(2, 0))

    lbl(win, "Conteúdo *", anchor="w").pack(fill="x", **PAD)
    txt = ctk.CTkTextbox(win, height=180, corner_radius=4,
                        border_color="#bdbdbd", border_width=1,
                        fg_color="#fdfdfd", font=FONT())
    txt.pack(fill="x", padx=26, pady=(2, 0))

    lbl_err = ctk.CTkLabel(win, text="", text_color="red", font=FONT(12, True))
    lbl_err.pack(pady=(6, 0))

    def salvar():
        lbl_err.configure(text="")
        pac_nome = var_pac.get().strip()
        titulo   = e_titulo.get().strip()
        conteudo = txt.get("1.0", "end").strip()
        erros = []
        if not pac_nome:  erros.append("Selecione um paciente.")
        if not titulo:    erros.append("Título é obrigatório.")
        if not conteudo:  erros.append("Conteúdo é obrigatório.")
        if erros:
            lbl_err.configure(text="\n".join(erros))
            return
        pid = id_map.get(pac_nome)
        db_exec("""
            INSERT INTO relatorios (paciente_id,titulo,conteudo,data_criacao,criado_por)
            VALUES (?,?,?,?,?)
        """, (pid, titulo, conteudo,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"), usuario),
            commit=True)
        callback()
        win.destroy()

    frm_b = ctk.CTkFrame(win, fg_color=FG)
    frm_b.pack(pady=(10, 20))
    ctk.CTkButton(frm_b, text="💾  Salvar Relatório", command=salvar,
                fg_color="#1a5276", hover_color="#154360",
                corner_radius=4, height=36, width=160).pack(side="left", padx=(0, 10))
    ctk.CTkButton(frm_b, text="✕  Cancelar", command=win.destroy,
                fg_color="#c0392b", hover_color="#922b21",
                corner_radius=4, height=36, width=120).pack(side="left")


def montar_aba_relatorios(parent, main_win, usuario):
    frm_top = ctk.CTkFrame(parent, fg_color=FG)
    frm_top.pack(fill="x", padx=20, pady=(14, 4))
    lbl(frm_top, "Relatórios", 15, True).pack(side="left")
    btn_add = ctk.CTkButton(frm_top, text="＋  Novo Relatório",
                            fg_color="#1a5276", hover_color="#154360",
                            corner_radius=4, height=30, width=150, font=FONT())
    btn_add.pack(side="right")

    frm_busca = ctk.CTkFrame(parent, fg_color=FG)
    frm_busca.pack(fill="x", padx=20, pady=(0, 6))
    lbl(frm_busca, "🔍  Buscar:").pack(side="left")
    var_busca = ctk.StringVar()
    ctk.CTkEntry(frm_busca, textvariable=var_busca, height=28, width=300,
                corner_radius=4, border_color="#bdbdbd",
                fg_color="#fdfdfd", font=FONT()).pack(side="left", padx=(8, 0))

    COLS   = ["ID", "Título", "Paciente", "Criado por", "Data"]
    WIDTHS = [40, 220, 200, 130, 140]
    FONT_H = FONT(12, True)
    FONT_R = FONT(12)

    frm_head = ctk.CTkFrame(parent, fg_color="#d9d9d9", corner_radius=0, height=28)
    frm_head.pack(fill="x", padx=20)
    frm_head.pack_propagate(False)
    for c, w in zip(COLS, WIDTHS):
        ctk.CTkLabel(frm_head, text=c, font=FONT_H, width=w,
                    anchor="w", padx=5, fg_color="#d9d9d9").pack(side="left")

    frm_body = ctk.CTkScrollableFrame(parent, fg_color="#fafafa",
                                    border_color="#cccccc", border_width=1)
    frm_body.pack(fill="both", expand=True, padx=20, pady=(0, 14))

    def carregar(filtro=""):
        for w in frm_body.winfo_children():
            w.destroy()
        rows = db_exec("""
            SELECT r.id,r.titulo,p.nome_completo,r.criado_por,r.data_criacao
            FROM relatorios r JOIN pacientes p ON r.paciente_id=p.id
            WHERE r.titulo LIKE ? OR p.nome_completo LIKE ?
            ORDER BY r.data_criacao DESC
        """, (f"%{filtro}%", f"%{filtro}%"), fetchall=True)

        if not rows:
            lbl(frm_body, "Nenhum relatório encontrado.", text_color="#888").pack(pady=20)
            return

        for i, row in enumerate(rows):
            rid, titulo, pac, criador, data = row
            bg = "#ffffff" if i % 2 == 0 else "#f0f0f0"
            frm_row = ctk.CTkFrame(frm_body, fg_color=bg, corner_radius=0)
            frm_row.pack(fill="x")
            for d, w in zip([str(rid), titulo, pac, criador, data], WIDTHS):
                ctk.CTkLabel(frm_row, text=d, font=FONT_R,
                            width=w, anchor="w", padx=5, fg_color=bg).pack(side="left")
            ctk.CTkButton(frm_row, text="👁 Ver", width=70, height=24,
                        fg_color="#1a5276", hover_color="#154360",
                        corner_radius=3, font=FONT(11),
                        command=lambda rid_=rid: visualizar_relatorio(main_win, rid_)
                        ).pack(side="left", padx=4, pady=2)

    var_busca.trace_add("write", lambda *_: carregar(var_busca.get()))
    btn_add.configure(command=lambda: abrir_criar_relatorio(
        main_win, usuario, lambda: carregar(var_busca.get())))
    carregar()


def montar_aba_configuracoes(parent, main_win, usuario):
    scroll = ctk.CTkScrollableFrame(parent, fg_color=FG)
    scroll.pack(fill="both", expand=True, padx=0, pady=0)

    lbl(scroll, "Configurações", 16, True).pack(anchor="w", padx=26, pady=(18, 2))
    ctk.CTkFrame(scroll, height=1, fg_color="#cccccc").pack(fill="x", padx=26, pady=(0, 16))

    frm1 = ctk.CTkFrame(scroll, fg_color="#efefef", corner_radius=8, border_color="#cccccc", border_width=1)
    frm1.pack(fill="x", padx=26, pady=(0, 20))
    lbl(frm1, "🔑  Alterar senha de login", 14, True).pack(anchor="w", padx=18, pady=(14, 4))
    lbl(frm1, f"Usuário: {usuario}", text_color="#555").pack(anchor="w", padx=18)

    PAD = dict(padx=18, pady=(6, 0))
    lbl(frm1, "Senha atual *", anchor="w").pack(fill="x", **PAD)
    e_atual1 = ctk.CTkEntry(frm1, show="*", **entry_kwargs())
    e_atual1.pack(fill="x", padx=18, pady=(2, 0))

    lbl(frm1, "Nova senha *", anchor="w").pack(fill="x", **PAD)
    e_nova1 = ctk.CTkEntry(frm1, show="*", **entry_kwargs())
    e_nova1.pack(fill="x", padx=18, pady=(2, 0))

    lbl(frm1, "Confirmar nova senha *", anchor="w").pack(fill="x", **PAD)
    e_conf1 = ctk.CTkEntry(frm1, show="*", **entry_kwargs())
    e_conf1.pack(fill="x", padx=18, pady=(2, 0))

    lbl_msg1 = ctk.CTkLabel(frm1, text="", font=FONT(12, True))
    lbl_msg1.pack(pady=(6, 0))

    def alterar_login():
        lbl_msg1.configure(text="", text_color="red")
        atual = e_atual1.get()
        nova  = e_nova1.get()
        conf  = e_conf1.get()

        row = db_exec("SELECT id FROM usuarios WHERE nome=? AND senha=?",
                    (usuario, atual), fetchone=True)
        if row is None:
            lbl_msg1.configure(text="Senha atual incorreta.")
            return
        if not nova:
            lbl_msg1.configure(text="A nova senha não pode ser vazia.")
            return
        if nova != conf:
            lbl_msg1.configure(text="As senhas não coincidem.")
            return
        db_exec("UPDATE usuarios SET senha=? WHERE nome=?",
                (nova, usuario), commit=True)
        e_atual1.delete(0, "end")
        e_nova1.delete(0, "end")
        e_conf1.delete(0, "end")
        lbl_msg1.configure(text="✅  Senha de login alterada com sucesso!", text_color="#2d6a4f")

    ctk.CTkButton(frm1, text="Salvar nova senha de login", command=alterar_login,
                fg_color="#2d6a4f", hover_color="#1b4332",
                corner_radius=4, height=34, width=220).pack(anchor="w", padx=18, pady=(10, 16))

    CONFIG_FILE = "relatorio_senha.txt"

    def ler_senha_rel():
        try:
            with open(CONFIG_FILE, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "admin2"

    def salvar_senha_rel(s):
        os.makedirs("tia", exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            f.write(s)

    frm2 = ctk.CTkFrame(scroll, fg_color="#efefef", corner_radius=8,
                        border_color="#cccccc", border_width=1)
    frm2.pack(fill="x", padx=26, pady=(0, 20))
    lbl(frm2, "📄  Alterar senha de visualização de relatórios", 14, True).pack(
        anchor="w", padx=18, pady=(14, 4))

    lbl(frm2, "Senha atual dos relatórios *", anchor="w").pack(fill="x", **PAD)
    e_atual2 = ctk.CTkEntry(frm2, show="*", **entry_kwargs())
    e_atual2.pack(fill="x", padx=18, pady=(2, 0))

    lbl(frm2, "Nova senha *", anchor="w").pack(fill="x", **PAD)
    e_nova2 = ctk.CTkEntry(frm2, show="*", **entry_kwargs())
    e_nova2.pack(fill="x", padx=18, pady=(2, 0))

    lbl(frm2, "Confirmar nova senha *", anchor="w").pack(fill="x", **PAD)
    e_conf2 = ctk.CTkEntry(frm2, show="*", **entry_kwargs())
    e_conf2.pack(fill="x", padx=18, pady=(2, 0))

    lbl_msg2 = ctk.CTkLabel(frm2, text="", font=FONT(12, True))
    lbl_msg2.pack(pady=(6, 0))

    def alterar_relatorio():
        lbl_msg2.configure(text="", text_color="red")
        atual = e_atual2.get()
        nova  = e_nova2.get()
        conf  = e_conf2.get()

        if atual != ler_senha_rel():
            lbl_msg2.configure(text="Senha atual incorreta.")
            return
        if not nova:
            lbl_msg2.configure(text="A nova senha não pode ser vazia.")
            return
        if nova != conf:
            lbl_msg2.configure(text="As senhas não coincidem.")
            return
        salvar_senha_rel(nova)
        e_atual2.delete(0, "end")
        e_nova2.delete(0, "end")
        e_conf2.delete(0, "end")
        lbl_msg2.configure(text="✅  Senha de relatórios alterada com sucesso!", text_color="#2d6a4f")

    ctk.CTkButton(frm2, text="Salvar nova senha de relatórios", command=alterar_relatorio,
                fg_color="#1a5276", hover_color="#154360",
                corner_radius=4, height=34, width=240).pack(anchor="w", padx=18, pady=(10, 16))


def visualizar_relatorio(parent, rid):
    CONFIG_FILE = "relatorio_senha.txt"

    def ler_senha():
        try:
            with open(CONFIG_FILE, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "admin2"

    def _show():
        row = db_exec("""
            SELECT r.titulo,r.conteudo,r.data_criacao,r.criado_por,p.nome_completo
            FROM relatorios r JOIN pacientes p ON r.paciente_id=p.id
            WHERE r.id=?
        """, (rid,), fetchone=True)
        if not row:
            return
        titulo, conteudo, data_cri, criador, pac = row

        win = ctk.CTkToplevel(parent)
        win.title(f"Relatório — {titulo}")
        win.geometry("680x520")
        win.resizable(False, False)
        win.configure(fg_color=FG)
        win.grab_set()
        win.focus_force()

        lbl(win, f"📄  {titulo}", 16, True).pack(pady=(20, 4))
        lbl(win, f"Paciente: {pac}   |   Por: {criador}   |   {data_cri}",
            12, text_color="#555").pack()
        ctk.CTkFrame(win, height=1, fg_color="#ccc").pack(fill="x", padx=30, pady=8)
        txt = ctk.CTkTextbox(win, fg_color="#fdfdfd", border_color="#bdbdbd",
                            border_width=1, corner_radius=4, font=FONT(), state="normal")
        txt.pack(fill="both", expand=True, padx=30, pady=(0, 6))
        txt.insert("1.0", conteudo)
        txt.configure(state="disabled")
        lbl(win, "🔒 Somente leitura", 11, text_color="#888").pack()
        ctk.CTkButton(win, text="Fechar", command=win.destroy,
                    fg_color="#7f8c8d", hover_color="#566573",
                    corner_radius=4, height=30, width=90).pack(pady=(4, 16))

    ws = ctk.CTkToplevel(parent)
    ws.title("Acesso Restrito")
    ws.geometry("340x190")
    ws.resizable(False, False)
    ws.configure(fg_color=FG)
    ws.grab_set()
    ws.focus_force()

    lbl(ws, "🔒  Relatório Protegido", 15, True).pack(pady=(22, 4))
    lbl(ws, "Digite a senha para visualizar:").pack(pady=(0, 6))
    var_s = ctk.StringVar()
    e_s   = ctk.CTkEntry(ws, textvariable=var_s, show="*", height=32, width=200,
                        corner_radius=4, border_color="#bdbdbd", fg_color="#fdfdfd")
    e_s.pack()
    lbl_e = ctk.CTkLabel(ws, text="", text_color="red", font=FONT(12, True))
    lbl_e.pack(pady=(4, 0))

    def verificar(ev=None):
        if var_s.get() == ler_senha():
            ws.destroy()
            _show()
        else:
            lbl_e.configure(text="Senha incorreta.")
            var_s.set("")

    e_s.bind("<Return>", verificar)
    ctk.CTkButton(ws, text="Acessar", command=verificar,
                fg_color="#1a5276", hover_color="#154360",
                corner_radius=4, height=32, width=100).pack(pady=(8, 0))


def login1():
    usuario = cmb1.get()
    senha   = etr1_var1.get()
    row     = db_exec("SELECT id FROM usuarios WHERE nome=? AND senha=?",
                    (usuario, senha), fetchone=True)

    for w in loginwin.winfo_children():
        if isinstance(w, ctk.CTkLabel) and getattr(w, "_is_err", False):
            w.destroy()

    if not row:
        err = ctk.CTkLabel(loginwin, text="SENHA INVÁLIDA", text_color="red",
                            font=FONT(13, True))
        err._is_err = True
        err.place(x=186, y=135)
        return

    loginwin.destroy()

    win = ctk.CTk()
    win.title(f"v1.0 ~ {usuario}")
    win.geometry("1200x720")
    win.resizable(False, False)
    win.configure(fg_color=FG)

    tab = ctk.CTkTabview(win, width=1200, height=720,
                        corner_radius=5, border_color="black", fg_color=FG)
    tab.pack()
    for t in ("VISÃO GERAL", "CADASTROS", "RELATÓRIOS", "CONFIGURAÇÕES"):
        tab.add(t)
    tab.set("VISÃO GERAL")

    W, H = 1160, 650

    frm_vg = ctk.CTkFrame(tab.tab("VISÃO GERAL"), width=W, height=H,
                        fg_color=FG, border_width=1, border_color="black")
    frm_vg.place(x=10, y=10)
    frm_vg.pack_propagate(False)

    lbl_sau  = lbl(frm_vg, "", 22, True)
    lbl_sau.place(x=30, y=30)
    lbl_hora = lbl(frm_vg, "", 18)
    lbl_hora.place(x=30, y=65)

    _img_psi = [None]
    def tick():
        agora = datetime.now()
        h     = agora.hour
        greet = "Bom dia" if h < 12 else ("Boa tarde" if h < 18 else "Boa noite")
        lbl_sau.configure(text=f"{greet}, {usuario}!")
        lbl_hora.configure(text=agora.strftime("Data: %d/%m/%Y  Hora: %H:%M:%S"))
        if _img_psi[0] is None:
            try:
                _img_psi[0] = ctk.CTkImage(Image.open("tia-main/assets/psi.png"), size=(511, 509))
                ctk.CTkLabel(frm_vg, image=_img_psi[0], text="").place(x=625, y=100)
            except Exception:
                pass
        lbl_hora.after(1000, tick)
    tick()

    frm_cad = ctk.CTkFrame(tab.tab("CADASTROS"), width=W, height=H,
                            fg_color=FG, border_width=1, border_color="black")
    frm_cad.place(x=10, y=10)
    frm_cad.pack_propagate(False)
    montar_aba_cadastros(frm_cad, win)

    frm_rel = ctk.CTkFrame(tab.tab("RELATÓRIOS"), width=W, height=H,
                            fg_color=FG, border_width=1, border_color="black")
    frm_rel.place(x=10, y=10)
    frm_rel.pack_propagate(False)
    montar_aba_relatorios(frm_rel, win, usuario)

    frm_conf = ctk.CTkFrame(tab.tab("CONFIGURAÇÕES"), width=W, height=H,
                            fg_color=FG, border_width=1, border_color="black")
    frm_conf.place(x=10, y=10)
    frm_conf.pack_propagate(False)
    montar_aba_configuracoes(frm_conf, win, usuario)

    win.mainloop()


os.makedirs("tia", exist_ok=True)
criar_banco()

ctk.set_appearance_mode("light")
loginwin = ctk.CTk()
loginwin.title("Login do sistema")
loginwin.geometry("480x180")
loginwin.configure(fg_color="#f2f2f2")
loginwin.resizable(False, False)

ctk.CTkFrame(loginwin, width=460, height=160, corner_radius=0,
            border_color="#8b8b8b", fg_color="#f2f2f2",
            border_width=1).place(x=10, y=10)

try:
    _img1 = ctk.CTkImage(Image.open("tia-main/assets/homem_cadeado.png"), size=(115, 110))
    ctk.CTkLabel(loginwin, image=_img1, text="").place(x=30, y=35)
except Exception:
    pass

lbl(loginwin, "Informe o Usuário").place(x=180, y=30)

cmb1_var = ctk.StringVar(value="Tereza C")
cmb1     = ctk.CTkComboBox(loginwin, values=["Tereza C"], variable=cmb1_var,
                            height=14, width=130, fg_color="#fdfdfd",
                            border_width=1, border_color="#bdbdbd",
                            corner_radius=2, hover=False)
cmb1.place(x=180, y=56)

lbl(loginwin, "Informe a Senha").place(x=180, y=85)

etr1_var1 = ctk.StringVar()
etr1      = ctk.CTkEntry(loginwin, show="*", textvariable=etr1_var1,
                        height=14, width=130, fg_color="#fdfdfd",
                        border_width=1, corner_radius=2, border_color="#bdbdbd")
etr1.place(x=180, y=111)
etr1.bind("<Return>", lambda _: login1())

ctk.CTkFrame(loginwin, width=134, height=110, corner_radius=0,
            border_color="#8b8b8b", fg_color="#f2f2f2",
            border_width=1).place(x=325, y=34)

try:
    _img2 = ctk.CTkImage(Image.open("tia-main/assets/certo.png"), size=(30, 30))
    btn1  = ctk.CTkButton(loginwin, image=_img2, text="Acessar",
                        compound="left", fg_color="#fafffe",
                        border_color="#a0a0a0", border_width=1,
                        width=100, height=31, text_color="black",
                        cursor="hand1", hover=False, corner_radius=2,
                        command=login1)
except Exception:
    btn1 = ctk.CTkButton(loginwin, text="Acessar", fg_color="#fafffe",
                        border_color="#a0a0a0", border_width=1,
                        width=100, height=31, text_color="black",
                        cursor="hand1", hover=False, corner_radius=2,
                        command=login1)
btn1.place(x=340, y=45)

try:
    _img3 = ctk.CTkImage(Image.open("tia-main/assets/passar.png"),
        size=(30, 30))
    btn2 = ctk.CTkButton(loginwin, image=_img3, text="Sair",
                        compound="left", fg_color="#fafffe",
                        border_color="#a0a0a0", border_width=1,
                        width=100, height=31, text_color="black",
                        cursor="hand1", hover=False, corner_radius=2,
                        command=loginwin.destroy)
except Exception:
    btn2 = ctk.CTkButton(loginwin, text="Sair", fg_color="#fafffe",
                        border_color="#a0a0a0", border_width=1,
                        width=100, height=31, text_color="black",
                        cursor="hand1", hover=False, corner_radius=2,
                        command=loginwin.destroy)
btn2.place(x=340, y=100)

loginwin.mainloop()
