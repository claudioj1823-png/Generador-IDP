import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Generador de IDP", layout="wide")

# Control de Acceso
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.subheader("Acceso - Generador de IDP & Materiales")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if usuario == "admin" and password == "proyectos2026":
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
    st.stop()

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
    
    if not df_c.empty:
        col_desc = [c for c in df_c.columns if 'descripci' in c.lower()][0]
        mapeo = df_c[['Actividad', col_desc]].drop_duplicates().set_index('Actividad')[col_desc].to_dict()
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
                "Contratista": contrata_sel,
                "Actividad": act_sel,
                "Descripción": desc_act,
                "Cantidad": cant_sel
            })
            st.success("¡Actividad añadida con éxito!")
            
        if st.session_state.lista_idp:
            st.subheader("Resumen del IDP Actual (Actividades)")
            df_idp = pd.DataFrame(st.session_state.lista_idp)
            st.dataframe(df_idp, use_container_width=True)
            
            st.subheader("Requerimiento de Materiales y Montos")
            # Filtrar filas del Excel para las actividades agregadas y calcular materiales
            actividades_agregadas = {item["Actividad"]: item["Cantidad"] for item in st.session_state.lista_idp}
            
            df_filtrado = df_c[df_c['Actividad'].isin(actividades_agregadas.keys())].copy()
            
            if not df_filtrado.empty:
                # Multiplicar cantidad unitaria por la cantidad de la actividad seleccionada
                # Buscamos columnas de cantidad y precio de materiales si existen en el Excel
                col_cant_mat = [c for c in df_filtrado.columns if 'cant' in c.lower() and c.lower() != 'cantidad']
                col_precio = [c for c in df_filtrado.columns if 'precio' in c.lower() or 'costo' in c.lower()]
                
                # Mapeamos la cantidad multiplicadora del IDP
                df_filtrado['Cant_IDP'] = df_filtrado['Actividad'].map(actividades_agregadas)
                
                st.dataframe(df_filtrado, use_container_width=True)
            else:
                st.info("No hay materiales asociados a las actividades seleccionadas.")
            
            if st.button("Limpiar IDP"):
                st.session_state.lista_idp = []
                st.rerun()
