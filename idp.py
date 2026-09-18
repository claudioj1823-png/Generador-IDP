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
            st.subheader("Resumen del IDP Actual (Estructuras / Actividades)")
            df_idp = pd.DataFrame(st.session_state.lista_idp)
            
            # Obtener precio unitario de las estructuras para calcular su monto asegurando tipo numérico
            cols_precio = [c for c in df_c.columns if 'precio' in c.lower() or 'costo' in c.lower()]
            if cols_precio:
                c_precio = cols_precio[0]
                precios_dict = df_c[['Actividad', c_precio]].drop_duplicates().set_index('Actividad')[c_precio].to_dict()
                df_idp['Precio Unitario'] = pd.to_numeric(df_idp['Actividad'].map(precios_dict), errors='coerce')
                df_idp['Monto Total'] = df_idp['Precio Unitario'] * pd.to_numeric(df_idp['Cantidad'], errors='coerce')
            
            # Formatear valores monetarios y preparar dataframe sin índice
            df_idp_show = df_idp.copy()
            df_idp_show['Precio Unitario'] = df_idp_show['Precio Unitario'].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00")
            df_idp_show['Monto Total'] = df_idp_show['Monto Total'].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00")
            
            # Renderizar tabla superior con diseño personalizado (Sin columna de índice)
            html_est = df_idp_show.to_html(classes='custom-table', escape=False, index=False)
            st.html(f"""
                <style>
                .custom-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-family: sans-serif;
                    font-size: 14px;
                    background-color: white;
                    margin-bottom: 15px;
                }}
                .custom-table th {{
                    background-color: #0b2545 !important;
                    color: white !important;
                    text-align: left;
                    padding: 12px;
                    font-weight: bold;
                    border: 1px solid #0b2545;
                }}
                .custom-table td {{
                    padding: 10px 12px;
                    border-bottom: 1px solid #e0e0e0;
                    color: #31333F;
                }}
                .custom-table tr:hover {{
                    background-color: #f8f9fa;
                }}
                </style>
                {html_est}
            """)
            
            # Opción para eliminar una estructura específica por su número de fila
            col_del1, col_del2 = st.columns([2, 1])
            with col_del1:
                # Opciones basadas en el número de fila visible (1 a N)
                opciones_filas = list(range(1, len(df_idp) + 1))
                fila_a_borrar = st.selectbox("Selecciona el número de fila de la estructura a eliminar:", options=opciones_filas)
            with col_del2:
                st.write("") 
                if st.button("Eliminar Fila Seleccionada"):
                    st.session_state.lista_idp.pop(fila_a_borrar - 1)
                    st.success(f"Fila {fila_a_borrar} eliminada correctamente.")
                    st.rerun()

            if cols_precio:
                total_estructuras = df_idp['Monto Total'].sum()
                st.metric(label="Monto Total de Estructuras / Actividades", value=f"${total_estructuras:,.2f}")
            
            st.subheader("Requerimiento Consolidado de Materiales")
            
            # Consolidar cantidades del IDP por actividad para los materiales
            df_idp_agrupado = df_idp.groupby("Actividad")["Cantidad"].sum().to_dict()
            df_filtrado = df_c[df_c['Actividad'].isin(df_idp_agrupado.keys())].copy()
            
            if not df_filtrado.empty:
                df_filtrado['Cant_IDP'] = df_filtrado['Actividad'].map(df_idp_agrupado)
                col_cant_mat = [c for c in df_filtrado.columns if 'cant' in c.lower() and c.lower() != 'cantidad' and c.lower() != 'cant_idp']
                
                if col_cant_mat:
                    c_mat = col_cant_mat[0]
                    df_filtrado['Cantidad_Total'] = df_filtrado[c_mat] * df_filtrado['Cant_IDP']
                    
                    # Identificar columnas clave para agrupar materiales sin repetirse
                    cols_cod = [c for c in df_filtrado.columns if 'sap' in c.lower() or 'codigo' in c.lower()]
                    cols_desc_mat = [c for c in df_filtrado.columns if 'mat' in c.lower() or 'descripci_mat' in c.lower() or (c.lower() != 'descripción de la actividad' and 'descripci' in c.lower())]
                    cols_und = [c for c in df_filtrado.columns if 'unid' in c.lower()]
                    
                    cod_col = cols_cod[0] if cols_cod else df_filtrado.columns[0]
                    desc_mat_col = cols_desc_mat[0] if cols_desc_mat else cod_col
                    und_col = cols_und[0] if cols_und else None
                    
                    columnas_agrupacion = [cod_col, desc_mat_col]
                    if und_col:
                        columnas_agrupacion.append(und_col)
                        
                    agregaciones = {'Cantidad_Total': 'sum'}
                    df_resumen = df_filtrado.groupby(columnas_agrupacion, as_index=False).agg(agregaciones)
                    
                    # Limpiar código SAP y quitar decimales en la Cantidad Total convirtiéndola a entero
                    df_resumen[cod_col] = df_resumen[cod_col].astype(str).str.replace(r'\.0$', '', regex=True)
                    df_resumen['Cantidad_Total'] = pd.to_numeric(df_resumen['Cantidad_Total'], errors='coerce').fillna(0).astype(int)
                    
                    renombres = {
                        cod_col: "Código SAP",
                        desc_mat_col: "Descripción de Material",
                        'Cantidad_Total': "Cantidad Total"
                    }
                    if und_col:
                        renombres[und_col] = "Unidad"
                    
                    df_resumen = df_resumen.rename(columns=renombres)
                    
                    # Renderizar tabla inferior con diseño personalizado (Sin columna de índice)
                    html_mat = df_resumen.to_html(classes='custom-table', escape=False, index=False)
                    st.html(f"""
                        {html_mat}
                    """)
                else:
                    st.dataframe(df_filtrado, use_container_width=True)
            else:
                st.info("No hay materiales asociados a las actividades seleccionadas.")
            
            if st.button("Limpiar Todo el IDP"):
                st.session_state.lista_idp = []
                st.rerun()
