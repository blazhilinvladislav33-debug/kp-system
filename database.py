import streamlit as st
import gspread

# --- НОВИЙ БЕЗПЕЧНИЙ СПОСІБ ПІДКЛЮЧЕННЯ (БЕЗ ФАЙЛУ CREDS.JSON) ---
# Програма бере словник із секретними ключами прямо з налаштувань сервера Streamlit Cloud
credentials_dict = dict(st.secrets["gcp_service_account"])
client = gspread.service_account_from_dict(credentials_dict)

SHEET_NAME = "Система Управління КП"
sheet = client.open(SHEET_NAME)

def get_all_users():
    try: return sheet.worksheet("users").get_all_records()
    except: return []

def add_new_user(username, password, role, unit_name):
    sheet.worksheet("users").append_row([username, password, role, unit_name])

def add_new_position(pos_name, coordinates, created_by):
    sheet.worksheet("positions").append_row([pos_name, coordinates, created_by])