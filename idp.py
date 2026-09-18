import pandas as pd
import streamlit as st
import os

# --- AUTENTICACIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def verificar_credenciales(usuario, password):
    return usuario == "admin" and password == "proyectos2026"

if not st.session_state.autenticado:
    st.title("Acceso - Generador de IDP & Materiales")
    with st.form("login_idp"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            if verificar_credenciales(u, p):
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")
    st.stop()

# --- APLICACIÓN PRINCIPAL IDP ---
st.title("Generador de IDP (Informe Diario de Producción)")
st.write("Calcula montos por contratista y materiales excluyendo actividades sin insumos de almacén.")

@st.cache_data
def cargar_datos():
    try:
        ruta = os.path.join(os.path.dirname(__file__), "Actividades contratistas.xlsx")
        df = pd.read_excel(ruta, sheet_name="Actividades con materiales")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error al cargar el Excel: {e}")
        return None

df = cargar_datos()

if df is not None:
    if 'lista_idp' not in st.session_state:
        st.session_state.lista_idp = []

    df['Actividad'] = df['Actividad'].fillna('').astype(str).str.strip()
    df['Contrata'] = df['Contrata'].fillna('').astype(str).str.strip()

    # Seleccionar Contratista
    contratas = sorted([c for c in df['Contrata'].unique() if c and c.lower() != 'nan'])
    contrata_sel = st.selectbox("Selecciona la Compañía Contratista:", contratas)

    df_c = df[df['Contrata'].str.lower() == contrata_sel.lower()]
    
    # Mapeo de actividades
    mapeo = df_c[['Actividad', 'Descripción de la actividad ']].drop_duplicates().set_index('Actividad')['Descripción de la actividad '].to_dict()
    opciones = sorted(list(mapeo.keys()))

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        act_sel = st.selectbox("Unidad Constructiva (UU.TT.):", opciones)
    with col2:
        desc_act = mapeo.get(act_sel, "")
        st.write(f"**Desc:** {desc_act}")
    with col3:
        cant_sel = st.number_input("Cantidad:", min_value=1, value=1)

    if st.button("Añadir al IDP"):
        st.session_state.lista_idp.append({
            "Contrata": contrata_sel,
            "Actividad": act_sel,
            "Descripcion": desc_act,
            "Cantidad": cant_sel
        })

    if st.session_state.lista_idp:
        st.write("### 📝 Actividades en el IDP actual:")
        for idx, item in enumerate(st.session_state.lista_idp):
            st.write(f"{idx+1}. **{item['Actividad']}** (Cant: {item['Cantidad']}) - {item['Descripcion']}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Limpiar IDP"):
                st.session_state.lista_idp = []
                st.rerun()
        with c2:
            if st.button("Cerrar Sesión"):
                st.session_state.autenticado = False
                st.session_state.lista_idp = []
                st.rerun()

        st.markdown("---")
        if st.button("🧮 Calcular Montos y Materiales del IDP", type="primary"):
            montos = []
            materiales = []

            for item in st.session_state.lista_idp:
                match = df_c[df_c['Actividad'].str.lower() == item["Actividad"].lower()]
                if not match.empty:
                    try:
                        precio_u = float(match.iloc[0].get("Precio Actividad", 0))
                    except:
                        precio_u = 0.0
                    
                    total_u = precio_u * item["Cantidad"]
                    
                    montos.append({
                        "Unidad Constructiva": item["Actividad"],
                        "Descripción": item["Descripcion"],
                        "Cantidad": item["Cantidad"],
                        "Precio Unitario": precio_u,
                        "Monto Total": total_u
                    })

                    # Procesar materiales (omitiendo vacíos/excavaciones)
                    for _, row in match.iterrows():
                        sap = row.get("Codigo SAP", None)
                        if pd.notna(sap) and str(sap).strip() != "":
                            try:
                                c_base = float(row.get("Cantidad Materiales", 1))
                            except:
                                c_base = 1.0
                            
                            materiales.append({
                                "Código SAP": str(sap).split(".")[0],
                                "Descripción Material": row.get("Descripción_MAT", ""),
                                "Unidad": row.get("Unidad", ""),
                                "Cantidad Total": c_base * item["Cantidad"]
                            })

            st.success("¡Cálculo de IDP realizado con éxito!")
            
            st.subheader("💰 Resumen Financiero (Cubicación)")
            df_m = pd.DataFrame(montos)
            st.dataframe(df_m, use_container_width=True)
            st.markdown(f"### **Monto Total a Cobrar: RD$ {df_m['Monto Total'].sum():,.2f}**")

            if materiales:
                st.subheader("📦 Materiales de Almacén Requeridos")
                df_mat = pd.DataFrame(materiales)
                df_mat_final = df_mat.groupby(["Código SAP", "Descripción Material", "Unidad"], as_index=False)["Cantidad Total"].sum()
                st.dataframe(df_mat_final, use_container_width=True)
            else:
                st.info("Este grupo de actividades no requiere salida de materiales de almacén.")
else:
    st.warning("No se encontró el archivo 'Actividades contratistas.xlsx'.")
