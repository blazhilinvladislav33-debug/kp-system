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
        st.session_state.username = "Оператор КП"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = True
    if "played_sounds" not in st.session_state:
        st.session_state.played_sounds = []
    if "notified_route_updates" not in st.session_state:
        st.session_state.notified_route_updates = []

    # --- 🛑 ЯДЕРНИЙ CSS-ЩИТ ВІД ЗАТУХАННЯ 🛑 ---
    st.markdown(
        """
        <style>
        /* 1. Блокуємо затухання головних контейнерів */
        .stApp, 
        .main, 
        .block-container,
        [data-testid="stAppViewContainer"], 
        [data-testid="stAppViewBlockContainer"], 
        [data-testid="stSidebar"] {
            opacity: 1 !important;
            filter: blur(0px) brightness(1) !important;
            -webkit-filter: blur(0px) brightness(1) !important;
            transition: none !important;
        }

        /* 2. Блокуємо затухання специфічних внутрішніх блоків Streamlit (саме тут ховається сірий екран) */
        div[data-testid="stAppViewContainer"] > section > div > div,
        div[data-testid="stAppViewBlockContainer"] > div,
        div[data-testid="stAppViewContainer"] > section > div:nth-child(1),
        div[data-testid="stAppViewContainer"] > section > div:nth-child(2) {
            opacity: 1 !important;
            filter: none !important;
            -webkit-filter: none !important;
            transition: none !important;
        }

        /* 3. Скасовуємо будь-які стани 'running' по всьому документу */
        div[data-styled-state="running"],
        html[data-test-script-state="running"] * {
            opacity: 1 !important;
            filter: none !important;
            transition: none !important;
        }

        /* 4. Повне приховування системної плашки та індикатора загрузки */
        [data-testid="stStatusWidget"], header[data-testid="stHeader"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
        }

        /* --- Стилі компактності --- */
        [data-testid="stAppViewContainer"] .main h1 { font-size: clamp(1.15rem, 2.5vw, 1.45rem) !important; font-weight: 700 !important; margin-bottom: 0.5rem !important; padding-top: 0.5rem !important; }
        [data-testid="stAppViewContainer"] .main h2 { font-size: clamp(1.0rem, 2.2vw, 1.25rem) !important; font-weight: 600 !important; margin-top: 0.8rem !important; margin-bottom: 0.4rem !important; }
        [data-testid="stAppViewContainer"] .main h3, [data-testid="stAppViewContainer"] .main h4, [data-testid="stAppViewContainer"] .main h5 { font-size: clamp(0.9rem, 1.8vw, 1.1rem) !important; font-weight: 600 !important; margin-bottom: 0.3rem !important; }
        [data-testid="stAppViewContainer"] .main p, [data-testid="stAppViewContainer"] .main span, [data-testid="stAppViewContainer"] .main label, [data-testid="stAppViewContainer"] .main li { font-size: 13px !important; line-height: 1.35 !important; }
        [data-testid="stAppViewContainer"] .main code { font-size: 12px !important; padding: 1px 4px !important; }
        div[data-testid="element-container"] div[style*="border"] { padding: 0.65rem 0.8rem !important; margin-bottom: 0.35rem !important; border-radius: 6px !important; }
        div[data-testid="stForm"] { padding: 0.5rem !important; border-radius: 6px !important; }
        button[data-baseweb="tab"] { padding: 6px 12px !important; height: auto !important; }
        button[data-baseweb="tab"] div p { font-size: 13px !important; }
        div[data-testid="stWidgetLabel"] p { font-size: 12px !important; margin-bottom: 2px !important; }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] { padding-top: 4px !important; padding-bottom: 4px !important; font-size: 13px !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- 1. МЕНЮ БУТЕРБРОД ДЛЯ КП (Sidebar) ---
    with st.sidebar:
        st.markdown(f"### 🎛️ Меню Адміна КП")
        st.write(f"Оператор: **{st.session_state.username}**")
        st.caption("Роль: Головний Адміністратор")
        st.markdown("---")
        
        if st.button("🔄 Примусове оновлення бази", use_container_width=True, type="secondary"):
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("---")
        
        cp_menu = st.radio(
            "📍 ОБЕРІТЬ РЕЖИМ ДОСТУПУ:",
            [
                "🖥️ Оперативний моніторинг", 
                "🆕 Створити новий маршрут", 
                "📦 Створити посилку",
                "📍 Керування позиціями", 
                "👥 Реєстрація користувачів",
                "🗃️ Архів усіх маршрутів",
                "🗃️ Архів логістики (Supply)"
            ]
        )
        
        st.markdown("---")
        if st.button("🚪 Вийти з системи КП", use_container_width=True):
            st.session_state.authenticated = False
            st.cache_data.clear()
            st.rerun()

    # --- БЕЗПЕЧНЕ ЗЧИТУВАННЯ БАЗИ ДАНИХ (ЧЕРЕЗ КЕШ) ---
    all_routes = load_sheet_data("waypoints")
    all_supplies = load_sheet_data("supply")
    all_users = load_sheet_data("users")
    all_positions = load_sheet_data("positions")

    try: waypoint_sheet = db.sheet.worksheet("waypoints")
    except: waypoint_sheet = None
    
    try: supply_sheet = db.sheet.worksheet("supply")
    except: supply_sheet = None

    # =========================================================================
    # 🔊 ЗВУКОВИЙ СУПРОВІД 1: ЛОГІСТИКА (НОВІ ЗАПИТИ)
    # =========================================================================
    new_request_ids = [str(r.get('id')) for r in all_supplies if r.get('status') == "Новий запит"]
    st.session_state.played_sounds = [rid for rid in st.session_state.played_sounds if rid in new_request_ids]
    unnotified_requests = [rid for rid in new_request_ids if rid not in st.session_state.played_sounds]
    
    if unnotified_requests:
        st.components.v1.html(
            """
            <audio autoplay>
                <source src="https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg" type="audio/ogg">
            </audio>
            """,
            height=0,
        )
        st.toast("🚨 Виявлено нові незакриті запити забезпечення від підрозділів!")
        st.session_state.played_sounds = st.session_state.played_sounds + unnotified_requests

    # =========================================================================
    # 🔊 ЗВУКОВИЙ СУПРОВІД 2: МАРШРУТИ (РУХ ПО ТОЧКАХ ТА СКАСУВАННЯ)
    # =========================================================================
    new_route_events = []
    for r in all_routes:
        tid = str(r.get('id'))
        if r.get('status_A') == "Прибув": new_route_events.append(f"{tid}_A_{r.get('time_A')}")
        if r.get('status_B') == "Прибув": new_route_events.append(f"{tid}_B_{r.get('time_B')}")
        if r.get('status_C') == "Прибув": new_route_events.append(f"{tid}_C_{r.get('time_C')}")
        if str(r.get('is_closed')) == "CANCELLED": new_route_events.append(f"{tid}_CANCELLED")

    unnotified_route_events = [ev for ev in new_route_events if ev not in st.session_state.notified_route_updates]

    if unnotified_route_events:
        st.components.v1.html(
            """
            <audio autoplay>
                <source src="https://actions.google.com/sounds/v1/alarms/phone_alerts_and_rings.ogg" type="audio/ogg">
            </audio>
            """,
            height=0,
        )
        st.toast("🗺️ Зміна оперативної обстановки: Екіпаж відмітився на точці або скасував маршрут!")
        st.session_state.notified_route_updates = st.session_state.notified_route_updates + unnotified_route_events

    # =========================================================================
    # 🔥 РЕЖИМ 1: ОПЕРАТИВНИЙ МОНІТОРИНГ (ГОЛОВНИЙ ЕКРАН)
    # =========================================================================
    if cp_menu == "🖥️ Оперативний моніторинг":
        st.title("🦅 Оперативна обстановка — Головний екран")
        tab_trips, tab_logistics = st.tabs(["🗺️ Рух екіпажів (Путівки)", "📦 Замовлення забезпечення"])
        
        with tab_trips:
            st.subheader("📅 Стенд запланованих поїздок (Анонси)")
            planned_trips = [r for r in all_routes if str(r.get('is_closed')) == "PLANNED"]
            
            if not planned_trips:
                st.caption("Немає запланованих поїздок на майбутнє.")
            else:
                for ptrip in planned_trips:
                    p_row_idx = next((i for i, r in enumerate(all_routes, start=2) if str(r.get('id')) == str(ptrip.get('id'))), None)
                    with st.container(border=True):
                        st.markdown(f"🗓️ **Планова дата:** {ptrip.get('date')} | **Екіпаж:** `{ptrip.get('assigned_to')}` | **Маршрут:** *{ptrip.get('route_name')}*")
                        st.markdown(f"📍 Напрямок: `{ptrip.get('point_A')}` ➡️ `{ptrip.get('point_B')}` ➡️ `{ptrip.get('point_C')}`")
                        
                        if st.button(f"🚀 Перевести в активний маршрутний лист №{ptrip.get('id')}", key=f"activate_p_{ptrip.get('id')}", use_container_width=True, type="primary"):
                            if waypoint_sheet and p_row_idx:
                                waypoint_sheet.update_cell(p_row_idx, 14, "FALSE")
                                st.success(f"Маршрут №{ptrip.get('id')} успішно активовано!")
                                st.cache_data.clear()
                                st.rerun()
            st.markdown("---")

            st.subheader("🚗 Активні поїздки підрозділів (В русі)")
            active_trips = [r for r in all_routes if str(r.get('is_closed')) == "FALSE"]
            
            if not active_trips:
                st.success("На даний момент немає активних екіпажів у русі.")
            else:
                for trip in active_trips:
                    row_idx = next((i for i, r in enumerate(all_routes, start=2) if str(r.get('id')) == str(trip.get('id'))), None)
                    
                    if trip.get('status_C') == "Прибув":
                        stage = "🏁 Завершив маршрут (Очікує закриття)"
                        color = "green"
                    elif trip.get('status_B') == "Прибув":
                        stage = f"🚗 Прямує до Точки С. (Пройшов Б о {trip.get('time_B')})"
                        color = "blue"
                    elif trip.get('status_A') == "Прибув":
                        stage = f"🚗 Прямує до Точки Б. (Пройшов А о {trip.get('time_A')})"
                        color = "orange"
                    else:
                        stage = "⏳ Путівку отримано, екіпаж ще не рушив"
                        color = "grey"
                        
                    with st.container(border=True):
                        st.markdown(f"**Екіпаж:** `{trip.get('assigned_to')}` | **Маршрут:** *{trip.get('route_name')}*")
                        st.markdown(f"📍 Поточний етап: <b style='color:{color};'>{stage}</b>", unsafe_allow_html=True)
                        
                        st.markdown(f"🔹 **[А]**: {trip.get('point_A')} *({trip.get('status_A') or 'Очікує'})*")
                        st.markdown(f"🔹 **[Б]**: {trip.get('point_B')} *({trip.get('status_B') or 'Очікує'})*")
                        st.markdown(f"🔹 **[С]**: {trip.get('point_C')} *({trip.get('status_C') or 'Очікує'})*")
                        
                        with st.expander("❌ Скасувати цей маршрут/путівку"):
                            with st.form(key=f"cancel_form_{trip.get('id')}"):
                                cancel_reason = st.text_input("Обов'язковий коментар/причина скасування:")
                                if st.form_submit_button("🔥 Підтвердити скасування путівки", type="primary"):
                                    if cancel_reason and waypoint_sheet and row_idx:
                                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        waypoint_sheet.update_cell(row_idx, 14, "CANCELLED")
                                        waypoint_sheet.update_cell(row_idx, 4, f"{trip.get('route_name')} (СКАСОВАНО користувачем {st.session_state.username} о {now_str}. Причина: {cancel_reason})")
                                        st.success("Маршрут успішно скасовано та списано в архів!")
                                        st.cache_data.clear()
                                        st.rerun()
                                    elif not cancel_reason:
                                        st.warning("Ви не можете скасувати маршрут без пояснення причини!")

        with tab_logistics:
            active_requests = [r for r in all_supplies if str(r.get('is_archived')) == "FALSE"]
            shipping_reqs = [r for r in active_requests if r.get('status') == "В дорозі / Доставка"]
            urgent_reqs = [r for r in active_requests if r.get('status') == "Новий запит" and "ТЕРМІНОВО" in str(r.get('urgency'))]
            normal_reqs = [r for r in active_requests if r.get('status') == "Новий запит" and "НЕ ТЕРМІНОВО" in str(r.get('urgency'))]
            confirmed_reqs = [r for r in active_requests if r.get('status') == "Надійшло / Підтверджено"]

            st.markdown("## 🚚 1. ВАНТАЖІ В ДОРОЗІ (ПОТОЧНА ДОСТАВКА)")
            if not shipping_reqs:
                st.info("На даний момент немає активних вантажів у дорозі.")
            else:
                for req in shipping_reqs:
                    with st.container(border=True):
                        st.info(f"🟢 **Вантаж №{req.get('id')}** прямує на **{req.get('position_name')}** підрозділу `{req.get('unit_username')}`.")
                        st.write(f"📝 **Замовляли:** {req.get('items_list')}")
                        st.write(f"📦 **Фактично відправлено КП:** {req.get('items_sent', req.get('items_list'))}")
                        if req.get('admin_comment'):
                            st.write(f"💬 **Коментар адміна:** *{req.get('admin_comment')}*")
                        st.caption(f"Відправив admin: {req.get('processed_by')} о {req.get('shipping_time')}")
            
            st.markdown("---")

            st.markdown("### 🔥 2. НОВІ TЕРМІНОВІ ЗАПИТИ (ОЧІКУЮТЬ ВІДПРАВКИ)")
            if not urgent_reqs:
                st.success("Немає нових термінових запитів.")
            for req in urgent_reqs:
                row_idx = next((i for i, r in enumerate(all_supplies, start=2) if str(r.get('id')) == str(req.get('id'))), None)
                with st.container(border=True):
                    st.error(f"🚨 ТЕРМІНОВИЙ ЗАПИТ №{req.get('id')} від: {req.get('unit_username')} ({req.get('full_name')})")
                    st.write(f"📍 **Позиція:** {req.get('position_name')} | 🕒 {req.get('timestamp')}")
                    st.markdown(f"📋 **ЗАМОВЛЕНО ПІДРОЗДІЛОМ:** **{req.get('items_list')}**")
                    
                    with st.form(key=f"edit_form_urg_{req.get('id')}"):
                        sent_items_urg = st.text_area("📦 Що фактично завантажено / відправляється:", value=req.get('items_list'))
                        admin_comm_urg = st.text_input("💬 Додати коментар адміна (деталі доставки):")
                        if st.form_submit_button(f"🚚 Підтвердити відправку", type="primary", use_container_width=True):
                            if supply_sheet and row_idx:
                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                supply_sheet.update_cell(row_idx, 8, "В дорозі / Доставка")
                                supply_sheet.update_cell(row_idx, 9, st.session_state.username)
                                supply_sheet.update_cell(row_idx, 10, now_str)
                                supply_sheet.update_cell(row_idx, 13, sent_items_urg)  
                                supply_sheet.update_cell(row_idx, 14, admin_comm_urg)  
                                st.cache_data.clear()
                                st.rerun()

            st.markdown("### ⚠️ 3. ПЛАНОВІ (НЕ ТЕРМІНОВІ) ЗАПИТИ")
            if not normal_reqs:
                st.text("Немає планових запитів.")
            for req in normal_reqs:
                row_idx = next((i for i, r in enumerate(all_supplies, start=2) if str(r.get('id')) == str(req.get('id'))), None)
                with st.container(border=True):
                    st.warning(f"📦 ЗАПИТ №{req.get('id')} — {req.get('unit_username')} ({req.get('full_name')})")
                    st.write(f"📍 **Позиція:** {req.get('position_name')} | 🕒 {req.get('timestamp')}")
                    st.markdown(f"📋 **ЗАМОВЛЕНО ПІДРОЗДІЛОМ:** **{req.get('items_list')}**")
                    
                    with st.form(key=f"edit_form_norm_{req.get('id')}"):
                        sent_items_norm = st.text_area("📦 Що фактично завантажено / відправляється:", value=req.get('items_list'))
                        admin_comm_norm = st.text_input("💬 Додати коментар адміна:")
                        if st.form_submit_button(f"🚚 Відправити доставку", use_container_width=True):
                            if supply_sheet and row_idx:
                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                supply_sheet.update_cell(row_idx, 8, "В дорозі / Доставка")
                                supply_sheet.update_cell(row_idx, 9, st.session_state.username)
                                supply_sheet.update_cell(row_idx, 10, now_str)
                                supply_sheet.update_cell(row_idx, 13, sent_items_norm)  
                                supply_sheet.update_cell(row_idx, 14, admin_comm_norm)  
                                st.cache_data.clear()
                                st.rerun()

            st.markdown("### ✅ 4. ПІДТВЕРДЖЕНІ ОТРИМАННЯ (ОЧІКУЮТЬ АРХІВАЦІЇ)")
            if not confirmed_reqs:
                st.text("Немає нових підтверджень від підрозділів.")
            for req in confirmed_reqs:
                row_idx = next((i for i, r in enumerate(all_supplies, start=2) if str(r.get('id')) == str(req.get('id'))), None)
                with st.container(border=True):
                    st.success(f"Вантаж №{req.get('id')} успішно отримано на позиції {req.get('position_name')} о {req.get('delivery_time')}!")
                    st.write(f"📋 **Замовляли:** {req.get('items_list')}")
                    st.write(f"📦 **Було відправлено:** {req.get('items_sent', req.get('items_list'))}")
                    if req.get('admin_comment'):
                        st.write(f"💬 **Коментар:** {req.get('admin_comment')}")
                    if st.button(f"📁 Закрити замовлення та здати в Архів №{req.get('id')}", key=f"cp_arch_{req.get('id')}", use_container_width=True):
                        if supply_sheet and row_idx:
                            supply_sheet.update_cell(row_idx, 12, "TRUE")
                            st.cache_data.clear()
                            st.rerun()

    # =========================================================================
    # 🆕 РЕЖИМ 2: СТВОРЕННЯ МАРШРУТУ 
    # =========================================================================
    elif cp_menu == "🆕 Створити новий маршрут":
        st.title("🆕 Створення електронної путівки")
        units_list = [u.get('username') for u in all_users if u.get('role') == 'unit']

        col_w1, col_w2 = st.columns(2)
        with col_w1:
            route_date = st.date_input("Дата маршруту", datetime.now()).strftime("%Y-%m-%d")
            assign_to = st.selectbox("Призначити підрозділу (Екіпажу):", units_list if units_list else ["Немає юзерів"])
            route_name = st.text_input("Назва завдання / Напрямок:")
            
            route_status = st.radio("Статус путівки при створенні:", ["🚀 Одразу активувати (В рух)", "📅 Запланувати поїздку (Попередній анонс)"])
            
        with col_w2:
            p_A = st.text_input("Точка А (Старт):")
            p_B = st.text_input("Точка Б (Проміжна):")
            p_C = st.text_input("Точка С (Кінець):")

        if st.button("🚀 ЗАТВЕРДИТИ МАРШРУТНИЙ ЛИСТ", use_container_width=True, type="primary"):
            if route_name and p_A and p_B and p_C and waypoint_sheet:
                is_closed_val = "PLANNED" if "Запланувати" in route_status else "FALSE"
                route_id = max([int(r.get('id', 0)) for r in all_routes], default=0) + 1
                waypoint_sheet.append_row([route_id, assign_to, route_date, route_name, p_A, "Очікує", "", p_B, "Очікує", "", p_C, "Очікує", "", is_closed_val])
                st.success("Путівку успішно збережено в систему!")
                st.cache_data.clear()
                st.rerun()

    # =========================================================================
    # 📦 РЕЖИМ 3: СТВОРЕННЯ ПОСИЛКИ ВІД КП
    # =========================================================================
    elif cp_menu == "📦 Створити посилку":
        st.title("📦 Створення замовлення (від КП)")
        units_list = [u.get('username') for u in all_users if u.get('role') == 'unit']
        pos_list = [p.get('position_name') for p in all_positions if p.get('position_name')]
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            assign_unit = st.selectbox("Для якого підрозділу (Екіпажу):", units_list if units_list else ["Немає юзерів"])
            full_name = st.text_input("Хто отримувач (Прізвище/Позивний):", value="Від КП")
            current_pos = st.selectbox("Оберіть позицію призначення:", pos_list if pos_list else ["Порожньо"])
        with col_s2:
            urgency = st.radio("Рівень терміновості:", ["⚠️ НЕ TЕРМІНОВО", "🔥 ТЕРМІНОВО"], index=0)
            
        st.write("📋 Перелік майна/забезпечення:")
        if "admin_items_count" not in st.session_state:
            st.session_state.admin_items_count = 1
            
        items_inputs = []
        for i in range(st.session_state.admin_items_count):
            item = st.text_input(f"Назва майна / Кількість №{i+1}:", key=f"admin_item_input_{i}")
            if item:
                items_inputs.append(item)
                
        if st.button("➕ Додати ще одну позицію майна"):
            st.session_state.admin_items_count += 1
            st.rerun()
            
        if st.button("🚀 СТВОРИТИ ЗАПИТ У СИСТЕМІ", use_container_width=True, type="primary"):
            if assign_unit and full_name and items_inputs and supply_sheet:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                items_string = " | ".join(items_inputs)
                request_id = max([int(r.get('id', 0)) for r in all_supplies], default=0) + 1
                supply_sheet.append_row([request_id, now_str, assign_unit, full_name, current_pos, urgency, items_string, "Новий запит", "", "", "", "FALSE"])
                st.success("Посилку успішно створено та додано в чергу!")
                st.session_state.admin_items_count = 1
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Заповніть усі поля та додайте хоча б одне майно!")

    # =========================================================================
    # 📍 РЕЖИМ 4: КЕРУВАННЯ ПОЗИЦІЯМИ
    # =========================================================================
    elif cp_menu == "📍 Керування позиціями":
        st.title("📍 Керування бойовими позиціями / Локаціями")
        
        col_pos1, col_pos2 = st.columns(2)
        with col_pos1:
            st.subheader("🆕 Додати нову локацію")
            pos_name = st.text_input("Назва нової позиції / ВОП / Позивний локації:")
            pos_coords = st.text_input("Координати (Посилання або WGS84):")
            if st.button("Зберегти позицію в базу", use_container_width=True):
                if pos_name and pos_coords:
                    db.add_new_position(pos_name, pos_coords, st.session_state.username)
                    st.success(f"Позицію '{pos_name}' успішно внесено!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Заповніть усі поля.")
                    
        with col_pos2:
            st.subheader("📋 Позиції в наявності:")
            if not all_positions:
                st.info("У базі ще немає створених позицій.")
            else:
                for p in all_positions:
                    st.markdown(f"📍 **{p.get('position_name')}** — `{p.get('coordinates')}`")

    # =========================================================================
    # 👥 РЕЖИМ 5: РЕЄСТРАЦІЯ КОРИСТУВАЧІВ
    # =========================================================================
    elif cp_menu == "👥 Реєстрація користувачів":
        st.title("👥 Реєстрація нових акаунтів у системі")
        
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            st.subheader("🆕 Зареєструвати новий акаунт")
            new_user = st.text_input("Вкажіть новий Логін (латиницею):")
            new_pass = st.text_input("Вкажіть новий Пароль:", type="password")
            new_role = st.selectbox("Призначити рівень доступу (Роль):", ["unit", "command_post"], format_func=lambda x: "Підрозділ (User)" if x == "unit" else "Командний Пункт (Admin)")
            unit_info = st.text_input("Назва підрозділу або Позивний офіцера:")
            
            if st.button("Зареєструвати акаунт у базі даних", use_container_width=True, type="primary"):
                if new_user and new_pass and unit_info:
                    db.add_new_user(new_user, new_pass, new_role, unit_info)
                    st.success(f"Користувача '{new_user}' успішно внесено в Google Sheets!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Усі поля мають бути заповнені.")
                    
        with col_u2:
            st.subheader("📋 Зареєстровані користувачі:")
            if not all_users:
                st.info("У базі немає користувачів.")
            else:
                for u in all_users:
                    r_label = "💂‍♂️ КП (Admin)" if u.get('role') == 'command_post' else "📱 Підрозділ (User)"
                    st.markdown(f"**{u.get('username')}** ({u.get('unit_name', u.get('unit_info'))}) — *{r_label}*")

    # =========================================================================
    # 🗃️ РЕЖИМИ 6 ТА 7: АРХІВИ
    # =========================================================================
    elif cp_menu == "🗃️ Архів усіх маршрутів":
        st.title("🗃️ Глобальний архів усіх путівок")
        closed_trips = [r for r in all_routes if str(r.get('is_closed')) in ["TRUE", "CANCELLED"]]
        if not closed_trips:
            st.info("Архів путівок порожній.")
            return
        for trip in closed_trips:
            status_text = "❌ СКАСОВАНО" if trip.get('is_closed') == "CANCELLED" else "✅ ВИКОНАНО"
            with st.expander(f"📅 [{trip.get('date')}] — {status_text} — {trip.get('assigned_to')} — {trip.get('route_name')}"):
                st.markdown(f"**Точка А:** {trip.get('point_A')} — 🕒 {trip.get('time_A')} ({trip.get('status_A') or 'Ні'})")
                st.markdown(f"**Точка Б:** {trip.get('point_B')} — 🕒 {trip.get('time_B')} ({trip.get('status_B') or 'Ні'})")
                st.markdown(f"**Точка С:** {trip.get('point_C')} — 🕒 {trip.get('time_C')} ({trip.get('status_C') or 'Ні'})")

    elif cp_menu == "🗃️ Архів логістики (Supply)":
        st.title("🗃️ Глобальний архів забезпечення КП")
        cp_archive = [r for r in all_supplies if str(r.get('is_archived')) == "TRUE"]
        if not cp_archive:
            st.info("Архів замовлень логістики порожній.")
            return
        for req in cp_archive:
            with st.expander(f"📦 Замовлення №{req.get('id')} від {req.get('timestamp')} — {req.get('unit_username')}"):
                st.markdown(f"📍 **Куди:** {req.get('position_name')} | **Замовляв:** {req.get('full_name')}")
                st.markdown(f"📝 **Що просили:** {req.get('items_list')}")
                st.markdown(f"📦 **Що реально видано КП:** {req.get('items_sent', req.get('items_list'))}")
                if req.get('admin_comment'):
                    st.markdown(f"💬 **Коментар адміна:** {req.get('admin_comment')}")
                st.markdown(f"🚚 **Обробив:** {req.get('processed_by')} | ✅ **Отримано:** {req.get('delivery_time')}")

    # --- ⚙️ ЄДИНА СИСТЕМНА КНОПКА ТА СКРИПТ ОНОВЛЕННЯ (ВНИЗУ DOM) ⚙️ ---
    if st.button("Сховане оновлення КП", key="silent_cp_refresh_btn", type="secondary"):
        st.cache_data.clear()
        st.rerun()

    st.components.v1.html(
        """
        <script>
            function attemptRefresh() {
                const activeEl = window.parent.document.activeElement;
                if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
                    setTimeout(attemptRefresh, 5000); 
                    return; 
                }
                const buttons = window.parent.document.querySelectorAll('.stButton button');
                for (const btn of buttons) {
                    if (btn.innerText.includes("Сховане оновлення КП")) {
                        btn.click();
                        return;
                    }
                }
                setTimeout(attemptRefresh, 5000); 
            }
            setTimeout(attemptRefresh, 10000);
            
            // Приховуємо кнопку візуально, щоб вона не заважала внизу сторінки
            setTimeout(() => {
                const hBtn = Array.from(window.parent.document.querySelectorAll('.stButton button')).find(b => b.innerText.includes("Сховане оновлення КП"));
                if(hBtn) hBtn.closest('div[data-testid="stElementContainer"]').style.display = 'none';
            }, 100);
        </script>
        """,
        height=0,
    )