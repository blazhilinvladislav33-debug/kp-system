import streamlit as st
import database as db
from datetime import datetime

# --- КЕШУВАННЯ ДЛЯ ЗАХИСТУ ВІД GOOGLE RATE LIMITS ---
@st.cache_data(ttl=10)
def load_sheet_data(sheet_name):
    try:
        return db.sheet.worksheet(sheet_name).get_all_records()
    except:
        return []

def show_page():
    # --- ІНІЦІАЛІЗАЦІЯ СЕСІЇ ---
    if "username" not in st.session_state:
        st.session_state.username = "Екіпаж"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = True
    if "notified_deliveries" not in st.session_state:
        st.session_state.notified_deliveries = []

    # --- 🛑 АГРЕСИВНИЙ CSS (ПОВНЕ БЛОКУВАННЯ ЗАТУХАННЯ ТА СІРОГО ЕКРАНУ) 🛑 ---
    st.markdown(
        """
        <style>
        /* Максимально жорстке блокування сірого екрану під час фонового оновлення */
        html[data-test-script-state="running"] [data-testid="stAppViewContainer"],
        html[data-test-script-state="running"] [data-testid="stSidebar"],
        html[data-test-script-state="running"] .stApp,
        .stApp, 
        .stApp > header,
        .main, 
        .block-container,
        [data-testid="stAppViewContainer"], 
        [data-testid="stAppViewBlockContainer"], 
        [data-testid="stSidebar"],
        [data-testid="stSidebarContent"] {
            opacity: 1 !important;
            filter: blur(0px) brightness(1) !important;
            -webkit-filter: blur(0px) brightness(1) !important;
            transition: none !important;
            pointer-events: auto !important;
        }
        
        /* Скасування затухання під час "Running" */
        div[data-styled-state="running"] {
            opacity: 1 !important;
            filter: none !important;
        }

        /* Повне приховування крутилки "Running..." у верхньому правому куті */
        [data-testid="stStatusWidget"], #stStatusWidget {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
        }
        
        /* Приховування верхньої системної плашки */
        header[data-testid="stHeader"] {
            display: none !important;
        }

        /* --- Стилі компактності для телефонів --- */
        [data-testid="stAppViewContainer"] .main h2 {
            font-size: clamp(1.1rem, 2.4vw, 1.35rem) !important;
            font-weight: 700 !important;
            text-align: center !important;
            margin-top: 0.6rem !important;
            margin-bottom: 0.5rem !important;
        }
        [data-testid="stAppViewContainer"] .main h3, 
        [data-testid="stAppViewContainer"] .main h4 {
            font-size: clamp(0.95rem, 2.0vw, 1.15rem) !important;
            font-weight: 600 !important;
            margin-top: 0.5rem !important;
            margin-bottom: 0.3rem !important;
        }
        [data-testid="stAppViewContainer"] .main p, 
        [data-testid="stAppViewContainer"] .main span, 
        [data-testid="stAppViewContainer"] .main label, 
        [data-testid="stAppViewContainer"] .main li {
            font-size: 13px !important;
            line-height: 1.35 !important;
        }
        [data-testid="stAppViewContainer"] .main code {
            font-size: 12px !important;
            padding: 1px 4px !important;
        }
        div[data-testid="element-container"] div[style*="border"] {
            padding: 0.6rem 0.75rem !important;
            margin-bottom: 0.3rem !important;
            border-radius: 6px !important;
        }
        div[data-testid="stForm"] {
            padding: 0.5rem !important;
            border-radius: 6px !important;
        }
        button[data-baseweb="tab"] {
            padding: 6px 10px !important;
            height: auto !important;
        }
        button[data-baseweb="tab"] div p {
            font-size: 13px !important;
        }
        div[data-testid="stWidgetLabel"] p {
            font-size: 12px !important;
            margin-bottom: 1px !important;
        }
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
            padding-top: 4px !important;
            padding-bottom: 4px !important;
            font-size: 13px !important;
        }
        .stButton button {
            padding: 4px 10px !important;
            font-size: 13px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- 1. МЕНЮ БУТЕРБРОД ДЛЯ КОРИСТУВАЧА (Sidebar) ---
    with st.sidebar:
        st.markdown("### 📋 Меню Екіпажу")
        st.write(f"Користувач: **{st.session_state.username}**")
        st.caption("Роль: Підрозділ (User)")
        st.markdown("---")
        
        # КНОПКА ПРИМУСОВОГО ОНОВЛЕННЯ В МЕНЮ
        if st.button("🔄 Примусове оновлення бази", use_container_width=True, type="secondary"):
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("---")
        
        menu_option = st.radio(
            "Навігація:",
            ["🗺️ Активний маршрут", "📦 Замовлення забезпечення", "🗃️ Закриті путівки (Архів)"]
        )
        st.markdown("---")
        
        if st.button("🚪 Вийти з акаунта", use_container_width=True):
            st.session_state.authenticated = False
            st.cache_data.clear()
            st.rerun()

    # --- БЕЗПЕЧНЕ ЗЧИТУВАННЯ БАЗИ ДАНИХ (ЧЕРЕЗ КЕШ) ---
    all_routes = load_sheet_data("waypoints")
    all_supplies = load_sheet_data("supply")

    try: waypoint_sheet = db.sheet.worksheet("waypoints")
    except: waypoint_sheet = None

    try: supply_sheet = db.sheet.worksheet("supply")
    except: supply_sheet = None

    # --- ЗВУК ПРО ЗМІНУ СТАТУСУ ЗАБЕЗПЕЧЕННЯ (БЕЗ СПАМУ) ---
    current_shipping_ids = [
        str(r.get('id')) for r in all_supplies 
        if str(r.get('unit_username')) == st.session_state.username and str(r.get('status')) == "В дорозі / Доставка"
    ]
    
    new_shipping_notifications = [rid for rid in current_shipping_ids if rid not in st.session_state.notified_deliveries]
    
    if new_shipping_notifications:
        st.components.v1.html(
            """
            <audio autoplay>
                <source src="https://actions.google.com/sounds/v1/notification/ambient_hum_air_conditioner.ogg" type="audio/ogg">
            </audio>
            """,
            height=0,
        )
        st.toast("🚚 Увага! Ваше замовлення забезпечення було відправлене та знаходиться в дорозі!")
        st.session_state.notified_deliveries = st.session_state.notified_deliveries + new_shipping_notifications

    # =========================================================================
    # 🗺️ РЕЖИМ 1: АКТИВНИЙ МАРШРУТ (ЕЛЕКТРОННА ПУТІВКА)
    # =========================================================================
    if menu_option == "🗺️ Активний маршрут" or menu_option == "🗺️ ️Активний маршрут":
        st.markdown("## 🗺️ Електронна Путівка")
        
        my_planned_trips = [r for r in all_routes if str(r.get('assigned_to')) == st.session_state.username and str(r.get('is_closed')) == "PLANNED"]
        for p_trip in my_planned_trips:
            st.warning(f"📅 **ЗАПЛАНОВАНА ПОЇЗДКА НА {p_trip.get('date')}**\n\n**Завдання:** {p_trip.get('route_name')}\n\n📍 Маршрут: `{p_trip.get('point_A')}` ➡️ `{p_trip.get('point_B')}` ➡️ `{p_trip.get('point_C')}`\n\n*Путівка висить у режимі очікування. Щойно адмін КП запустить її в рух, вона автоматично стане активною для відміток.*")
        
        active_route = next((r for r in all_routes if str(r.get('assigned_to')) == st.session_state.username and str(r.get('is_closed')) == "FALSE"), None)
        
        if not active_route:
            if not my_planned_trips:
                st.info("👋 На сьогодні активних чи запланованих путівок для вашого екіпажу немає.")
            return

        row_idx = next((i for i, r in enumerate(all_routes, start=2) if str(r.get('id')) == str(active_route.get('id'))), None)

        st.info(f"📅 **АКТИВНИЙ МАРШРУТ:** {active_route.get('date')} | **Завдання:** {active_route.get('route_name')}")
        st.markdown("### 📍 Прогрес руху маршрутом:")
        
        colA, colB, colC = st.columns(3)
        
        with colA:
            st.markdown(f"**📍 Точка А (Старт):**\n`{active_route.get('point_A')}`")
            if active_route.get('status_A') == "Прибув":
                st.success(f"✅ Прибув\n⏱️ {active_route.get('time_A')}")
            else:
                if st.button("🚗 Прибув в А", key="btn_A", use_container_width=True):
                    if waypoint_sheet and row_idx:
                        now_time = datetime.now().strftime("%H:%M:%S")
                        waypoint_sheet.update_cell(row_idx, 6, "Прибув")
                        waypoint_sheet.update_cell(row_idx, 7, now_time)
                        st.cache_data.clear()
                        st.rerun()

        with colB:
            st.markdown(f"**📍 Точка Б (Проміжна):**\n`{active_route.get('point_B')}`")
            if active_route.get('status_B') == "Прибув":
                st.success(f"✅ Прибув\n⏱️ {active_route.get('time_B')}")
            elif active_route.get('status_A') != "Прибув":
                st.caption("🔒 Доступ закритий")
            else:
                if st.button("🚗 Прибув в Б", key="btn_B", use_container_width=True):
                    if waypoint_sheet and row_idx:
                        now_time = datetime.now().strftime("%H:%M:%S")
                        waypoint_sheet.update_cell(row_idx, 9, "Прибув")
                        waypoint_sheet.update_cell(row_idx, 10, now_time)
                        st.cache_data.clear()
                        st.rerun()

        with colC:
            st.markdown(f"**📍 Точка С (Кінець):**\n`{active_route.get('point_C')}`")
            if active_route.get('status_C') == "Прибув":
                st.success(f"🏁 Фініш\n⏱️ {active_route.get('time_C')}")
            elif active_route.get('status_B') != "Прибув":
                st.caption("🔒 Доступ закритий")
            else:
                if st.button("🏁 Фініш в С", key="btn_C", use_container_width=True):
                    if waypoint_sheet and row_idx:
                        now_time = datetime.now().strftime("%H:%M:%S")
                        waypoint_sheet.update_cell(row_idx, 12, "Прибув")
                        waypoint_sheet.update_cell(row_idx, 13, now_time)
                        st.cache_data.clear()
                        st.rerun()

        if active_route.get('status_A') == "Прибув" and active_route.get('status_B') == "Прибув" and active_route.get('status_C') == "Прибув":
            st.markdown("---")
            if st.button("💾 ЗАКРИТИ ТА ЗДАТИ ПУТІВКУ НА КП", type="primary", use_container_width=True):
                if waypoint_sheet and row_idx:
                    waypoint_sheet.update_cell(row_idx, 14, "TRUE")
                    st.success("Путівку успішно здано в архів КП!")
                    st.balloons()
                    st.cache_data.clear()
                    st.rerun()

        st.markdown("---")
        with st.expander("🚨 СКАСУВАТИ ЛИСТ МАРШРУТУ (АВАРІЙНА ВІДМІНА)"):
            with st.form(key="user_cancel_form"):
                user_cancel_reason = st.text_input("Вкажіть коментар/причину відміни маршруту:")
                if st.form_submit_button("❌ Підтвердити скасування путівки", use_container_width=True):
                    if user_cancel_reason and waypoint_sheet and row_idx:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        waypoint_sheet.update_cell(row_idx, 14, "CANCELLED")
                        waypoint_sheet.update_cell(row_idx, 4, f"{active_route.get('route_name')} (СКАСОВАНО екіпажем {st.session_state.username} о {now_str}. Коментар: {user_cancel_reason})")
                        st.error("Маршрут скасовано. Дані передані на КП.")
                        st.cache_data.clear()
                        st.rerun()
                    elif not user_cancel_reason:
                        st.warning("Необхідно обов'язково ввести коментар для скасування завдання!")

    # =========================================================================
    # 📦 РЕЖИМ 2: ЗАМОВЛЕННЯ ЗАБЕЗПЕЧЕННЯ (ЛОГІСТИКА)
    # =========================================================================
    elif menu_option == "📦 Замовлення забезпечення":
        st.markdown("## 📦 Логістика та Забезпечення")
        tab1, tab2, tab3 = st.tabs(["🆕 Новий запит", "⏳ Активні замовлення", "🗃️ Архів замовлень"])
        
        try:
            positions_sheet = load_sheet_data("positions")
            pos_list = [pos.get('position_name') for pos in positions_sheet if pos.get('position_name')]
        except:
            pos_list = ["Не вказано"]

        with tab1:
            st.subheader("Форма нового запиту майна")
            full_name = st.text_input("Прізвище, Ім'я або Позивний заявника:")
            current_pos = st.selectbox("Оберіть локацію/позицію призначення:", pos_list if pos_list else ["Порожньо"])
            urgency = st.radio("Рівень терміновості:", ["⚠️ НЕ TЕРМІНОВО", "🔥 ТЕРМІНОВО"], index=0)
            
            st.write("📋 Перелік майна/забезпечення:")
            if "items_count" not in st.session_state:
                st.session_state.items_count = 1
                
            items_inputs = []
            for i in range(st.session_state.items_count):
                item = st.text_input(f"Назва майна / Кількість №{i+1}:", key=f"item_input_{i}")
                if item:
                    items_inputs.append(item)
                    
            if st.button("➕ Додати ще одну позицію майна"):
                st.session_state.items_count += 1
                st.rerun()
                
            if st.button("🚀 ВІДПРАВИТИ ЗАПИТ НА КП", use_container_width=True, type="primary"):
                if full_name and items_inputs and supply_sheet:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    items_string = " | ".join(items_inputs)
                    request_id = 1
                    if all_supplies:
                        request_id = max([int(r.get('id', 0)) for r in all_supplies]) + 1
                    supply_sheet.append_row([request_id, now_str, st.session_state.username, full_name, current_pos, urgency, items_string, "Новий запит", "", "", "", "FALSE"])
                    st.success("Запит успішно надіслано Командному пункту!")
                    st.session_state.items_count = 1
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Заповніть поле заявника та хоча б одне поле майна!")

        with tab2:
            st.subheader("Замовлення в процесі обробки / В дорозі")
            my_active = [r for r in all_supplies if str(r.get('unit_username')) == st.session_state.username and str(r.get('is_archived')) == "FALSE"]
            
            if not my_active:
                st.info("У вас немає активних замовлень на цей момент.")
                
            for req in my_active:
                row_idx = next((i for i, r in enumerate(all_supplies, start=2) if str(r.get('id')) == str(req.get('id'))), None)
                
                if req.get('status') == "Новий запит":
                    with st.container(border=True):
                        st.warning(f"📦 Замовлення №{req.get('id')} — Очікує підтвердження КП ({req.get('urgency')})")
                        st.write(f"**Що замовлено:** {req.get('items_list')}")
                        
                elif req.get('status') == "В дорозі / Доставка":
                    with st.container(border=True):
                        st.info(f"🚚 Замовлення №{req.get('id')} — В ДОРОЗІ (Відправлено: {req.get('shipping_time')})")
                        
                        col_u1, col_u2 = st.columns(2)
                        with col_u1:
                            st.markdown(f"**📝 Ви замовляли:**\n{req.get('items_list')}")
                        with col_u2:
                            st.markdown(f"**📦 КП фактично відправив:**\n:green[{req.get('items_sent') if req.get('items_sent') else req.get('items_list')}]")
                        
                        if req.get('admin_comment'):
                            st.warning(f"💬 **Коментар КП:** {req.get('admin_comment')}")
                            
                        st.markdown(f"**Офіцер доставки (КП):** {req.get('processed_by')}")
                        
                        if st.button(f"🏁 Підтвердити Отримання №{req.get('id')}", key=f"confirm_{req.get('id')}", use_container_width=True, type="primary"):
                            if supply_sheet and row_idx:
                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                supply_sheet.update_cell(row_idx, 8, "Надійшло / Підтверджено")
                                supply_sheet.update_cell(row_idx, 11, now_str)
                                st.success("Отримання успішно підтверджено!")
                                st.cache_data.clear()
                                st.rerun()
                                
                elif req.get('status') == "Надійшло / Підтверджено":
                    with st.container(border=True):
                        st.success(f"✅ Замовлення №{req.get('id')} — Надійшло / Підтверджено")
                        
                        col_u1, col_u2 = st.columns(2)
                        with col_u1:
                            st.markdown(f"**📝 Ви замовляли:**\n{req.get('items_list')}")
                        with col_u2:
                            st.markdown(f"**📦 Отримано (за версією КП):**\n{req.get('items_sent') if req.get('items_sent') else req.get('items_list')}")
                            
                        if req.get('admin_comment'):
                            st.markdown(f"💬 **Коментар КП:** *{req.get('admin_comment')}*")
                            
                        st.caption("Очікує фінального закриття офіцером Командного пункту.")

        with tab3:
            st.subheader("Історія виконаних замовлень")
            my_archive = [r for r in all_supplies if str(r.get('unit_username')) == st.session_state.username and str(r.get('is_archived')) == "TRUE"]
            if not my_archive:
                st.text("Архів порожній.")
            for req in my_archive:
                with st.expander(f"📦 Замовлення №{req.get('id')} від {req.get('timestamp')} (Виконано)"):
                    st.markdown(f"**Хто отримував:** {req.get('full_name')} | **Позиція:** {req.get('position_name')}")
                    st.markdown(f"**📝 Що замовляли:** {req.get('items_list')}")
                    st.markdown(f"**📦 Що фактично отримано:** {req.get('items_sent') if req.get('items_sent') else req.get('items_list')}")

    # =========================================================================
    # 🗃️ РЕЖИМ 3: АРХІВ МАРШРУТІВ ЕКІПАЖУ
    # =========================================================================
    elif menu_option == "🗃️ Закриті путівки (Архів)":
        st.markdown("## 🗃️ Архів виконаних маршрутів")
        my_closed_routes = [r for r in all_routes if str(r.get('assigned_to')) == st.session_state.username and str(r.get('is_closed')) in ["TRUE", "CANCELLED"]]

        if not my_closed_routes:
            st.info("Архів порожній.")
            return

        for route in my_closed_routes:
            status_lbl = "❌ СКАСОВАНО" if route.get('is_closed') == "CANCELLED" else "✅ ВИКОНАНО"
            with st.expander(f"📅 Маршрут від {route.get('date')} — {status_lbl} — {route.get('route_name')}"):
                st.write(f"А: {route.get('point_A')} ({route.get('time_A')})")
                st.write(f"Б: {route.get('point_B')} ({route.get('time_B')})")
                st.write(f"С: {route.get('point_C')} ({route.get('time_C')})")

    # --- ⚙️ СИСТЕМНА КНОПКА ТА СКРИПТ АВТООНОВЛЕННЯ (ВНИЗУ DOM) ⚙️ ---
    if st.button("Сховане оновлення", key="silent_cp_refresh_btn_user"):
        st.cache_data.clear()
        st.rerun()

    st.components.v1.html(
        """
        <script>
            function attemptRefreshUser() {
                const activeEl = window.parent.document.activeElement;
                if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
                    setTimeout(attemptRefreshUser, 5000); 
                    return; 
                }
                const buttons = window.parent.document.querySelectorAll('.stButton button');
                for (const btn of buttons) {
                    if (btn.innerText.includes("Сховане оновлення")) {
                        btn.click();
                        return;
                    }
                }
                setTimeout(attemptRefreshUser, 5000);
            }
            setTimeout(attemptRefreshUser, 10000);
            
            // Приховуємо системну кнопку фонової синхронізації
            setTimeout(() => {
                const hBtn = Array.from(window.parent.document.querySelectorAll('.stButton button')).find(b => b.innerText.includes("Сховане оновлення"));
                if(hBtn) hBtn.closest('div[data-testid="stElementContainer"]').style.display = 'none';
            }, 100);
        </script>
        """,
        height=0,
    )