import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import time
import plotly.graph_objects as go
import random
import sqlite3
import hashlib
import re
import json
import os

# compatibilidade: fallback quando st.experimental_rerun / st.rerun não existir
if not hasattr(st, "experimental_rerun"):
    def _st_fallback_rerun():
        # força re-render mínimo alterando uma flag na session_state
        st.session_state["_rerun_toggle"] = not st.session_state.get("_rerun_toggle", False)
    st.experimental_rerun = _st_fallback_rerun
if not hasattr(st, "rerun"):
    st.rerun = st.experimental_rerun

DB_PATH = "fitnesshub.db"

def make_hashes(password):
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_db_connection():
    # garante que o arquivo está no cwd do projeto (evita caminhos relativos inesperados)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            nome TEXT,
            idade INTEGER,
            genero TEXT,
            altura INTEGER,
            peso REAL,
            objetivo TEXT,
            nivel_atividade TEXT,
            meta_peso REAL,
            bmi REAL,
            bmr REAL,
            tdee REAL,
            data_cadastro TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plano_nome TEXT,
            dias_semana TEXT,
            exercicios TEXT,
            data_criacao TEXT,
            UNIQUE(user_id, plano_nome),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS workout_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plano TEXT,
            data TEXT,
            inicio TEXT,
            fim TEXT,
            duracao REAL,
            exercicios_completos TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS food_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data TEXT,
            alimentos TEXT,
            totais TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data TEXT,
            peso REAL,
            circunferencia_abdomen INTEGER,
            observacoes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS water_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data TEXT,
            ml INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sleep_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data TEXT,
            horas REAL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# --- AUTENTICAÇÃO ---
def add_user(email, password):
    email = email.strip().lower()
    hashed = make_hashes(password)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed))
    conn.commit()
    conn.close()

def login_user(email, password):
    email = email.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, password FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    if row and check_hashes(password, row["password"]):
        return row["id"]
    return False

def get_user_email(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["email"] if row else None


# --- PERFIL ---
def save_user_profile(user_id, user_data):
    conn = get_db_connection()
    cur = conn.cursor()
    # upsert profile (unique user_id)
    cur.execute("SELECT id FROM user_profiles WHERE user_id = ?", (user_id,))
    exists = cur.fetchone()
    if exists:
        cur.execute("""
            UPDATE user_profiles
            SET nome=?, idade=?, genero=?, altura=?, peso=?, objetivo=?, nivel_atividade=?, meta_peso=?, bmi=?, bmr=?, tdee=?, data_cadastro=?
            WHERE user_id=?
        """, (
            user_data["nome"], user_data["idade"], user_data["genero"], user_data["altura"],
            user_data["peso"], user_data["objetivo"], user_data["nivel_atividade"],
            user_data.get("meta_peso"), user_data["bmi"], user_data["bmr"], user_data["tdee"],
            user_data["data_cadastro"], user_id
        ))
    else:
        cur.execute("""
            INSERT INTO user_profiles
            (user_id, nome, idade, genero, altura, peso, objetivo, nivel_atividade, meta_peso, bmi, bmr, tdee, data_cadastro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, user_data["nome"], user_data["idade"], user_data["genero"], user_data["altura"],
            user_data["peso"], user_data["objetivo"], user_data["nivel_atividade"],
            user_data.get("meta_peso"), user_data["bmi"], user_data["bmr"], user_data["tdee"],
            user_data["data_cadastro"]
        ))
    conn.commit()
    conn.close()

def load_user_profile(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT nome, idade, genero, altura, peso, objetivo, nivel_atividade, meta_peso, bmi, bmr, tdee, data_cadastro
        FROM user_profiles WHERE user_id = ?
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        keys = ["nome", "idade", "genero", "altura", "peso", "objetivo", "nivel_atividade", "meta_peso", "bmi", "bmr", "tdee", "data_cadastro"]
        return {k: row[k] for k in keys}
    return None

def delete_user_profile(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# --- WORKOUTS (JSON storage) ---
def save_workout_plan(user_id, plan_name, plan_data):
    # upsert: se já existir plano com mesmo nome para o usuário, atualiza
    conn = get_db_connection()
    cur = conn.cursor()
    dias_json = json.dumps(plan_data.get("dias_semana", []), ensure_ascii=False)
    exerc_json = json.dumps(plan_data.get("exercicios", []), ensure_ascii=False)
    cur.execute("SELECT id FROM workouts WHERE user_id = ? AND plano_nome = ?", (user_id, plan_name))
    row = cur.fetchone()
    if row:
        cur.execute("""
            UPDATE workouts
            SET dias_semana = ?, exercicios = ?, data_criacao = ?
            WHERE id = ?
        """, (dias_json, exerc_json, plan_data.get("data_criacao", datetime.now().strftime("%Y-%m-%d")), row["id"]))
    else:
        cur.execute("""
            INSERT INTO workouts (user_id, plano_nome, dias_semana, exercicios, data_criacao)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, plan_name, dias_json, exerc_json, plan_data.get("data_criacao", datetime.now().strftime("%Y-%m-%d"))))
    conn.commit()
    conn.close()

