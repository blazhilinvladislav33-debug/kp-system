import streamlit as st
import database as db

st.set_page_config(page_title="Система Керування", layout="wide")

# Ініціалізація сесії
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.username = None

def check_login(username, password):
    try:
        users = db.get_all_users()
        if not users:
            st.error("База даних користувачів порожня або недоступна!")
            return None
            
        for user in users:
            # Перевіряємо наявність потрібних стовпчиків у таблиці
            if 'username' not in user or 'password' not in user or 'role' not in user:
                st.error("Помилка структури таблиці! Перевірте, що стовпчики названі точно: username, password, role")
                return None
                
            if str(user['username']).strip() == username.strip() and str(user['password']).strip() == password.strip():
                return user['role']
        return None
    except Exception as e:
        st.error(f"Критична помилка при зчитуванні бази даних: {e}")
        return None

# ЛОГІКА АВТОРИЗАЦІЇ
if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center;'>🔐 Вхід у систему управління</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Логін")
        password = st.text_input("Пароль", type="password")
        if st.button("Увійти", use_container_width=True):
            with st.spinner("Перевірка даних..."):
                role = check_login(username, password)
            if role:
                st.session_state.authenticated = True
                st.session_state.role = role
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Невірний логін або пароль! Або перевірте структуру таблиці.")
else:
    # Динамічний імпорт, щоб уникнути збоїв при запуску
    try:
        if st.session_state.role == "command_post":
            from command_post import cp_dash
            cp_dash.show_page()
        elif st.session_state.role == "unit":
            from units import unit_dash
            unit_dash.show_page()
        else:
            st.error(f"Невідома роль користувача: {st.session_state.role}")
    except Exception as e:
        st.error(f"Помилка завантаження сторінки інтерфейсу: {e}")
        if st.button("Вийти"):
            st.session_state.authenticated = False
            st.rerun()