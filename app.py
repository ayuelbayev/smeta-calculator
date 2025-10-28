import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Смета по прайсу", page_icon="📘", layout="wide")

st.title("📘 Смета по прайсу")

# --- Загрузка прайса ---
uploaded_file = st.file_uploader("Загрузите прайс-лист (price_list_processed.csv)", type="csv")

if uploaded_file:
    price_df = pd.read_csv(uploaded_file)
    price_df['примечание'] = price_df['примечание'].fillna('')
    price_df['наименование'] = price_df['наименование'].str.strip()
    price_df['примечание'] = price_df['примечание'].str.strip()

    price_df['ключ_поиска'] = price_df.apply(
        lambda r: f"{r['наименование']} | {r['примечание']}" if r['примечание'] else r['наименование'], axis=1
    )

    price_lookup = price_df.set_index('ключ_поиска')['цена'].to_dict()
    unit_lookup = price_df.set_index('ключ_поиска')['ед изм'].to_dict()

    st.success("✅ Прайс-лист успешно загружен!")

    # --- Ввод позиций ---
    st.subheader("Добавьте позиции для расчета")

    num_rows = st.number_input("Количество позиций", 1, 30, 3)

    order_data = []
    for i in range(num_rows):
        st.markdown(f"### Позиция {i+1}")
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
        name = col1.selectbox(f"Наименование {i+1}", list(price_lookup.keys()), key=f"name_{i}")
        typ = col2.selectbox("Тип", ["шт", "м/п", "кв/м"], key=f"type_{i}")
        width = col3.number_input("Ширина", value=0.0, key=f"width_{i}")
        height = col4.number_input("Высота", value=0.0, key=f"height_{i}")
        qty = col5.number_input("Количество", value=0.0, key=f"qty_{i}")

        order_data.append({
            "наименование": name,
            "тип": typ,
            "ширина": width,
            "высота": height,
            "количество": qty
        })

    markup = st.number_input("Наценка (%)", value=11.0, min_value=0.0)

    if st.button("🧮 Рассчитать"):
        MARKUP_PERCENTAGE = markup / 100
        receipt_items = []
        total_base_cost = 0

        for item in order_data:
            item_name_key = item["наименование"]
            item_type = item["тип"]
            price = price_lookup.get(item_name_key)
            unit = unit_lookup.get(item_name_key, 'шт')

            if price is None:
                st.error(f"❌ Не найдена позиция: {item_name_key}")
                continue

            if item_type == "кв/м":
                quantity = item["ширина"] * item["высота"]
            else:
                quantity = item["количество"]

            if quantity == 0:
                st.warning(f"⚠ Не указано количество для: {item_name_key}")
                continue

            base_cost = price * quantity
            final_cost = base_cost * (1 + MARKUP_PERCENTAGE)
            total_base_cost += base_cost

            receipt_items.append({
                "Наименование": item_name_key,
                "Кол-во": f"{quantity:.2f} {unit}",
                "Цена": price,
                "Сумма": base_cost,
                "Итого (с наценкой)": final_cost
            })

        if receipt_items:
            df_result = pd.DataFrame(receipt_items)
            total_final_cost = total_base_cost * (1 + MARKUP_PERCENTAGE)

            st.subheader("📋 Готовая смета")
            st.dataframe(df_result, use_container_width=True)

            st.markdown(f"**Базовая сумма:** {total_base_cost:,.0f} ₸")
            st.markdown(f"**Итого (с наценкой {markup:.0f}%):** {total_final_cost:,.0f} ₸")

            # --- Кнопка для скачивания Excel ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_result.to_excel(writer, index=False, sheet_name="Смета")
                summary_df = pd.DataFrame({
                    "Показатель": ["Базовая сумма", f"Итого (с наценкой {markup:.0f}%)"],
                    "Сумма": [total_base_cost, total_final_cost]
                })
                summary_df.to_excel(writer, index=False, sheet_name="Итог", startrow=2)
            st.download_button(
                label="💾 Скачать смету в Excel",
                data=buffer.getvalue(),
                file_name="smeta.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("👆 Загрузите прайс-лист, чтобы начать расчет.")