def load_workout_plans(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT plano_nome, dias_semana, exercicios, data_criacao FROM workouts WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    plans = {}
    for row in rows:
        dias = json.loads(row["dias_semana"]) if row["dias_semana"] else []
        exerc = json.loads(row["exercicios"]) if row["exercicios"] else []
        plans[row["plano_nome"]] = {"dias_semana": dias, "exercicios": exerc, "data_criacao": row["data_criacao"]}
    return plans

def save_workout_history(user_id, workout_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO workout_history (user_id, plano, data, inicio, fim, duracao, exercicios_completos)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        workout_data["plano"],
        workout_data["data"],
        workout_data["inicio"],
        workout_data["fim"],
        workout_data["duracao"],
        json.dumps(workout_data["exercicios_completos"], ensure_ascii=False)
    ))
    conn.commit()
    conn.close()

def load_workout_history(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT plano, data, inicio, fim, duracao, exercicios_completos
        FROM workout_history
        WHERE user_id = ?
        ORDER BY data DESC, inicio DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    history = []
    for row in rows:
        history.append({
            "plano": row["plano"],
            "data": row["data"],
            "inicio": row["inicio"],
            "fim": row["fim"],
            "duracao": row["duracao"],
            "exercicios_completos": json.loads(row["exercicios_completos"]) if row["exercicios_completos"] else []
        })
    return history


# --- FOOD LOG: use JSON, não eval/str ---
def save_food_log(user_id, food_data):
    conn = get_db_connection()
    cur = conn.cursor()
    alimentos_json = json.dumps(food_data["alimentos"], ensure_ascii=False)
    totais_json = json.dumps(food_data["totais"], ensure_ascii=False)
    cur.execute("INSERT INTO food_log (user_id, data, alimentos, totais) VALUES (?, ?, ?, ?)",
                (user_id, food_data["data"], alimentos_json, totais_json))
    conn.commit()
    conn.close()

def load_food_log(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT data, alimentos, totais FROM food_log WHERE user_id = ? ORDER BY data DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    food_log = []
    for row in rows:
        alimentos = json.loads(row["alimentos"]) if row["alimentos"] else []
        totais = json.loads(row["totais"]) if row["totais"] else {}
        food_log.append({"data": row["data"], "alimentos": alimentos, "totais": totais})
    return food_log


# --- PROGRESS, WATER, SLEEP ---
def save_progress_data(user_id, progress_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO progress_data (user_id, data, peso, circunferencia_abdomen, observacoes)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, progress_data["data"], progress_data["peso"], progress_data["circunferencia_abdomen"], progress_data["observacoes"]))
    conn.commit()
    conn.close()

def load_progress_data(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT data, peso, circunferencia_abdomen, observacoes FROM progress_data WHERE user_id = ? ORDER BY data DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"data": r["data"], "peso": r["peso"], "circunferencia_abdomen": r["circunferencia_abdomen"], "observacoes": r["observacoes"]} for r in rows]

def save_water_log(user_id, water_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO water_log (user_id, data, ml) VALUES (?, ?, ?)", (user_id, water_data["data"], water_data["ml"]))
    conn.commit()
    conn.close()

def load_water_log(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT data, ml FROM water_log WHERE user_id = ? ORDER BY data DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"data": r["data"], "ml": r["ml"]} for r in rows]

def save_sleep_log(user_id, sleep_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO sleep_log (user_id, data, horas) VALUES (?, ?, ?)", (user_id, sleep_data["data"], sleep_data["horas"]))
    conn.commit()
    conn.close()

def load_sleep_log(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT data, horas FROM sleep_log WHERE user_id = ? ORDER BY data DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"data": r["data"], "horas": r["horas"]} for r in rows]


