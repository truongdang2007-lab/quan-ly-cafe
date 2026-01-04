import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- KHỞI TẠO DATABASE ---
def init_db():
    conn = sqlite3.connect('cafe_v9.db')
    c = conn.cursor()
    # Thêm cột 'category' vào menu
    c.execute('''CREATE TABLE IF NOT EXISTS menu 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, category TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS active_orders 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, order_name TEXT, item_name TEXT, price REAL)''')
    # Lưu date kiểu YYYY-MM-DD để dễ lọc
    c.execute('''CREATE TABLE IF NOT EXISTS sales 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, amount REAL, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, reason TEXT, cost REAL, date TEXT)''')
    conn.commit()
    conn.close()

init_db()

def run_query(query, params=(), fetch=False):
    with sqlite3.connect('cafe_v9.db') as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        if fetch: return c.fetchall()

# --- GIAO DIỆN ---
st.set_page_config(page_title="Cafe v9 - Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>☕ CAFE PRO v9: QUẢN LÝ CHUYÊN NGHIỆP</h1>", unsafe_allow_html=True)

tab_order, tab_report, tab_expense, tab_menu = st.tabs(["🛒 GỌI MÓN", "📊 BÁO CÁO", "💸 CHI PHÍ", "⚙️ CÀI ĐẶT"])

# --- 1. GỌI MÓN & THANH TOÁN ---
with tab_order:
    col_list, col_detail = st.columns([1, 2])

    with col_list:
        st.subheader("Danh sách Đơn")
        new_order = st.text_input("Tên đơn (Bàn...)", placeholder="Nhập tên bàn/đơn...")
        if st.button("➕ Tạo đơn mới"):
            if new_order:
                st.session_state['current_order'] = new_order
                st.toast(f"Đã mở {new_order}")
            else: st.error("Nhập tên đơn đã!")

        active_list = [row[0] for row in run_query("SELECT DISTINCT order_name FROM active_orders", fetch=True)]
        if active_list:
            st.divider()
            selected_order = st.radio("Đơn đang phục vụ:", active_list)
            if selected_order: st.session_state['current_order'] = selected_order

    with col_detail:
        if 'current_order' in st.session_state:
            order_name = st.session_state['current_order']
            st.subheader(f"📍 Đang phục vụ: {order_name}")

            # --- LỌC ĐỒ UỐNG THEO LOẠI ---
            st.write("**Thêm món:**")
            categories = run_query("SELECT DISTINCT category FROM menu", fetch=True)
            cat_list = ["Tất cả"] + [c[0] for c in categories if c[0]]
            chosen_cat = st.selectbox("Lọc theo loại:", cat_list)

            query_menu = "SELECT name, price FROM menu"
            params_menu = ()
            if chosen_cat != "Tất cả":
                query_menu += " WHERE category = ?"
                params_menu = (chosen_cat,)
            
            menu_items = run_query(query_menu, params_menu, fetch=True)
            cols = st.columns(3)
            for i, (name, price) in enumerate(menu_items):
                if cols[i % 3].button(f"{name}\n{price:,.0f}", key=f"btn_{name}_{i}"):
                    run_query("INSERT INTO active_orders (order_name, item_name, price) VALUES (?,?,?)", (order_name, name, price))
                    st.rerun()

            st.write("---")
            current_items = run_query("SELECT id, item_name, price FROM active_orders WHERE order_name = ?", (order_name,), fetch=True)
            if current_items:
                df_order = pd.DataFrame(current_items, columns=["ID", "Món", "Giá"])
                st.table(df_order[["Món", "Giá"]])
                total_order = df_order["Giá"].sum()
                st.markdown(f"### 💰 Tổng: {total_order:,.0f} VNĐ")

                c1, c2 = st.columns(2)
                if c1.button("✅ THANH TOÁN", use_container_width=True, type="primary"):
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for _, item, price in current_items:
                        run_query("INSERT INTO sales (item, amount, date) VALUES (?,?,?)", (item, price, now))
                    run_query("DELETE FROM active_orders WHERE order_name = ?", (order_name,))
                    st.success(f"Xong {order_name}!")
                    del st.session_state['current_order']
                    st.rerun()
                if c2.button("❌ Hủy đơn", use_container_width=True):
                    run_query("DELETE FROM active_orders WHERE order_name = ?", (order_name,))
                    del st.session_state['current_order']
                    st.rerun()

# --- 2. BÁO CÁO NGÀY/THÁNG ---
with tab_report:
    st.header("Thống kê Lợi nhuận")
    
    today = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")

    # Hàm tính toán nhanh
    def get_stats(time_str):
        s = run_query("SELECT SUM(amount) FROM sales WHERE date LIKE ?", (f"{time_str}%",), fetch=True)[0][0] or 0
        e = run_query("SELECT SUM(cost) FROM expenses WHERE date LIKE ?", (f"{time_str}%",), fetch=True)[0][0] or 0
        return s, e

    s_day, e_day = get_stats(today)
    s_month, e_month = get_stats(this_month)
    s_total, e_total = get_stats("")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📅 **HÔM NAY ({today})**")
        st.write(f"Thu: {s_day:,.0f}")
        st.write(f"Chi: {e_day:,.0f}")
        st.subheader(f"Lời: {s_day-e_day:,.0f}")

    with col2:
        st.success(f"📅 **THÁNG NÀY ({this_month})**")
        st.write(f"Thu: {s_month:,.0f}")
        st.write(f"Chi: {e_month:,.0f}")
        st.subheader(f"Lời: {s_month-e_month:,.0f}")

    with col3:
        st.warning("📊 **TỔNG CỘNG**")
        st.write(f"Thu: {s_total:,.0f}")
        st.write(f"Chi: {e_total:,.0f}")
        st.subheader(f"Lời: {s_total-e_total:,.0f}")

    st.divider()
    if st.button("🗑 Reset toàn bộ dữ liệu (Cẩn thận!)"):
        if st.checkbox("Xác nhận xoá"):
            run_query("DELETE FROM sales"); run_query("DELETE FROM expenses")
            st.rerun()

# --- 3. CHI PHÍ ---
with tab_expense:
    st.header("Nhập chi phí")
    reason = st.text_input("Nội dung chi")
    cost = st.number_input("Số tiền", min_value=0, step=1000)
    if st.button("Lưu chi phí"):
        run_query("INSERT INTO expenses (reason, cost, date) VALUES (?,?,?)", 
                  (reason, cost, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        st.success("Đã lưu!")

# --- 4. CÀI ĐẶT MENU ---
with tab_menu:
    st.header("Quản lý món ăn & Phân loại")
    col_in, col_list = st.columns([1, 1])
    with col_in:
        m_name = st.text_input("Tên món")
        m_price = st.number_input("Giá", min_value=0, step=1000)
        m_cat = st.selectbox("Loại đồ uống:", ["Cafe", "Trà", "Đá xay", "Nước ép", "Khác"])
        if st.button("Thêm món"):
            run_query("INSERT INTO menu (name, price, category) VALUES (?,?,?)", (m_name, m_price, m_cat))
            st.rerun()
    
    with col_list:
        menu_data = run_query("SELECT id, name, price, category FROM menu", fetch=True)
        if menu_data:
            df = pd.DataFrame(menu_data, columns=["ID", "Tên", "Giá", "Loại"])
            st.dataframe(df, use_container_width=True)
            del_id = st.number_input("Nhập ID để xóa", min_value=1, step=1)
            if st.button("Xóa món"):
                run_query("DELETE FROM menu WHERE id = ?", (del_id,))
                st.rerun()

