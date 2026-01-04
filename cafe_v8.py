import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- KHỞI TẠO DATABASE ---
def init_db():
    conn = sqlite3.connect('cafe_v8.db')
    c = conn.cursor()
    # Menu món
    c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL)')
    # Đơn hàng đang phục vụ (Chưa thanh toán)
    c.execute('CREATE TABLE IF NOT EXISTS active_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, order_name TEXT, item_name TEXT, price REAL)')
    # Lịch sử doanh thu (Đã thanh toán)
    c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, amount REAL, date TEXT)')
    # Chi phí
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, reason TEXT, cost REAL, date TEXT)')
    conn.commit()
    conn.close()

init_db()

def run_query(query, params=(), fetch=False):
    with sqlite3.connect('cafe_v8.db') as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        if fetch: return c.fetchall()

# --- GIAO DIỆN ---
st.set_page_config(page_title="Cafe v8 - Quản lý Đơn", layout="wide")
st.markdown("<h1 style='text-align: center;'>☕ CAFE PRO v8: QUẢN LÝ ĐƠN HÀNG</h1>", unsafe_allow_width=True)

tab_order, tab_report, tab_expense, tab_menu = st.tabs(["📝 GỌI MÓN/THANH TOÁN", "📈 BÁO CÁO", "💸 CHI PHÍ", "⚙️ CÀI ĐẶT MENU"])

# --- 1. TAB GỌI MÓN & THANH TOÁN ---
with tab_order:
    col_list, col_detail = st.columns([1, 2])

    with col_list:
        st.subheader("Danh sách Đơn")
        new_order = st.text_input("Tên đơn mới (VD: Bàn 5, Đơn 1...)", placeholder="Nhập tên bàn...")
        if st.button("➕ Tạo đơn mới"):
            if new_order:
                # Chỉ tạo tên đơn, chưa có món
                st.toast(f"Đã mở {new_order}")
                st.session_state['current_order'] = new_order
            else:
                st.error("Nhập tên đơn đã mày!")

        # Lấy danh sách các đơn đang có khách
        active_order_names = run_query("SELECT DISTINCT order_name FROM active_orders", fetch=True)
        active_list = [row[0] for row in active_order_names]
        
        if active_list:
            st.write("---")
            selected_order = st.radio("Chọn đơn đang phục vụ:", active_list)
            if selected_order:
                st.session_state['current_order'] = selected_order

    with col_detail:
        if 'current_order' in st.session_state:
            order_name = st.session_state['current_order']
            st.subheader(f"📍 Đang xem: {order_name}")

            # --- PHẦN GỌI MÓN ---
            with st.expander("Thêm món vào đơn này"):
                menu_items = run_query("SELECT name, price FROM menu", fetch=True)
                cols = st.columns(3)
                for i, (name, price) in enumerate(menu_items):
                    if cols[i % 3].button(f"{name}\n{price:,.0f}", key=f"btn_{name}_{i}"):
                        run_query("INSERT INTO active_orders (order_name, item_name, price) VALUES (?,?,?)", (order_name, name, price))
                        st.rerun()

            # --- DANH SÁCH MÓN ĐÃ GỌI ---
            st.write("**Chi tiết đơn hàng:**")
            current_items = run_query("SELECT id, item_name, price FROM active_orders WHERE order_name = ?", (order_name,), fetch=True)
            if current_items:
                df_order = pd.DataFrame(current_items, columns=["ID", "Món", "Giá"])
                st.table(df_order[["Món", "Giá"]])
                total_order = df_order["Giá"].sum()
                st.markdown(f"### 💰 Tổng cộng: {total_order:,.0f} VNĐ")

                # --- THANH TOÁN ---
                c1, c2 = st.columns(2)
                if c1.button("✅ THANH TOÁN (Chốt đơn)", use_container_width=True, type="primary"):
                    # Chuyển vào bảng Sales
                    for _, item, price in current_items:
                        run_query("INSERT INTO sales (item, amount, date) VALUES (?,?,?)", (item, price, datetime.now().strftime("%d/%m %H:%M")))
                    # Xóa khỏi đơn đang phục vụ
                    run_query("DELETE FROM active_orders WHERE order_name = ?", (order_name,))
                    st.success(f"Đã thanh toán {order_name}! Tiền đã vào túi.")
                    del st.session_state['current_order']
                    st.rerun()
                
                if c2.button("❌ Hủy toàn bộ đơn", use_container_width=True):
                    run_query("DELETE FROM active_orders WHERE order_name = ?", (order_name,))
                    del st.session_state['current_order']
                    st.rerun()
            else:
                st.info("Đơn này chưa có món nào. Bấm 'Thêm món' ở trên nhé.")

# --- 2. BÁO CÁO ---
with tab_report:
    st.header("Kết quả kinh doanh")
    rev = run_query("SELECT SUM(amount) FROM sales", fetch=True)[0][0] or 0
    exp = run_query("SELECT SUM(cost) FROM expenses", fetch=True)[0][0] or 0
    st.metric("Lợi nhuận hiện tại", f"{rev-exp:,.0f} VNĐ", delta=f"Doanh thu: {rev:,.0f}")
    
    if st.button("🗑 Reset toàn bộ báo cáo"):
        run_query("DELETE FROM sales")
        run_query("DELETE FROM expenses")
        st.rerun()

# --- 3. CHI PHÍ ---
with tab_expense:
    st.header("Nhập chi phí")
    reason = st.text_input("Nội dung mua hàng")
    cost = st.number_input("Số tiền", min_value=0, step=1000)
    if st.button("Lưu chi"):
        run_query("INSERT INTO expenses (reason, cost, date) VALUES (?,?,?)", (reason, cost, datetime.now().strftime("%d/%m")))
        st.success("Đã lưu!")

# --- 4. CÀI ĐẶT MENU ---
with tab_menu:
    st.header("Quản lý Menu")
    name = st.text_input("Tên món mới")
    price = st.number_input("Giá", min_value=0, step=1000)
    if st.button("Thêm món vào Menu"):
        run_query("INSERT INTO menu (name, price) VALUES (?,?)", (name, price))
        st.rerun()
    
    st.write("---")
    menu_data = run_query("SELECT id, name, price FROM menu", fetch=True)
    if menu_data:
        df_menu = pd.DataFrame(menu_data, columns=["ID", "Tên món", "Giá"])
        st.dataframe(df_menu, use_container_width=True)
        del_id = st.number_input("Nhập ID món muốn xóa", min_value=1, step=1)
        if st.button("Xóa món"):
            run_query("DELETE FROM menu WHERE id = ?", (del_id,))
            st.rerun()