# --- UI & APP CLASS ---
st.set_page_config(page_title="FitBuddy - Seu Companheiro Fitness", page_icon="💪", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
/* (mantive seu CSS) */
.stApp { background: #232323; }
.main-header { font-size: 2.5rem; color: #ff9800; text-align: center; margin-bottom: 2rem; font-weight: 900; letter-spacing: 1px; text-shadow: 1px 2px 8px #111; }
.sub-header { font-size: 1.25rem; color: #ff9800; margin: 1.2rem 0 0.7rem 0; border-left: 4px solid #ff9800; padding-left: 10px; font-weight: 600; background: #333; border-radius: 4px; }
.metric-card { display: flex; flex-direction: column; background: #181818; padding: 20px 16px 14px 16px; border-radius: 12px; color: #fff; margin: 10px 0; box-shadow: 0 2px 8px rgba(30,30,30,0.13); text-align: center; font-weight: 600; border: 1px solid #444; transition: box-shadow 0.2s, border 0.2s; border-left: 5px solid #ff9800; }
.metric-card:hover { box-shadow: 0 4px 16px rgba(255,152,0,0.13); border-left: 5px solid #ffa726; }
.workout-card, .food-card { background: #232323; border-radius: 8px; padding: 13px; margin: 10px 0; border-left: 4px solid #ff9800; box-shadow: 0 1px 4px rgba(30,30,30,0.10); color: #fff; }
.food-card { border-left: 4px solid #ffa726; } .completed { background: #2e2e2e; border-left: 4px solid #ffb74d; }
.stButton button { width: 100%; border-radius: 7px; background: linear-gradient(90deg, #ff9800 0%, #ffa726 100%); color: #181818; font-weight: bold; border: none; padding: 0.7em 0; font-size: 1.08em; box-shadow: 0 1px 4px rgba(255,152,0,0.10); transition: background 0.2s, transform 0.2s; }
.stButton button:hover { background: linear-gradient(90deg, #ffa726 0%, #ff9800 100%); color: #fff; transform: scale(1.01); }
.section-divider { height: 2px; background: linear-gradient(90deg, transparent, #ff9800, transparent); margin: 1.2rem 0; border-radius: 2px; }
[data-testid="stSidebar"] { background: #181818; color: #fff; }
.login-container { background: #1e1e1e; padding: 2rem; border-radius: 12px; border: 1px solid #444; margin: 2rem auto; max-width: 500px; }
.login-header { text-align: center; color: #ff9800; margin-bottom: 1.5rem; font-size: 1.8rem; }
</style>""", unsafe_allow_html=True)


class FitnessHub:
    def __init__(self):
        create_tables()
        self.initialize_session_state()
        self.load_food_database()
        self.load_motivational_phrases()
        self.load_jokes()

    def initialize_session_state(self):
        defaults = {
            "user_id": None,
            "user_email": None,
            "user_data": None,
            "workout_plans": {},
            "active_workout": None,
            "workout_history": [],
            "diet_plans": {},
            "active_diet": None,
            "food_log": [],
            "progress_data": [],
            "current_date": datetime.now().date(),
            "selected_plan": None,
            "today_food": [],
            "water_log": [],
            "sleep_log": [],
            "selected": "Dashboard",
            "just_logged_in": False,
            "start_time": None
        }
        for k, v in defaults.items():
            if k not in st.session_state:
                st.session_state[k] = v

    def load_food_database(self):
        # mantive a sua base de alimentos
        self.food_db = {
            "Proteínas": { "Peito de Frango (100g)": {"calorias":165,"proteina":31,"carboidrato":0,"gordura":3.6}, "Ovo (1 unidade)": {"calorias":78,"proteina":6,"carboidrato":0.6,"gordura":5}, "Salmão (100g)": {"calorias":208,"proteina":20,"carboidrato":0,"gordura":13} },
            "Carboidratos": { "Arroz Integral (100g cozido)": {"calorias":112,"proteina":2.6,"carboidrato":23,"gordura":0.9}, "Batata Doce (100g)": {"calorias":86,"proteina":1.6,"carboidrato":20,"gordura":0.1} },
            "Gorduras": { "Abacate (100g)": {"calorias":160,"proteina":2,"carboidrato":9,"gordura":15}, "Azeite de Oliva (1 colher)": {"calorias":119,"proteina":0,"carboidrato":0,"gordura":14} },
            "Vegetais": { "Brócolis (100g)": {"calorias":34,"proteina":2.8,"carboidrato":7,"gordura":0.4}, "Espinafre (100g)": {"calorias":23,"proteina":2.9,"carboidrato":3.6,"gordura":0.4} }
        }

    def load_motivational_phrases(self):
        self.motivational_phrases = ["Acredite em você! Cada passo conta.","Você é mais forte do que imagina.","Disciplina é o caminho para o sucesso."]

    def load_jokes(self):
        self.jokes = ["Por que o computador foi ao médico? Porque estava com um vírus!","O que o zero disse para o oito? Belo cinto!"]

    def login_section(self):
        st.markdown('<div class="login-header">💪 FitBuddy</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align: center; margin-bottom: 2rem; color: #ffa726;">Seu Companheiro Fitness<br><br>NÃO UTILIZE DADOS REAIS</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Login", "Registrar"])

        with tab1:
            with st.form("login_form"):
                email = st.text_input("EMAIL")
                password = st.text_input("SENHA", type="password")
                submit = st.form_submit_button("Entrar")
                if submit:
                    if not email or not password:
                        st.error("Preencha email e senha")
                    else:
                        user_id = login_user(email, password)
                        if user_id:
                            st.session_state.user_id = user_id
                            st.session_state.user_email = email.strip().lower()
                            st.session_state.just_logged_in = True
                            st.success("Login realizado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Email ou senha incorretos")

        with tab2:
            with st.form("register_form"):
                email = st.text_input("EMAIL")
                password = st.text_input("SENHA", type="password")
                confirm_password = st.text_input("CONFIRMAR SENHA", type="password")
                submit = st.form_submit_button("Criar Conta")
                if submit:
                    email = (email or "").strip().lower()
                    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                        st.error("Por favor, insira um email válido")
                    elif len(password or "") < 3:
                        st.error("A senha deve ter pelo menos 3 caracteres")
                    elif password != confirm_password:
                        st.error("As senhas não coincidem")
                    else:
                        try:
                            add_user(email, password)
                            st.success("Conta criada com sucesso! Faça login.")
                        except sqlite3.IntegrityError:
                            st.error("Este email já está em uso")

    def load_user_data(self):
        if st.session_state.user_id:
            st.session_state.user_data = load_user_profile(st.session_state.user_id)
            st.session_state.workout_plans = load_workout_plans(st.session_state.user_id)
            st.session_state.workout_history = load_workout_history(st.session_state.user_id)
            st.session_state.food_log = load_food_log(st.session_state.user_id)
            st.session_state.progress_data = load_progress_data(st.session_state.user_id)
            st.session_state.water_log = load_water_log(st.session_state.user_id)
            st.session_state.sleep_log = load_sleep_log(st.session_state.user_id)

    def logout(self):
        # limpa apenas chaves do app para não perder dados do navegador
        keys = list(st.session_state.keys())
        for k in keys:
            del st.session_state[k]
        self.initialize_session_state()
        st.experimental_rerun()

    def motivational_card(self):
        st.markdown('<div class="sub-header">💡 Motivação do Dia</div>', unsafe_allow_html=True)
        st.info(f"**{random.choice(self.motivational_phrases)}**")

    def joke_card(self):
        st.markdown('<div class="sub-header">😂 Sorria!</div>', unsafe_allow_html=True)
        st.success(f"_{random.choice(self.jokes)}_")

    def calculate_bmi(self, weight, height):
        try:
            h = height / 100
            return round(weight / (h * h), 1)
        except:
            return 0

    def calculate_bmr(self, weight, height, age, gender):
        if gender == "Masculino":
            return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        else:
            return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

    def calculate_tdee(self, bmr, activity_level):
        multipliers = {"Sedentário":1.2,"Levemente ativo":1.375,"Moderadamente ativo":1.55,"Muito ativo":1.725,"Extremamente ativo":1.9}
        return int(bmr * multipliers.get(activity_level, 1.2))

    def calculate_water_goal(self, weight, activity_level):
        base = weight * 35
        bonus = {"Sedentário":0,"Levemente ativo":250,"Moderadamente ativo":500,"Muito ativo":750,"Extremamente ativo":1000}
        return int(base + bonus.get(activity_level, 0))

    def calculate_calorie_goal(self, tdee, objetivo):
        if objetivo == "Ganho de massa":
            return int(tdee * 1.15)
        elif objetivo == "Perda de peso":
            return int(tdee * 0.85)
        elif objetivo == "Definição muscular":
            return int(tdee * 0.90)
        else:
            return int(tdee)

    def calculate_min_training_time(self, objetivo, nivel_atividade):
        base = 30
        if objetivo == "Ganho de massa":
            base = 45
        elif objetivo == "Perda de peso":
            base = 40
        elif objetivo == "Definição muscular":
            base = 50
        bonus = {"Sedentário":0,"Levemente ativo":5,"Moderadamente ativo":10,"Muito ativo":15,"Extremamente ativo":20}
        return base + bonus.get(nivel_atividade, 0)

    # --- cadastro ---
    def user_registration(self):
        st.markdown('<div class="sub-header">👤 Cadastro do Usuário</div>', unsafe_allow_html=True)
        if st.session_state.user_data:
            st.info(f"Usuário cadastrado: {st.session_state.user_data['nome']}")
            if st.button("🗑️ Excluir Perfil"):
                delete_user_profile(st.session_state.user_id)
                st.session_state.user_data = None
                st.success("Perfil excluído")
                st.rerun()
            return

        with st.form("user_registration"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome Completo*").strip()
                idade = st.number_input("Idade*", min_value=10, max_value=100, step=1)
                genero = st.selectbox("Gênero*", ["Masculino", "Feminino", "Outro"])
                altura = st.number_input("Altura (cm)*", min_value=100, max_value=250, step=1)
            with col2:
                peso = st.number_input("Peso (kg)*", min_value=20.0, max_value=300.0, step=0.1)
                objetivo = st.selectbox("Objetivo*", ["Perda de peso", "Ganho de massa", "Manutenção", "Definição muscular"])
                nivel_atividade = st.selectbox("Nível de Atividade*", ["Sedentário", "Levemente ativo", "Moderadamente ativo", "Muito ativo", "Extremamente ativo"])
                meta_peso = st.number_input("Meta de Peso (kg)", min_value=20.0, max_value=300.0, step=0.1, value=peso)
            submit = st.form_submit_button("Salvar Perfil")
            if submit:
                required = all([nome, idade, genero, altura, peso, objetivo, nivel_atividade])
                if not required:
                    st.error("Por favor, preencha todos os campos obrigatórios (*)")
                    return
                bmi = self.calculate_bmi(peso, altura)
                bmr = self.calculate_bmr(peso, altura, int(idade), genero)
                tdee = self.calculate_tdee(bmr, nivel_atividade)
                user_data = {"nome": nome, "idade": int(idade), "genero": genero, "altura": int(altura), "peso": float(peso),
                             "objetivo": objetivo, "nivel_atividade": nivel_atividade, "meta_peso": float(meta_peso),
                             "bmi": float(bmi), "bmr": float(bmr), "tdee": int(tdee), "data_cadastro": datetime.now().strftime("%Y-%m-%d")}
                save_user_profile(st.session_state.user_id, user_data)
                st.session_state.user_data = user_data
                st.success("Perfil salvo com sucesso!")
                st.rerun()

    # --- criar plano (tabela/lista de exercícios) ---
    
    def create_workout_plan(self):
        st.markdown('<div class="sub-header">🏋️ Criar Plano de Treino</div>', unsafe_allow_html=True)
        if not st.session_state.user_data:
            st.warning("Complete seu cadastro primeiro!")
            return

        if "tmp_plan" not in st.session_state:
            st.session_state.tmp_plan = {"nome_plano": "", "dias_semana": [], "exercicios": []}

        with st.form("workout_plan"):
            # usar valores atuais da sessão como default — não sobrescrever keys de widget depois
            nome_default = st.session_state.tmp_plan.get("nome_plano", "")
            dias_default = st.session_state.tmp_plan.get("dias_semana", [])
            st.session_state.tmp_plan["nome_plano"] = st.text_input("Nome do Plano*", value=nome_default)
            st.session_state.tmp_plan["dias_semana"] = st.multiselect(
                "Dias da Semana*",
                ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"],
                default=dias_default
            )

            st.markdown("**Adicionar Exercício (ordem preservada)**")
            colg, cole, col1, col2, col3 = st.columns([2,3,2,2,2])
            with colg:
                grupo = colg.selectbox("Grupo Muscular", ["Peito","Costas","Pernas","Ombros","Braços","Abdômen"], key="new_grp")
            with cole:
                exercicio = cole.text_input("Nome do Exercício", key="new_ex")
            with col1:
                series = col1.number_input("Séries", min_value=1, max_value=10, value=3, key="new_ser")
            with col2:
                repeticoes = col2.number_input("Repetições", min_value=1, max_value=50, value=12, key="new_rep")
            with col3:
                descanso = col3.number_input("Descanso (s)", min_value=10, max_value=600, value=60, key="new_desc")

            add_ex = st.form_submit_button("Adicionar Exercício")
            if add_ex:
                if exercicio and exercicio.strip():
                    st.session_state.tmp_plan["exercicios"].append({
                        "grupo": grupo,
                        "exercicio": exercicio.strip(),
                        "series": int(series),
                        "repeticoes": int(repeticoes),
                        "descanso": int(descanso)
                    })
                    # NÃO sobrescrever st.session_state["new_ex"] aqui — apenas rerun para atualizar UI
                    st.experimental_rerun()
                else:
                    st.error("Informe o nome do exercício")

        # exibe exercícios adicionados com controles de ordem/remoção
        if st.session_state.tmp_plan["exercicios"]:
            st.markdown("**Exercícios adicionados (ordem):**")
            for idx, ex in enumerate(st.session_state.tmp_plan["exercicios"]):
                cols = st.columns([6,1,1])
                with cols[0]:
                    st.write(f"{idx+1}. {ex['grupo']} — {ex['exercicio']} — {ex['series']}×{ex['repeticoes']} (desc {ex['descanso']}s)")
                with cols[1]:
                    if st.button("↑", key=f"up_{idx}") and idx > 0:
                        lst = st.session_state.tmp_plan["exercicios"]
                        lst[idx-1], lst[idx] = lst[idx], lst[idx-1]
                        st.experimental_rerun()
                with cols[2]:
                    if st.button("✖", key=f"del_{idx}"):
                        st.session_state.tmp_plan["exercicios"].pop(idx)
                        st.experimental_rerun()

        st.markdown("---")
        if st.button("Salvar Plano de Treino Final"):
            nome_plano = st.session_state.tmp_plan["nome_plano"].strip()
            dias_semana = st.session_state.tmp_plan["dias_semana"]
            plano_treino = st.session_state.tmp_plan["exercicios"]
            if not nome_plano:
                st.error("Informe um nome para o plano.")
            elif not dias_semana:
                st.error("Selecione ao menos um dia da semana.")
            elif not plano_treino:
                st.error("Adicione ao menos um exercício.")
            else:
                plan_data = {"dias_semana": dias_semana, "exercicios": plano_treino, "data_criacao": datetime.now().strftime("%Y-%m-%d")}
                save_workout_plan(st.session_state.user_id, nome_plano, plan_data)
                st.session_state.workout_plans[nome_plano] = plan_data
                st.session_state.tmp_plan = {"nome_plano":"", "dias_semana":[], "exercicios":[]}
                st.success(f"Plano '{nome_plano}' salvo com sucesso!")

    # --- iniciar treino ---
    def start_workout(self):
        if not st.session_state.workout_plans:
            st.warning("Nenhum plano disponível. Crie um plano primeiro.")
            return
        st.markdown('<div class="sub-header">🚀 Iniciar Treino</div>', unsafe_allow_html=True)
        planos = list(st.session_state.workout_plans.keys())
        plano_selecionado = st.selectbox("Selecione o plano de treino", planos, index=0)
        if st.button("Iniciar Treino"):
            st.session_state.active_workout = {"plano": plano_selecionado, "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "exercicios_completos": [], "status":"em_andamento"}
            st.session_state.start_time = time.time()
            st.success(f"Treino '{plano_selecionado}' iniciado!")
            st.experimental_rerun()

    # --- tracker que permite completar apenas o próximo exercício ---
    def workout_tracker(self):
        if not st.session_state.active_workout:
            return
        st.markdown('<div class="sub-header">⏱️ Treino em Andamento</div>', unsafe_allow_html=True)
        plano_nome = st.session_state.active_workout.get("plano")
        plano = st.session_state.workout_plans.get(plano_nome)
        if not plano:
            st.error("Plano não encontrado.")
            return

        st.info(f"Plano: {plano_nome} | Iniciado: {st.session_state.active_workout.get('inicio')}")
        if not st.session_state.start_time:
            st.session_state.start_time = time.time()
        elapsed_time = time.time() - st.session_state.start_time
        mins, secs = divmod(int(elapsed_time), 60)
        st.write(f"⏰ Tempo decorrido: {mins:02d}:{secs:02d}")

        exercises = plano.get("exercicios", [])
        completed_indices = st.session_state.active_workout.get("exercicios_completos", [])
        # next incomplete index
        next_idx = next((i for i in range(len(exercises)) if i not in completed_indices), None)

        for i, ex in enumerate(exercises):
            done = i in completed_indices
            card_class = "workout-card completed" if done else "workout-card"
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            st.markdown(f"**{i+1}. {ex['grupo']}**: {ex['exercicio']}")
            st.markdown(f"Séries: {ex['series']} × {ex['repeticoes']} reps | Descanso: {ex['descanso']}s")
            if not done:
                if i == next_idx:
                    if st.button(f"Completar {i+1}", key=f"complete_{i}"):
                        st.session_state.active_workout.setdefault("exercicios_completos", []).append(i)
                        st.experimental_rerun()
                else:
                    st.button(f"Completar {i+1}", key=f"disabled_{i}", disabled=True)
            else:
                st.markdown("✅ Concluído")
            st.markdown("</div>", unsafe_allow_html=True)

        todos_completos = len(st.session_state.active_workout.get("exercicios_completos", [])) == len(exercises)
        if st.button("Finalizar Treino", disabled=not todos_completos):
            fim = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            duracao = time.time() - st.session_state.start_time
            # montar lista legível de exercícios concluídos
            completed_list = []
            for idx in st.session_state.active_workout.get("exercicios_completos", []):
                ex = exercises[idx]
                completed_list.append(f"{idx+1}. {ex['grupo']} — {ex['exercicio']}")
            registro = {"plano": plano_nome, "data": datetime.now().strftime("%Y-%m-%d"), "inicio": st.session_state.active_workout.get("inicio"), "fim": fim, "duracao": duracao, "exercicios_completos": completed_list}
            save_workout_history(st.session_state.user_id, registro)
            st.session_state.workout_history.append(registro)
            st.session_state.active_workout = None
            st.session_state.start_time = None
            st.success("Treino finalizado e salvo no histórico!")
            st.experimental_rerun()

    # --- food logger, dashboard, history, progress, dashboard main (mantive lógica e corrigi JSON) ---
    def food_logger(self):
        st.markdown('<div class="sub-header">🍽️ Registro de Alimentos</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Adicionar Alimento**")
            categoria = st.selectbox("Categoria", list(self.food_db.keys()))
            alimento = st.selectbox("Alimento", list(self.food_db[categoria].keys()))
            col_qtd, col_unid = st.columns(2)
            with col_qtd:
                quantidade = st.number_input("Quantidade", min_value=1.0, value=100.0, step=1.0, format="%.1f")
            with col_unid:
                unidade = st.selectbox("Unidade", ["g", "unidades"])
            if st.button("Adicionar à Refeição"):
                alimento_info = dict(self.food_db[categoria][alimento])
                alimento_info["nome"] = alimento
                alimento_info["categoria"] = categoria
                alimento_info["quantidade"] = float(quantidade)
                alimento_info["unidade"] = unidade
                st.session_state.today_food.append(alimento_info)
                st.success(f"{alimento} adicionado!")
        with col2:
            st.markdown("**Sua Refeição de Hoje**")
            if st.session_state.today_food:
                total_calorias = total_proteina = total_carboidrato = total_gordura = 0.0
                for alimento in st.session_state.today_food:
                    fator = (alimento["quantidade"] / 100.0) if alimento["unidade"] == "g" else alimento["quantidade"]
                    calorias = alimento["calorias"] * fator
                    proteina = alimento["proteina"] * fator
                    carbo = alimento["carboidrato"] * fator
                    gordura = alimento["gordura"] * fator
                    total_calorias += calorias
                    total_proteina += proteina
                    total_carboidrato += carbo
                    total_gordura += gordura
                    st.markdown(f"""<div class="food-card"><b>{alimento['nome']}</b> - {alimento['quantidade']}{alimento['unidade']}<br>Calorias: {calorias:.1f} | Proteína: {proteina:.1f}g | Carbs: {carbo:.1f}g | Gordura: {gordura:.1f}g</div>""", unsafe_allow_html=True)
                st.markdown("---")
                st.markdown(f"""**Totais:**<br>🔥 Calorias: {total_calorias:.1f}kcal<br>💪 Proteína: {total_proteina:.1f}g<br>🍞 Carboidratos: {total_carboidrato:.1f}g<br>🥑 Gorduras: {total_gordura:.1f}g""", unsafe_allow_html=True)
                if st.button("Salvar Refeição do Dia"):
                    refeicao = {"data": datetime.now().strftime("%Y-%m-%d"), "alimentos": st.session_state.today_food.copy(), "totais": {"calorias": total_calorias, "proteina": total_proteina, "carboidrato": total_carboidrato, "gordura": total_gordura}}
                    save_food_log(st.session_state.user_id, refeicao)
                    st.session_state.food_log.insert(0, refeicao)
                    st.session_state.today_food = []
                    st.success("Refeição salva no histórico!")
            else:
                st.info("Nenhum alimento adicionado hoje.")

    def nutrition_dashboard(self):
        st.markdown('<div class="sub-header">📊 Dashboard Nutricional</div>', unsafe_allow_html=True)
        if not st.session_state.food_log:
            st.info("Nenhum registro alimentar encontrado.")
            return
        dias = []
        calorias_dia = []
        proteinas_dia = []
        carbs_dia = []
        gorduras_dia = []
        for registro in st.session_state.food_log[:7]:
            dias.append(registro["data"])
            calorias_dia.append(registro["totais"]["calorias"])
            proteinas_dia.append(registro["totais"]["proteina"])
            carbs_dia.append(registro["totais"]["carboidrato"])
            gorduras_dia.append(registro["totais"]["gordura"])
        fig_cal = go.Figure()
        fig_cal.add_trace(go.Scatter(x=dias, y=calorias_dia, mode='lines+markers', name='Calorias', line=dict(color='#FF6B6B', width=3)))
        if st.session_state.user_data:
            tdee = st.session_state.user_data.get("tdee")
            if tdee:
                fig_cal.add_hline(y=tdee, line_dash="dash", line_color="green", annotation_text="Meta Calórica Diária")
        fig_cal.update_layout(title="Consumo Calórico Diário", xaxis_title="Data", yaxis_title="Calorias")
        st.plotly_chart(fig_cal, use_container_width=True)

    def workout_history_view(self):
        st.markdown('<div class="sub-header">📋 Histórico de Treinos</div>', unsafe_allow_html=True)
        if not st.session_state.workout_history:
            st.info("Nenhum treino registrado ainda.")
            return
        for treino in st.session_state.workout_history:
            with st.expander(f"{treino['data']} - {treino['plano']} - {int(treino['duracao']//60)}min"):
                st.write(f"**Início:** {treino['inicio']}")
                st.write(f"**Término:** {treino['fim']}")
                st.write(f"**Duração:** {int(treino['duracao']//60)} minutos")
                st.write("**Exercícios completos:**")
                for exercicio in treino['exercicios_completos']:
                    st.write(f"- {exercicio}")

    def progress_tracking(self):
        st.markdown('<div class="sub-header">📈 Acompanhamento de Progresso</div>', unsafe_allow_html=True)
        if not st.session_state.user_data:
            st.warning("Complete seu cadastro primeiro!")
            return
        with st.form("progress_tracking"):
            data = st.date_input("Data", datetime.now())
            peso = st.number_input("Peso (kg)", min_value=20.0, max_value=300.0, step=0.1, value=st.session_state.user_data.get("peso", 70.0))
            circunferencia = st.number_input("Circunferência Abdômen (cm)", min_value=50, max_value=200, value=80)
            observacoes = st.text_area("Observações")
            submit = st.form_submit_button("Registrar Progresso")
            if submit:
                registro = {"data": data.strftime("%Y-%m-%d"), "peso": float(peso), "circunferencia_abdomen": int(circunferencia), "observacoes": observacoes}
                save_progress_data(st.session_state.user_id, registro)
                st.session_state.progress_data.insert(0, registro)
                # atualiza peso no perfil em sessão
                if st.session_state.user_data:
                    st.session_state.user_data["peso"] = float(peso)
                st.success("Progresso registrado com sucesso!")
        if st.session_state.progress_data:
            df = pd.DataFrame(st.session_state.progress_data)
            df['data'] = pd.to_datetime(df['data'])
            df = df.sort_values('data')
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['data'], y=df['peso'], mode='lines+markers', name='Peso (kg)', line=dict(color='#FF6B6B', width=3)))
            if st.session_state.user_data.get("meta_peso"):
                fig.add_hline(y=st.session_state.user_data["meta_peso"], line_dash="dash", line_color="green", annotation_text="Meta de Peso")
            fig.update_layout(title="Evolução do Peso", xaxis_title="Data", yaxis_title="Peso (kg)", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    def dashboard(self):
        st.markdown('<h1 class="main-header">💪 FitBuddy</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; font-size: 1.2rem;">Seu Companheiro Fitness Completo</p>', unsafe_allow_html=True)
        if not st.session_state.user_data:
            st.info("👋 Bem-vindo! Complete seu cadastro para personalizar sua experiência.")
            return
        user = st.session_state.user_data
        meta_agua = self.calculate_water_goal(user['peso'], user['nivel_atividade'])
        meta_calorias = self.calculate_calorie_goal(user['tdee'], user['objetivo'])
        meta_treino = self.calculate_min_training_time(user['objetivo'], user['nivel_atividade'])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"<div class='metric-card'><h3>📊 IMC</h3><h2>{user['bmi']:.1f}</h2><p>{self.classify_bmi(user['bmi'])}</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h3>🔥 Calorias</h3><h2>{meta_calorias} kcal</h2><p>Meta diária</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><h3>💧 Água</h3><h2>{meta_agua} ml</h2><p>Meta diária</p></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='metric-card'><h3>⏱️ Duração do Treino</h3><h2>{meta_treino} min</h2><p>Por sessão</p></div>", unsafe_allow_html=True)

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🏋️ Iniciar Treino", use_container_width=True):
                st.session_state.selected = "Iniciar Treino"
                st.rerun()
        with col2:
            if st.button("🍽️ Registrar Refeição", use_container_width=True):
                st.session_state.selected = "Registrar Refeição"
                st.rerun()
        with col3:
            if st.button("📈 Registrar Progresso", use_container_width=True):
                st.session_state.selected = "Acompanhamento"
                st.rerun()

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📋 Treinos Recentes")
            if st.session_state.workout_history:
                for treino in st.session_state.workout_history[:3]:
                    st.write(f"**{treino['data']}**: {treino['plano']} ({int(treino['duracao']//60)} min)")
            else:
                st.info("Nenhum treino registrado")
        with col2:
            st.subheader("🍽️ Refeições Recentes")
            if st.session_state.food_log:
                for refeicao in st.session_state.food_log[:3]:
                    st.write(f"**{refeicao['data']}**: {refeicao['totais']['calorias']:.0f} kcal")
            else:
                st.info("Nenhuma refeição registrada")

        st.markdown("---")
        self.motivational_card()
        self.joke_card()
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            self.water_tracker(meta_agua=meta_agua)
        with c2:
            self.sleep_tracker()

    def water_tracker(self, meta_agua=None):
        st.markdown('<div class="sub-header">💧 Controle de Água</div>', unsafe_allow_html=True)
        today = datetime.now().strftime("%Y-%m-%d")
        water_today = [w for w in st.session_state.water_log if w["data"] == today]
        total_ml = sum([w["ml"] for w in water_today])
        st.write(f"Total consumido hoje: **{total_ml} ml**")
        ml = st.number_input("Adicionar água (ml)", min_value=50, max_value=2000, step=50, value=250)
        if st.button("Registrar Água"):
            water_data = {"data": today, "ml": int(ml)}
            save_water_log(st.session_state.user_id, water_data)
            st.session_state.water_log.insert(0, water_data)
            st.success(f"{ml} ml adicionados!")
            st.rerun()
        meta = meta_agua or 2000
        st.progress(min(total_ml/meta, 1.0), text=f"Meta diária: {meta}ml")

    def sleep_tracker(self):
        st.markdown('<div class="sub-header">😴 Controle de Sono</div>', unsafe_allow_html=True)
        today = datetime.now().strftime("%Y-%m-%d")
        horas = st.number_input("Horas de sono na última noite", min_value=0.0, max_value=24.0, step=0.5, value=8.0)
        if st.button("Registrar Sono"):
            sleep_data = {"data": today, "horas": float(horas)}
            save_sleep_log(st.session_state.user_id, sleep_data)
            st.session_state.sleep_log.insert(0, sleep_data)
            st.success(f"{horas} horas registradas!")
            st.rerun()
        sleep_today = [s for s in st.session_state.sleep_log if s["data"] == today]
        if sleep_today:
            st.write(f"Hoje: {sleep_today[0]['horas']} horas")
        else:
            st.info("Registre suas horas de sono para acompanhar seu descanso.")

    def classify_bmi(self, bmi):
        if bmi < 18.5:
            return "Abaixo do peso"
        elif 18.5 <= bmi < 25:
            return "Peso normal"
        elif 25 <= bmi < 30:
            return "Sobrepeso"
        else:
            return "Obesidade"

    def run(self):
        if not st.session_state.user_id:
            self.login_section()
            return

        if "selected" not in st.session_state:
            st.session_state.selected = "Dashboard"

        with st.sidebar:
            st.title("💪 FitBuddy")
            st.markdown(f"**Usuário:** {st.session_state.user_email or get_user_email(st.session_state.user_id)}")
            st.markdown("---")
            menu_options = {"Dashboard":"📊","Cadastro":"👤","Criar Plano de Treino":"🏋️","Iniciar Treino":"🚀","Registrar Refeição":"🍽️","Dashboard Nutricional":"📈","Histórico de Treinos":"📋","Acompanhamento":"🎯"}
            for option, emoji in menu_options.items():
                if st.button(f"{emoji} {option}", use_container_width=True, key=f"btn_{option}"):
                    st.session_state.selected = option
                    st.rerun()

            st.markdown("---")
            if st.session_state.user_data:
                st.markdown("### 👤 Seu Perfil")
                user = st.session_state.user_data
                st.write(f"**Nome:** {user['nome']}")
                st.write(f"**Idade:** {user['idade']} anos")
                st.write(f"**Peso:** {user['peso']} kg")
                st.write(f"**Objetivo:** {user['objetivo']}")
            st.markdown("---")
            if st.button("🚪 Sair", use_container_width=True):
                self.logout()
            st.markdown("*FitBuddy - Versão 1.0*<br><span style='font-size:0.9em;color:#888;'>by Guilherme Gama</span>", unsafe_allow_html=True)

        if st.session_state.just_logged_in:
            self.load_user_data()
            st.session_state.just_logged_in = False

        sel = st.session_state.selected
        if sel == "Dashboard":
            self.dashboard()
        elif sel == "Cadastro":
            self.user_registration()
        elif sel == "Criar Plano de Treino":
            self.create_workout_plan()
        elif sel == "Iniciar Treino":
            self.start_workout()
            self.workout_tracker()
        elif sel == "Registrar Refeição":
            self.food_logger()
        elif sel == "Dashboard Nutricional":
            self.nutrition_dashboard()
        elif sel == "Histórico de Treinos":
            self.workout_history_view()
        elif sel == "Acompanhamento":
            self.progress_tracking()

if __name__ == "__main__":
    app = FitnessHub()
    app.run()