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

# --- CONFIGURAÇÃO DE AUTENTICAÇÃO ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- BANCO DE DADOS SQLITE ---
def get_db_connection():
    conn = sqlite3.connect("fitnesshub.db", check_same_thread=False)
    return conn

def create_tables():
    conn = get_db_connection()
    
    # Tabela de usuários (autenticação)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de perfis de usuário
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
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
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Tabela de treinos
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plano_nome TEXT,
            dias_semana TEXT,
            exercicios TEXT,
            data_criacao TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Tabela de histórico de treinos
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workout_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plano TEXT,
            data TEXT,
            inicio TEXT,
            fim TEXT,
            duracao REAL,
            exercicios_completos TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Tabela de registro alimentar
    conn.execute("""
        CREATE TABLE IF NOT EXISTS food_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data TEXT,
            alimentos TEXT,
            totais TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Tabela de progresso
    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data TEXT,
            peso REAL,
            circunferencia_abdomen INTEGER,
            observacoes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Tabela de água
    conn.execute("""
        CREATE TABLE IF NOT EXISTS water_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data TEXT,
            ml INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Tabela de sono
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sleep_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data TEXT,
            horas REAL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

# --- FUNÇÕES DE AUTENTICAÇÃO ---
def add_user(email, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (email, password) VALUES (?, ?)", 
                (email, make_hashes(password)))
    conn.commit()
    conn.close()

def login_user(email, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    data = cur.fetchone()
    conn.close()
    
    if data and check_hashes(password, data[2]):
        return data[0]  # Retorna o user_id
    return False

def get_user_email(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    data = cur.fetchone()
    conn.close()
    return data[0] if data else None

# --- FUNÇÕES DE PERFIL DO USUÁRIO ---
def save_user_profile(user_id, user_data):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verifica se já existe um perfil para este usuário
    cur.execute("SELECT id FROM user_profiles WHERE user_id = ?", (user_id,))
    existing_profile = cur.fetchone()
    
    if existing_profile:
        # Atualiza o perfil existente
        cur.execute("""
            UPDATE user_profiles 
            SET nome=?, idade=?, genero=?, altura=?, peso=?, objetivo=?, 
                nivel_atividade=?, meta_peso=?, bmi=?, bmr=?, tdee=?, data_cadastro=?
            WHERE user_id=?
        """, (
            user_data["nome"], user_data["idade"], user_data["genero"], user_data["altura"], 
            user_data["peso"], user_data["objetivo"], user_data["nivel_atividade"], 
            user_data["meta_peso"], user_data["bmi"], user_data["bmr"], user_data["tdee"], 
            user_data["data_cadastro"], user_id
        ))
    else:
        # Insere um novo perfil
        cur.execute("""
            INSERT INTO user_profiles 
            (user_id, nome, idade, genero, altura, peso, objetivo, nivel_atividade, 
             meta_peso, bmi, bmr, tdee, data_cadastro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, user_data["nome"], user_data["idade"], user_data["genero"], 
            user_data["altura"], user_data["peso"], user_data["objetivo"], 
            user_data["nivel_atividade"], user_data["meta_peso"], user_data["bmi"], 
            user_data["bmr"], user_data["tdee"], user_data["data_cadastro"]
        ))
    
    conn.commit()
    conn.close()

def load_user_profile(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT nome, idade, genero, altura, peso, objetivo, nivel_atividade, 
               meta_peso, bmi, bmr, tdee, data_cadastro 
        FROM user_profiles 
        WHERE user_id = ?
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        keys = ["nome", "idade", "genero", "altura", "peso", "objetivo", 
                "nivel_atividade", "meta_peso", "bmi", "bmr", "tdee", "data_cadastro"]
        return dict(zip(keys, row))
    return None

def delete_user_profile(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- FUNÇÕES PARA DADOS DO USUÁRIO ---
def save_workout_plan(user_id, plan_name, plan_data):
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO workouts (user_id, plano_nome, dias_semana, exercicios, data_criacao)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, plan_name, 
          ','.join(plan_data["dias_semana"]), 
          str(plan_data["exercicios"]), 
          datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def load_workout_plans(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT plano_nome, dias_semana, exercicios FROM workouts WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    plans = {}
    for row in rows:
        plans[row[0]] = {
            "dias_semana": row[1].split(','),
            "exercicios": eval(row[2]),
            "data_criacao": row[3] if len(row) > 3 else ""
        }
    return plans

def save_workout_history(user_id, workout_data):
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO workout_history 
        (user_id, plano, data, inicio, fim, duracao, exercicios_completos)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, workout_data["plano"], workout_data["data"], 
        workout_data["inicio"], workout_data["fim"], workout_data["duracao"],
        str(workout_data["exercicios_completos"])
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
            "plano": row[0],
            "data": row[1],
            "inicio": row[2],
            "fim": row[3],
            "duracao": row[4],
            "exercicios_completos": eval(row[5]) if row[5] else []
        })
    return history

def save_food_log(user_id, food_data):
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO food_log (user_id, data, alimentos, totais)
        VALUES (?, ?, ?, ?)
    """, (
        user_id, food_data["data"], str(food_data["alimentos"]), str(food_data["totais"])
    ))
    conn.commit()
    conn.close()

def load_food_log(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT data, alimentos, totais 
        FROM food_log 
        WHERE user_id = ? 
        ORDER BY data DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    food_log = []
    for row in rows:
        food_log.append({
            "data": row[0],
            "alimentos": eval(row[1]) if row[1] else [],
            "totais": eval(row[2]) if row[2] else {}
        })
    return food_log

def save_progress_data(user_id, progress_data):
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO progress_data (user_id, data, peso, circunferencia_abdomen, observacoes)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id, progress_data["data"], progress_data["peso"], 
        progress_data["circunferencia_abdomen"], progress_data["observacoes"]
    ))
    conn.commit()
    conn.close()

def load_progress_data(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT data, peso, circunferencia_abdomen, observacoes 
        FROM progress_data 
        WHERE user_id = ? 
        ORDER BY data DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    progress = []
    for row in rows:
        progress.append({
            "data": row[0],
            "peso": row[1],
            "circunferencia_abdomen": row[2],
            "observacoes": row[3]
        })
    return progress

def save_water_log(user_id, water_data):
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO water_log (user_id, data, ml)
        VALUES (?, ?, ?)
    """, (user_id, water_data["data"], water_data["ml"]))
    conn.commit()
    conn.close()

def load_water_log(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT data, ml 
        FROM water_log 
        WHERE user_id = ? 
        ORDER BY data DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    water_log = []
    for row in rows:
        water_log.append({
            "data": row[0],
            "ml": row[1]
        })
    return water_log

def save_sleep_log(user_id, sleep_data):
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO sleep_log (user_id, data, horas)
        VALUES (?, ?, ?)
    """, (user_id, sleep_data["data"], sleep_data["horas"]))
    conn.commit()
    conn.close()

def load_sleep_log(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT data, horas 
        FROM sleep_log 
        WHERE user_id = ? 
        ORDER BY data DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    sleep_log = []
    for row in rows:
        sleep_log.append({
            "data": row[0],
            "horas": row[1]
        })
    return sleep_log

# --- EMBELEZAMENTO E CSS ---
st.set_page_config(
    page_title="FitBuddy - Seu Companheiro Fitness",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* Fundo cinza escuro */
.stApp {
    background: #232323;
}

/* Cabeçalho principal */
.main-header {
    font-size: 2.5rem;
    color: #ff9800;
    text-align: center;
    margin-bottom: 2rem;
    font-weight: 900;
    letter-spacing: 1px;
    text-shadow: 1px 2px 8px #111;
}

/* Subcabeçalho */
.sub-header {
    font-size: 1.25rem;
    color: #ff9800;
    margin: 1.2rem 0 0.7rem 0;
    border-left: 4px solid #ff9800;
    padding-left: 10px;
    font-weight: 600;
    background: #333;
    border-radius: 4px;
}

/* Cartões de métricas */
.metric-card {
    display: flex;
    flex-direction: column;
    background: #181818;
    padding: 20px 16px 14px 16px;
    border-radius: 12px;
    color: #fff;
    margin: 10px 0;
    box-shadow: 0 2px 8px rgba(30,30,30,0.13);
    text-align: center;
    font-weight: 600;
    border: 1px solid #444;
    transition: box-shadow 0.2s, border 0.2s;
    border-left: 5px solid #ff9800;
    
}

.metric-card:hover {
    box-shadow: 0 4px 16px rgba(255,152,0,0.13);
    border-left: 5px solid #ffa726;
}

/* Cartões de treino e alimentação */
.workout-card, .food-card {
    background: #232323;
    border-radius: 8px;
    padding: 13px;
    margin: 10px 0;
    border-left: 4px solid #ff9800;
    box-shadow: 0 1px 4px rgba(30,30,30,0.10);
    color: #fff;
}
.food-card { border-left: 4px solid #ffa726; }
.completed {
    background: #2e2e2e;
    border-left: 4px solid #ffb74d;
}

/* Botões */
.stButton button {
    width: 100%;
    border-radius: 7px;
    background: linear-gradient(90deg, #ff9800 0%, #ffa726 100%);
    color: #181818;
    font-weight: bold;
    border: none;
    padding: 0.7em 0;
    font-size: 1.08em;
    box-shadow: 0 1px 4px rgba(255,152,0,0.10);
    transition: background 0.2s, transform 0.2s;
}
.stButton button:hover {
    background: linear-gradient(90deg, #ffa726 0%, #ff9800 100%);
    color: #fff;
    transform: scale(1.01);
}

/* Divisor de seção */
.section-divider {
    height: 2px;
    background: linear-gradient(90deg, transparent, #ff9800, transparent);
    margin: 1.2rem 0;
    border-radius: 2px;
}

/* Sidebar customizado */
[data-testid="stSidebar"] {
    background: #181818;
    color: #fff;
}
[data-testid="stSidebar"] .stImage img {
    border-radius: 10px;
    margin-bottom: 1em;
    box-shadow: 0 1px 4px rgba(255,152,0,0.13);
}
[data-testid="stSidebar"] .stTitle {
    color: #ff9800;
    font-weight: 900;
    letter-spacing: 1px;
    
}
[data-testid="stSidebar"] .stMarkdown {
    color: #ffa726;
    font-weight: 600;
}

/* Formulários de login */
.login-container {
    background: #1e1e1e;
    padding: 2rem;
    border-radius: 12px;
    border: 1px solid #444;
    margin: 2rem auto;
    max-width: 500px;
}
.login-header {
    text-align: center;
    color: #ff9800;
    margin-bottom: 1.5rem;
    font-size: 1.8rem;
}
</style>
""", unsafe_allow_html=True)

class FitnessHub:
    def __init__(self):
        create_tables()  # Cria as tabelas no banco de dados
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
            "just_logged_in": False
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def load_food_database(self):
        self.food_db = {
            "Proteínas": {
                "Peito de Frango (100g)": {"calorias": 165, "proteina": 31, "carboidrato": 0, "gordura": 3.6},
                "Ovo (1 unidade)": {"calorias": 78, "proteina": 6, "carboidrato": 0.6, "gordura": 5},
                "Salmão (100g)": {"calorias": 208, "proteina": 20, "carboidrato": 0, "gordura": 13},
                "Carne Bovina (100g)": {"calorias": 250, "proteina": 26, "carboidrato": 0, "gordura": 15},
                "Whey Protein (30g)": {"calorias": 120, "proteina": 24, "carboidrato": 3, "gordura": 1},
                "Iogurte Grego (100g)": {"calorias": 59, "proteina": 10, "carboidrato": 3.6, "gordura": 0.4},
                "Queijo Cottage (100g)": {"calorias": 98, "proteina": 11, "carboidrato": 3.4, "gordura": 4.3},
            },
            "Carboidratos": {
                "Arroz Integral (100g cozido)": {"calorias": 112, "proteina": 2.6, "carboidrato": 23, "gordura": 0.9},
                "Batata Doce (100g)": {"calorias": 86, "proteina": 1.6, "carboidrato": 20, "gordura": 0.1},
                "Aveia (100g)": {"calorias": 389, "proteina": 16.9, "carboidrato": 66, "gordura": 6.9},
                "Pão Integral (1 fatia)": {"calorias": 69, "proteina": 3.5, "carboidrato": 11, "gordura": 0.9},
                "Massa Integral (100g cozido)": {"calorias": 124, "proteina": 5, "carboidrato": 25, "gordura": 1},
                "Quinoa (100g cozido)": {"calorias": 120, "proteina": 4.4, "carboidrato": 21, "gordura": 1.9},
                "Banana (1 unidade)": {"calorias": 105, "proteina": 1.3, "carboidrato": 27, "gordura": 0.4},
            },
            "Gorduras": {
                "Abacate (100g)": {"calorias": 160, "proteina": 2, "carboidrato": 9, "gordura": 15},
                "Azeite de Oliva (1 colher)": {"calorias": 119, "proteina": 0, "carboidrato": 0, "gordura": 14},
                "Castanhas (30g)": {"calorias": 180, "proteina": 5, "carboidrato": 6, "gordura": 16},
                "Manteiga de Amendoim (1 colher)": {"calorias": 96, "proteina": 4, "carboidrato": 3, "gordura": 8},
                "Semente de Chia (20g)": {"calorias": 97, "proteina": 3, "carboidrato": 8, "gordura": 6},
                "Coco (100g)": {"calorias": 354, "proteina": 3.3, "carboidrato": 15, "gordura": 33},
                "Azeitonas (100g)": {"calorias": 115, "proteina": 0.8, "carboidrato": 6, "gordura": 11},
            },
            "Vegetais": {
                "Brócolis (100g)": {"calorias": 34, "proteina": 2.8, "carboidrato": 7, "gordura": 0.4},
                "Espinafre (100g)": {"calorias": 23, "proteina": 2.9, "carboidrato": 3.6, "gordura": 0.4},
                "Cenoura (100g)": {"calorias": 41, "proteina": 0.9, "carboidrato": 10, "gordura": 0.2},
                "Alface (100g)": {"calorias": 15, "proteina": 1.4, "carboidrato": 2.9, "gordura": 0.2},
                "Tomate (100g)": {"calorias": 18, "proteina": 0.9, "carboidrato": 3.9, "gordura": 0.2},
                "Pepino (100g)": {"calorias": 15, "proteina": 0.7, "carboidrato": 3.6, "gordura": 0.1},
                "Pimentão (100g)": {"calorias": 31, "proteina": 1, "carboidrato": 6, "gordura": 0.3},
            }
        }

    def load_motivational_phrases(self):
        self.motivational_phrases = [
            "Acredite em você! Cada passo conta.",
            "Você é mais forte do que imagina.",
            "Disciplina é o caminho para o sucesso.",
            "Não desista, o progresso é construído dia após dia.",
            "Seu esforço de hoje é o resultado de amanhã.",
            "A jornada pode ser difícil, mas a vitória é certa para quem persiste.",
            "Seja constante, não perfeito.",
            "O impossível é apenas o possível que nunca foi tentado."
        ]

    def load_jokes(self):
        self.jokes = [
            "Por que o computador foi ao médico? Porque estava com um vírus!",
            "O que o zero disse para o oito? Belo cinto!",
            "Por que o livro foi ao hospital? Porque ele tinha muitas páginas amarelas.",
            "O que o tomate foi fazer no banco? Tirar extrato."
        ]

    def login_section(self):
        st.markdown('<div class="login-header">💪 FitBuddy</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align: center; margin-bottom: 2rem; color: #ffa726;">Seu Companheiro Fitness<br><br>NÃO UTILIZE DADOS REAIS</div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Login", "Registrar"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("EMAIL FALSO")
                password = st.text_input("SENHA FALSA", type="password")
                submit = st.form_submit_button("Entrar")
                
                if submit:
                    user_id = login_user(email, password)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.user_email = email
                        st.session_state.just_logged_in = True
                        self.load_user_data()
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Email ou senha não cadastrados ou incorretos")
        
        with tab2:
            with st.form("register_form"):
                email = st.text_input("EMAIL FALSO")
                password = st.text_input("SENHA FALSA", type="password")
                confirm_password = st.text_input("CONFIRMAR SENHA FALSA", type="password")
                submit = st.form_submit_button("Criar Conta")
                
                if submit:
                    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                        st.error("Por favor, insira um email com '@gmail.com'")
                    elif len(password) < 3:
                        st.error("A senha deve ter pelo menos 3 caracteres")
                    elif password != confirm_password:
                        st.error("As senhas não coincidem")
                    else:
                        try:
                            add_user(email, password)
                            st.success("Conta criada com sucesso! Faça login para continuar.")
                        except sqlite3.IntegrityError:
                            st.error("Este email já está em uso")

    def load_user_data(self):
        # Carrega os dados do usuário do banco de dados
        if st.session_state.user_id:
            # Carrega perfil do usuário
            st.session_state.user_data = load_user_profile(st.session_state.user_id)
            
            # Carrega planos de treino
            st.session_state.workout_plans = load_workout_plans(st.session_state.user_id)
            
            # Carrega histórico de treinos
            st.session_state.workout_history = load_workout_history(st.session_state.user_id)
            
            # Carrega registro alimentar
            st.session_state.food_log = load_food_log(st.session_state.user_id)
            
            # Carrega dados de progresso
            st.session_state.progress_data = load_progress_data(st.session_state.user_id)
            
            # Carrega registro de água
            st.session_state.water_log = load_water_log(st.session_state.user_id)
            
            # Carrega registro de sono
            st.session_state.sleep_log = load_sleep_log(st.session_state.user_id)

    def logout(self):
        # Limpa todos os dados da sessão
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        self.initialize_session_state()
        st.rerun()

    def motivational_card(self):
        st.markdown('<div class="sub-header">💡 Motivação do Dia</div>', unsafe_allow_html=True)
        st.info(f"**{random.choice(self.motivational_phrases)}**")

    def joke_card(self):
        st.markdown('<div class="sub-header">😂 Sorria!</div>', unsafe_allow_html=True)
        st.success(f"_{random.choice(self.jokes)}_")

    def water_tracker(self, meta_agua=None):
        st.markdown('<div class="sub-header">💧 Controle de Água</div>', unsafe_allow_html=True)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Filtra apenas os registros de água de hoje
        water_today = [w for w in st.session_state.water_log if w["data"] == today]
        total_ml = sum([w["ml"] for w in water_today])
        
        st.write(f"Total consumido hoje: **{total_ml} ml**")
        ml = st.number_input("Adicionar água (ml)", min_value=50, max_value=2000, step=50, value=250)
        
        if st.button("Registrar Água"):
            water_data = {"data": today, "ml": ml}
            save_water_log(st.session_state.user_id, water_data)
            st.session_state.water_log.append(water_data)
            st.success(f"{ml} ml adicionados!")
            st.rerun()
        
        # Sincroniza meta de água
        meta = meta_agua if meta_agua else 2000
        st.progress(min(total_ml/meta, 1.0), text=f"Meta diária: {meta}ml")

    def sleep_tracker(self):
        st.markdown('<div class="sub-header">😴 Controle de Sono</div>', unsafe_allow_html=True)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Filtra apenas os registros de sono de hoje
        sleep_today = [s for s in st.session_state.sleep_log if s["data"] == today]
        
        horas = st.number_input("Horas de sono na última noite", min_value=0.0, max_value=24.0, step=0.5, value=8.0)
        
        if st.button("Registrar Sono"):
            sleep_data = {"data": today, "horas": horas}
            save_sleep_log(st.session_state.user_id, sleep_data)
            st.session_state.sleep_log.append(sleep_data)
            st.success(f"{horas} horas registradas!")
            st.rerun()
        
        if sleep_today:
            st.write(f"Hoje: {sleep_today[-1]['horas']} horas")
        else:
            st.info("Registre suas horas de sono para acompanhar seu descanso.")

    def calculate_bmi(self, weight, height):
        height_m = height / 100
        return weight / (height_m ** 2)

    def calculate_bmr(self, weight, height, age, gender):
        if gender == "Masculino":
            return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        else:
            return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

    def calculate_tdee(self, bmr, activity_level):
        multipliers = {
            "Sedentário": 1.2,
            "Levemente ativo": 1.375,
            "Moderadamente ativo": 1.55,
            "Muito ativo": 1.725,
            "Extremamente ativo": 1.9
        }
        return bmr * multipliers.get(activity_level, 1.2)

    def calculate_water_goal(self, weight, activity_level):
        # 35ml por kg + ajuste por atividade
        base = weight * 35  # ml
        activity_bonus = {
            "Sedentário": 0,
            "Levemente ativo": 250,
            "Moderadamente ativo": 500,
            "Muito ativo": 750,
            "Extremamente ativo": 1000
        }
        return int(base + activity_bonus.get(activity_level, 0))

    def calculate_calorie_goal(self, tdee, objetivo):
        # Bulking: +15%, Cutting: -15%, Manutenção: igual
        if objetivo == "Ganho de massa":
            return int(tdee * 1.15)
        elif objetivo == "Perda de peso":
            return int(tdee * 0.85)
        elif objetivo == "Definição muscular":
            return int(tdee * 0.90)
        else:
            return int(tdee)

    def calculate_min_training_time(self, objetivo, nivel_atividade):
        # Recomendações gerais (em minutos/dia)
        base = 30
        if objetivo == "Ganho de massa":
            base = 45
        elif objetivo == "Perda de peso":
            base = 40
        elif objetivo == "Definição muscular":
            base = 50
        # Ajuste por nível de atividade
        bonus = {
            "Sedentário": 0,
            "Levemente ativo": 5,
            "Moderadamente ativo": 10,
            "Muito ativo": 15,
            "Extremamente ativo": 20
        }
        return base + bonus.get(nivel_atividade, 0)

    def user_registration(self):
        st.markdown('<div class="sub-header">👤 Cadastro do Usuário</div>', unsafe_allow_html=True)
        if st.session_state.user_data:
            st.info(f"Usuário cadastrado: {st.session_state.user_data['nome']}")
            if st.button("🗑️ Excluir Conta", type="primary"):
                delete_user_profile(st.session_state.user_id)
                st.session_state.user_data = None
                st.success("Dados do perfil excluídos com sucesso!")
                st.rerun()
            return

        with st.form("user_registration"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome Completo*")
                idade = st.number_input("Idade*", min_value=10, max_value=100, step=1)
                genero = st.selectbox("Gênero*", ["Masculino", "Feminino", "Outro"])
                altura = st.number_input("Altura (cm)*", min_value=100, max_value=250, step=1)
            with col2:
                peso = st.number_input("Peso (kg)*", min_value=20.0, max_value=300.0, step=0.1)
                objetivo = st.selectbox("Objetivo*", 
                    ["Perda de peso", "Ganho de massa", "Manutenção", "Definição muscular"])
                nivel_atividade = st.selectbox("Nível de Atividade*", 
                    ["Sedentário", "Levemente ativo", "Moderadamente ativo", "Muito ativo", "Extremamente ativo"])
                meta_peso = st.number_input("Meta de Peso (kg)", min_value=20.0, max_value=300.0, step=0.1)
            submit = st.form_submit_button("Salvar Perfil")
            if submit:
                if all([nome, idade, genero, altura, peso, objetivo, nivel_atividade]):
                    bmi = self.calculate_bmi(peso, altura)
                    bmr = self.calculate_bmr(peso, altura, idade, genero)
                    tdee = self.calculate_tdee(bmr, nivel_atividade)
                    user_data = {
                        "nome": nome,
                        "idade": idade,
                        "genero": genero,
                        "altura": altura,
                        "peso": peso,
                        "objetivo": objetivo,
                        "nivel_atividade": nivel_atividade,
                        "meta_peso": meta_peso,
                        "bmi": bmi,
                        "bmr": bmr,
                        "tdee": tdee,
                        "data_cadastro": datetime.now().strftime("%Y-%m-%d")
                    }
                    save_user_profile(st.session_state.user_id, user_data)
                    st.session_state.user_data = user_data
                    st.success("Perfil salvo com sucesso!")
                    st.rerun()
                else:
                    st.error("Por favor, preencha todos os campos obrigatórios (*)")

    def create_workout_plan(self):
        st.markdown('<div class="sub-header">🏋️ Criar Plano de Treino</div>', unsafe_allow_html=True)
        if not st.session_state.user_data:
            st.warning("Complete seu cadastro primeiro!")
            return
        with st.form("workout_plan"):
            nome_plano = st.text_input("Nome do Plano*")
            dias_semana = st.multiselect("Dias da Semana*",
                ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"])
            st.markdown("**Exercícios por Grupo Muscular**")
            grupos_musculares = {
                "Peito": ["Supino reto", "Supino inclinado", "Crucifixo", "Flexão", "Crossover"],
                "Costas": ["Puxada frontal", "Remada curvada", "Pull-down", "Barra fixa", "Pulley"],
                "Pernas": ["Agachamento", "Leg press", "Cadeira extensora", "Stiff", "Afundo", "Cadeira flexora"],
                "Ombros": ["Desenvolvimento", "Elevação lateral", "Remada alta", "Face pull", "Elevação frontal"],
                "Braços": ["Rosca direta", "Tríceps testa", "Rosca martelo", "Tríceps pulley", "Rosca scott"],
                "Abdômen": ["Abdominal crunch", "Prancha", "Elevação de pernas", "Russian twist", "Abdominal bicicleta"]
            }
            plano_treino = {}
            for grupo, exercicios in grupos_musculares.items():
                if st.checkbox(f"{grupo}"):
                    exercicio_selecionado = st.selectbox(f"Exercício para {grupo}", exercicios, key=f"ex_{grupo}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        series = st.slider(f"Séries para {grupo}", 1, 10, 3, key=f"ser_{grupo}")
                    with col2:
                        repeticoes = st.slider(f"Repetições para {grupo}", 1, 20, 12, key=f"rep_{grupo}")
                    with col3:
                        descanso = st.slider(f"Descanso (segundos)", 30, 180, 60, key=f"desc_{grupo}")
                    plano_treino[grupo] = {
                        "exercicio": exercicio_selecionado,
                        "series": series,
                        "repeticoes": repeticoes,
                        "descanso": descanso
                    }
            submit = st.form_submit_button("Salvar Plano de Treino")
            if submit and nome_plano and dias_semana and plano_treino:
                plan_data = {
                    "dias_semana": dias_semana,
                    "exercicios": plano_treino,
                    "data_criacao": datetime.now().strftime("%Y-%m-%d")
                }
                save_workout_plan(st.session_state.user_id, nome_plano, plan_data)
                st.session_state.workout_plans[nome_plano] = plan_data
                st.success(f"Plano '{nome_plano}' salvo com sucesso!")

    def start_workout(self):
        if not st.session_state.workout_plans:
            st.warning("Nenhum plano de treino disponível. Crie um plano primeiro!")
            return
        st.markdown('<div class="sub-header">🚀 Iniciar Treino</div>', unsafe_allow_html=True)
        planos = list(st.session_state.workout_plans.keys())
        plano_selecionado = st.selectbox("Selecione o plano de treino", planos)
        if st.button("Iniciar Treino"):
            st.session_state.active_workout = {
                "plano": plano_selecionado,
                "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "exercicios_completos": [],
                "status": "em_andamento"
            }
            st.success(f"Treino '{plano_selecionado}' iniciado!")
            st.rerun()

    def workout_tracker(self):
        if not st.session_state.active_workout:
            return
        st.markdown('<div class="sub-header">⏱️ Treino em Andamento</div>', unsafe_allow_html=True)
        plano_nome = st.session_state.active_workout["plano"]
        plano = st.session_state.workout_plans[plano_nome]
        st.info(f"Plano: {plano_nome} | Iniciado: {st.session_state.active_workout['inicio']}")
        if 'start_time' not in st.session_state:
            st.session_state.start_time = time.time()
        elapsed_time = time.time() - st.session_state.start_time
        mins, secs = divmod(int(elapsed_time), 60)
        st.write(f"⏰ Tempo decorrido: {mins:02d}:{secs:02d}")
        for i, (grupo, detalhes) in enumerate(plano["exercicios"].items()):
            completed = grupo in st.session_state.active_workout["exercicios_completos"]
            card_class = "workout-card completed" if completed else "workout-card"
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            st.markdown(f"**{grupo}**: {detalhes['exercicio']}")
            st.markdown(f"Séries: {detalhes['series']} × {detalhes['repeticoes']} reps | Descanso: {detalhes['descanso']}s")
            if not completed:
                if st.button(f"Completar {grupo}", key=f"complete_{i}"):
                    st.session_state.active_workout["exercicios_completos"].append(grupo)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        todos_completos = len(st.session_state.active_workout["exercicios_completos"]) == len(plano["exercicios"])
        if st.button("Finalizar Treino", disabled=not todos_completos):
            fim = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            duracao = time.time() - st.session_state.start_time
            registro = {
                "plano": plano_nome,
                "data": datetime.now().strftime("%Y-%m-%d"),
                "inicio": st.session_state.active_workout["inicio"],
                "fim": fim,
                "duracao": duracao,
                "exercicios_completos": st.session_state.active_workout["exercicios_completos"]
            }
            save_workout_history(st.session_state.user_id, registro)
            st.session_state.workout_history.append(registro)
            st.session_state.active_workout = None
            st.session_state.start_time = None
            st.success("Treino finalizado e salvo no histórico!")
            st.rerun()

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
                unidade = st.selectbox("Unidade", ["g", "unidades", "colheres", "xícaras"])
            if st.button("Adicionar à Refeição"):
                alimento_info = self.food_db[categoria][alimento].copy()
                alimento_info["nome"] = alimento
                alimento_info["categoria"] = categoria
                alimento_info["quantidade"] = quantidade
                alimento_info["unidade"] = unidade
                st.session_state.today_food.append(alimento_info)
                st.success(f"{alimento} adicionado!")
        with col2:
            st.markdown("**Sua Refeição de Hoje**")
            if st.session_state.today_food:
                total_calorias = 0
                total_proteina = 0
                total_carboidrato = 0
                total_gordura = 0
                for alimento in st.session_state.today_food:
                    fator = alimento["quantidade"] / 100 if alimento["unidade"] == "g" else alimento["quantidade"]
                    calorias = alimento["calorias"] * fator
                    proteina = alimento["proteina"] * fator
                    carboidrato = alimento["carboidrato"] * fator
                    gordura = alimento["gordura"] * fator
                    total_calorias += calorias
                    total_proteina += proteina
                    total_carboidrato += carboidrato
                    total_gordura += gordura
                    st.markdown(f"""
                    <div class="food-card">
                        <b>{alimento['nome']}</b> - {alimento['quantidade']}{alimento['unidade']}<br>
                        Calorias: {calorias:.1f} | Proteína: {proteina:.1f}g | Carbs: {carboidrato:.1f}g | Gordura: {gordura:.1f}g
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("---")
                st.markdown(f"""
                **Totais:**<br>
                🔥 Calorias: {total_calorias:.1f}kcal<br>
                💪 Proteína: {total_proteina:.1f}g<br>
                🍞 Carboidratos: {total_carboidrato:.1f}g<br>
                🥑 Gorduras: {total_gordura:.1f}g
                """)
                if st.button("Salvar Refeição do Dia"):
                    refeicao = {
                        "data": datetime.now().strftime("%Y-%m-%d"),
                        "alimentos": st.session_state.today_food.copy(),
                        "totais": {
                            "calorias": total_calorias,
                            "proteina": total_proteina,
                            "carboidrato": total_carboidrato,
                            "gordura": total_gordura
                        }
                    }
                    save_food_log(st.session_state.user_id, refeicao)
                    st.session_state.food_log.append(refeicao)
                    st.session_state.today_food = []
                    st.success("Refeição salva no histórico!")
            else:
                st.info("Nenhum alimento adicionado hoje.")

    def nutrition_dashboard(self):
        st.markdown('<div class="sub-header">📊 Dashboard Nutricional</div>', unsafe_allow_html=True)
        if not st.session_state.food_log:
            st.info("Nenhum registro alimentar encontrado. Adicione alimentos para ver estatísticas.")
            return
        dias = []
        calorias_dia = []
        proteinas_dia = []
        carbs_dia = []
        gorduras_dia = []
        for registro in st.session_state.food_log[-7:]:
            dias.append(registro["data"])
            calorias_dia.append(registro["totais"]["calorias"])
            proteinas_dia.append(registro["totais"]["proteina"])
            carbs_dia.append(registro["totais"]["carboidrato"])
            gorduras_dia.append(registro["totais"]["gordura"])
        fig_cal = go.Figure()
        fig_cal.add_trace(go.Scatter(x=dias, y=calorias_dia, mode='lines+markers', name='Calorias',
                                    line=dict(color='#FF6B6B', width=3)))
        if st.session_state.user_data:
            tdee = st.session_state.user_data["tdee"]
            fig_cal.add_hline(y=tdee, line_dash="dash", line_color="green", 
                             annotation_text="Meta Calórica Diária")
        fig_cal.update_layout(title="Consumo Calórico Diário", xaxis_title="Data", yaxis_title="Calorias")
        st.plotly_chart(fig_cal, use_container_width=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            fig_prot = go.Figure(go.Indicator(
                mode="gauge+number",
                value=np.mean(proteinas_dia) if proteinas_dia else 0,
                title={'text': "Proteína Média (g)"},
                gauge={'axis': {'range': [0, 200]}}
            ))
            st.plotly_chart(fig_prot, use_container_width=True)
        with col2:
            fig_carb = go.Figure(go.Indicator(
                mode="gauge+number",
                value=np.mean(carbs_dia) if carbs_dia else 0,
                title={'text': "Carbs Média (g)"},
                gauge={'axis': {'range': [0, 400]}}
            ))
            st.plotly_chart(fig_carb, use_container_width=True)
        with col3:
            fig_fat = go.Figure(go.Indicator(
                mode="gauge+number",
                value=np.mean(gorduras_dia) if gorduras_dia else 0,
                title={'text': "Gorduras Média (g)"},
                gauge={'axis': {'range': [0, 100]}}
            ))
            st.plotly_chart(fig_fat, use_container_width=True)

    def workout_history_view(self):
        st.markdown('<div class="sub-header">📋 Histórico de Treinos</div>', unsafe_allow_html=True)
        if not st.session_state.workout_history:
            st.info("Nenhum treino registrado ainda. Inicie um treino para ver o histórico.")
            return
        for treino in reversed(st.session_state.workout_history):
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
            peso = st.number_input("Peso (kg)", min_value=20.0, max_value=300.0, step=0.1, 
                                  value=st.session_state.user_data["peso"])
            circunferencia_abdomen = st.number_input("Circunferência Abdômen (cm)", min_value=50, max_value=200, step=1)
            observacoes = st.text_area("Observações")
            submit = st.form_submit_button("Registrar Progresso")
            if submit:
                registro = {
                    "data": data.strftime("%Y-%m-%d"),
                    "peso": peso,
                    "circunferencia_abdomen": circunferencia_abdomen,
                    "observacoes": observacoes
                }
                save_progress_data(st.session_state.user_id, registro)
                st.session_state.progress_data.append(registro)
                st.session_state.user_data["peso"] = peso
                st.success("Progresso registrado com sucesso!")
        if st.session_state.progress_data:
            df = pd.DataFrame(st.session_state.progress_data)
            df['data'] = pd.to_datetime(df['data'])
            df = df.sort_values('data')
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['data'], y=df['peso'], 
                                   mode='lines+markers', name='Peso (kg)',
                                   line=dict(color='#FF6B6B', width=3)))
            if st.session_state.user_data.get("meta_peso"):
                fig.add_hline(y=st.session_state.user_data["meta_peso"], 
                             line_dash="dash", line_color="green", 
                             annotation_text="Meta de Peso")
            fig.update_layout(
                title="Evolução do Peso",
                xaxis_title="Data",
                yaxis_title="Peso (kg)",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

    def dashboard(self):
        st.markdown('<h1 class="main-header">💪 FitBuddy</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; font-size: 1.2rem;">Seu Companheiro Fitness Completo</p>', unsafe_allow_html=True)
        if not st.session_state.user_data:
            st.info("👋 Bem-vindo! Complete seu cadastro para personalizar sua experiência.")
            return
        user = st.session_state.user_data

        # --- NOVAS METAS ---
        meta_agua = self.calculate_water_goal(user['peso'], user['nivel_atividade'])
        meta_calorias = self.calculate_calorie_goal(user['tdee'], user['objetivo'])
        meta_treino = self.calculate_min_training_time(user['objetivo'], user['nivel_atividade'])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📊 IMC</h3>
                <h2>{user['bmi']:.1f}</h2>
                <p>{self.classify_bmi(user['bmi'])}</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🔥 Calorias</h3>
                <h2>{meta_calorias} kcal</h2>
                <p>Meta diária</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>💧 Água</h3>
                <h2>{meta_agua} ml</h2>
                <p>Meta diária</p>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>⏱️ Duração do Treino</h3>
                <h2>{meta_treino} min</h2>
                <p>Por sessão</p>
            </div>
            """, unsafe_allow_html=True)
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
                for treino in list(reversed(st.session_state.workout_history))[:3]:
                    data = treino['data']
                    plano = treino['plano']
                    duracao = int(treino['duracao'] // 60)
                    st.write(f"**{data}**: {plano} ({duracao} min)")
            else:
                st.info("Nenhum treino registrado")
        with col2:
            st.subheader("🍽️ Refeições Recentes")
            if st.session_state.food_log:
                for refeicao in list(reversed(st.session_state.food_log))[:3]:
                    data = refeicao['data']
                    calorias = refeicao['totais']['calorias']
                    st.write(f"**{data}**: {calorias:.0f} kcal")
            else:
                st.info("Nenhuma refeição registrada")
        st.markdown("---")
        self.motivational_card()
        self.joke_card()
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            self.water_tracker(meta_agua=meta_agua)
        with col2:
            self.sleep_tracker()

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
        # Verifica se o usuário está logado
        if not st.session_state.user_id:
            self.login_section()
            return

        # Menu lateral normal após login
        if "selected" not in st.session_state:
            st.session_state.selected = "Dashboard"
            
        with st.sidebar:
            st.title("💪 FitBuddy")
            st.markdown(f"**Usuário:** {st.session_state.user_email}")
            st.markdown("---")
            
            menu_options = {
                "Dashboard": "📊",
                "Cadastro": "👤",
                "Criar Plano de Treino": "🏋️",
                "Iniciar Treino": "🚀",
                "Registrar Refeição": "🍽️",
                "Dashboard Nutricional": "📈",
                "Histórico de Treinos": "📋",
                "Acompanhamento": "🎯"
            }
            
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

        # Carrega os dados do usuário se acabou de fazer login
        if st.session_state.just_logged_in:
            self.load_user_data()
            st.session_state.just_logged_in = False

        # Renderiza a página selecionada
        if st.session_state.selected == "Dashboard":
            self.dashboard()
        elif st.session_state.selected == "Cadastro":
            self.user_registration()
        elif st.session_state.selected == "Criar Plano de Treino":
            self.create_workout_plan()
        elif st.session_state.selected == "Iniciar Treino":
            self.start_workout()
            self.workout_tracker()
        elif st.session_state.selected == "Registrar Refeição":
            self.food_logger()
        elif st.session_state.selected == "Dashboard Nutricional":
            self.nutrition_dashboard()
        elif st.session_state.selected == "Histórico de Treinos":
            self.workout_history_view()
        elif st.session_state.selected == "Acompanhamento":
            self.progress_tracking()

if __name__ == "__main__":
    app = FitnessHub()
    app.run()