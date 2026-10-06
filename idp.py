import io
import os
import pandas as pd
import streamlit as st

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
st.write(
    "Calcula montos por contratista, proyecto y materiales excluyendo"
    " actividades sin insumos de almacén."
)


# --- CARGAR LISTADO DE PROYECTOS DESDE EL EXCEL EXTERNO ---
@st.cache_data
def cargar_proyectos():
    ruta_proj = os.path.join(
        os.path.dirname(__file__), "Codigos de proyectos.xlsx"
    )
    try:
        df_proj = pd.read_excel(ruta_proj, header=0)
        df_proj = df_proj.dropna(subset=[df_proj.columns[0]])
        codigos = df_proj.iloc[:, 0].astype(str).str.strip()
        nombres = df_proj.iloc[:, 1].astype(str).str.strip()
        dict_proj = dict(zip(codigos, nombres))
        return dict_proj
    except Exception as e:
        return {"O-RP-24-368": f"Error al cargar proyectos: {e}"}


dict_proyectos = cargar_proyectos()


@st.cache_data
def cargar_datos():
    try:
        ruta = os.path.join(os.path.dirname(__file__), "Actividades contratistas.xlsx")
        df = pd.read_excel(ruta, sheet_name="Actividades con materiales")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error al cargar el Excel de actividades: {e}")
        return None


df = cargar_datos()

if df is not None:
    if "lista_idp" not in st.session_state:
        st.session_state.lista_idp = []

    df["Actividad"] = df["Actividad"].fillna("").astype(str).str.strip()
    df["Contrata"] = df["Contrata"].fillna("").astype(str).str.strip()

    # --- CABECERA SUPERIOR (Contratista, IDP numérico, Fecha y Proyecto) ---
    col_cont, col_idp_num, col_fecha, col_proj = st.columns([2, 1.2, 1.5, 2.5])

    with col_cont:
        contratas_puras = sorted(
            [c for c in df["Contrata"].unique() if c and c.lower() != "nan"]
        )
        opciones_contrata_menu = ["-- Seleccione la contrata --"] + contratas_puras
        contrata_sel_menu = st.selectbox(
            "Selecciona la Compañía Contratista:", opciones_contrata_menu
        )
        
        if contrata_sel_menu != "-- Seleccione la contrata --":
            contrata_sel = contrata_sel_menu
        else:
            contrata_sel = None

    with col_idp_num:
        idp_numero = st.number_input("IDP N°:", min_value=1, value=1, step=1)

    with col_fecha:
        fecha_idp = st.date_input("Fecha:")

    with col_proj:
        lista_codigos = list(dict_proyectos.keys())
        opciones_proyecto_menu = ["-- Seleccione el proyecto --"] + lista_codigos
        proyecto_sel_menu = st.selectbox("Código de Proyecto:", opciones_proyecto_menu)
        
        if proyecto_sel_menu != "-- Seleccione el proyecto --":
            codigo_proyecto_sel = proyecto_sel_menu
        else:
            codigo_proyecto_sel = None

    if contrata_sel and codigo_proyecto_sel:
        nombre_proyecto_sel = dict_proyectos.get(
            codigo_proyecto_sel, "Proyecto No Encontrado"
        )
        st.info(
            f"**Contratista:** {contrata_sel}  |  **Proyecto Seleccionado:** {nombre_proyecto_sel}  |  **IDP N°:** {idp_numero}  |  **Fecha:** {fecha_idp}"
        )
    else:
        st.info("💡 **Por favor, seleccione tanto la Compañía Contratista como el Código de Proyecto arriba para continuar.**")

    st.markdown("---")

    if contrata_sel and codigo_proyecto_sel:
        df_c = df[df["Contrata"].str.lower() == contrata_sel.lower()]

        if not df_c.empty:
            col_desc = [c for c in df_c.columns if "descripci" in c.lower()][0]
            mapeo = (
                df_c[["Actividad", col_desc]]
                .drop_duplicates()
                .set_index("Actividad")[col_desc]
                .to_dict()
            )
            opciones = sorted(list(mapeo.keys()))

            col1, col2 = st.columns([4, 2])
            with col1:
                act_sel = st.selectbox("Unidad Constructiva (UU.TT.):", opciones)
            with col2:
                cant_sel = st.number_input("Cantidad:", min_value=1, value=1)

            desc_act = mapeo.get(act_sel, "")

            if st.button("Añadir al IDP"):
                st.session_state.lista_idp.append({
                    "IDP N°": idp_numero,
                    "Fecha": str(fecha_idp),
                    "Código Proyecto": codigo_proyecto_sel,
                    "Contratista": contrata_sel,
                    "Actividad": act_sel,
                    "Descripción": desc_act,
                    "Cantidad": cant_sel,
                })
                st.success("¡Actividad añadida con éxito!")

            if st.session_state.lista_idp:
                st.subheader("Resumen del IDP Actual (Estructuras / Actividades)")
                df_idp = pd.DataFrame(st.session_state.lista_idp)

                cols_precio = [
                    c
                    for c in df_c.columns
                    if "precio" in c.lower() or "costo" in c.lower()
                ]
                if cols_precio:
                    c_precio = cols_precio[0]
                    precios_dict = (
                        df_c[["Actividad", c_precio]]
                        .drop_duplicates()
                        .set_index("Actividad")[c_precio]
                        .to_dict()
                    )
                    df_idp["Precio Unitario"] = pd.to_numeric(
                        df_idp["Actividad"].map(precios_dict), errors="coerce"
                    )
                    df_idp["Monto Total"] = df_idp["Precio Unitario"] * pd.to_numeric(
                        df_idp["Cantidad"], errors="coerce"
                    )

                df_idp_show = df_idp[
                    ["Actividad", "Descripción", "Cantidad", "Precio Unitario", "Monto Total"]
                ].copy()

                df_idp_show["Precio Unitario"] = df_idp_show["Precio Unitario"].map(
                    lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                )
                df_idp_show["Monto Total"] = df_idp_show["Monto Total"].map(
                    lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                )

                html_est = df_idp_show.to_html(
                    classes="custom-table", escape=False, index=False
                )
                st.html(f"""
                    <style>
                    .custom-table {{
                        width: 100%;
                        border-collapse: collapse;
                        font-family: sans-serif;
                        font-size: 14px;
                        background-color: white !important;
                        margin-bottom: 15px;
                    }}
                    .custom-table th {{
                        padding: 10px 12px;
                        border-bottom: 1px solid #e0e0e0;
                        text-align: left;
                        background-color: #0b2545 !important;
                        color: white !important;
                        font-weight: bold;
                        border: 1px solid #0b2545;
                    }}
                    .custom-table td {{
                        padding: 10px 12px;
                        border-bottom: 1px solid #e0e0e0;
                        text-align: left;
                        background-color: white !important;
                        color: #111111 !important;
                    }}
                    .custom-table tr:hover td {{
                        background-color: #f8f9fa !important;
                    }}
                    </style>
                    {html_est}
                """)

                col_del1, col_del2 = st.columns([2, 1])
                with col_del1:
                    opciones_filas = list(range(1, len(df_idp) + 1))
                    fila_a_borrar = st.selectbox(
                        "Selecciona el número de fila de la estructura a eliminar:",
                        options=opciones_filas,
                    )
                with col_del2:
                    st.write("")
                    if st.button("Eliminar Fila Seleccionada"):
                        st.session_state.lista_idp.pop(fila_a_borrar - 1)
                        st.success(f"Fila {fila_a_borrar} eliminada correctamente.")
                        st.rerun()

                if cols_precio:
                    total_estructuras = df_idp["Monto Total"].sum()
                    st.metric(
                        label="Monto Total de Estructuras / Actividades",
                        value=f"${total_estructuras:,.2f}",
                    )

                st.subheader("Requerimiento Consolidado de Materiales")

                df_idp_agrupado = df_idp.groupby("Actividad")["Cantidad"].sum().to_dict()
                df_filtrado = df_c[
                    df_c["Actividad"].isin(df_idp_agrupado.keys())
                ].copy()

                df_resumen = pd.DataFrame()
                if not df_filtrado.empty:
                    df_filtrado["Cant_IDP"] = df_filtrado["Actividad"].map(df_idp_agrupado)
                    col_cant_mat = [
                        c
                        for c in df_filtrado.columns
                        if "cant" in c.lower()
                        and c.lower() != "cantidad"
                        and c.lower() != "cant_idp"
                    ]

                    if col_cant_mat:
                        c_mat = col_cant_mat[0]
                        df_filtrado["Cantidad_Total"] = (
                            df_filtrado[c_mat] * df_filtrado["Cant_IDP"]
                        )

                        cols_cod = [
                            c
                            for c in df_filtrado.columns
                            if "sap" in c.lower() or "codigo" in c.lower()
                        ]
                        cols_desc_mat = [
                            c
                            for c in df_filtrado.columns
                            if "mat" in c.lower()
                            or "descripci_mat" in c.lower()
                            or (
                                c.lower() != "descripción de la actividad"
                                and "descripci" in c.lower()
                            )
                        ]
                        cols_und = [c for c in df_filtrado.columns if "unid" in c.lower()]

                        cod_col = (
                            cols_cod[0] if cols_cod else df_filtrado.columns[0]
                        )
                        desc_mat_col = cols_desc_mat[0] if cols_desc_mat else cod_col
                        und_col = cols_und[0] if cols_und else None

                        columnas_agrupacion = [cod_col, desc_mat_col]
                        if und_col:
                            columnas_agrupacion.append(und_col)

                        agregaciones = {"Cantidad_Total": "sum"}
                        df_resumen = df_filtrado.groupby(
                            columnas_agrupacion, as_index=False
                        ).agg(agregaciones)

                        df_resumen[cod_col] = (
                            df_resumen[cod_col].astype(str).str.replace(r"\.0$", "", regex=True)
                        )
                        df_resumen["Cantidad_Total"] = (
                            pd.to_numeric(df_resumen["Cantidad_Total"], errors="coerce")
                            .fillna(0)
                            .astype(int)
                        )

                        renombres = {
                            cod_col: "Código SAP",
                            desc_mat_col: "Descripción de Material",
                            "Cantidad_Total": "Cantidad Total",
                        }
                        if und_col:
                            renombres[und_col] = "Unidad"

                        df_resumen = df_resumen.rename(columns=renombres)

                        html_mat = df_resumen.to_html(
                            classes="custom-table-mat", escape=False, index=False
                        )
                        st.html(f"""
                                    <style>
                                    .custom-table-mat {{
                                        width: 100%;
                                        border-collapse: collapse;
                                        font-family: sans-serif;
                                        font-size: 14px;
                                        background-color: white !important;
                                        margin-bottom: 15px;
                                    }}
                                    .custom-table-mat th {{
                                        padding: 10px 12px;
                                        border-bottom: 1px solid #e0e0e0;
                                        text-align: left;
                                        background-color: #0b2545 !important;
                                        color: white !important;
                                        font-weight: bold;
                                        border: 1px solid #0b2545;
                                    }}
                                    .custom-table-mat td {{
                                        padding: 10px 12px;
                                        border-bottom: 1px solid #e0e0e0;
                                        text-align: left;
                                        background-color: white !important;
                                        color: #111111 !important;
                                    }}
                                    .custom-table-mat tr:hover td {{
                                        background-color: #f8f9fa !important;
                                    }}
                                    </style>
                                    {html_mat}
                                """)
                    else:
                        st.dataframe(df_filtrado, use_container_width=True)
                else:
                    st.info("No hay materiales asociados a las actividades seleccionadas.")

                st.markdown("---")
                st.subheader("Exportar Resultados y Registro Histórico")

                col_exp1, col_exp2 = st.columns([1, 1])

                with col_exp1:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        df_idp.to_excel(
                            writer, sheet_name="Estructuras_Actividades", index=False
                        )
                        if not df_resumen.empty:
                            df_resumen.to_excel(
                                writer, sheet_name="Requerimiento_Materiales", index=False
                            )
                    output.seek(0)

                    st.download_button(
                        label="📥 Descargar IDP Completo en Excel",
                        data=output,
                        file_name=f"IDP_{idp_numero}_{contrata_sel.replace(' ', '_')}.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        ),
                    )

                with col_exp2:
                    if st.button("💾 Guardar IDP en el Historial General"):
                        archivo_historial = "historial_idp_general.csv"
                        try:
                            df_guardar = df_idp.copy()
                            
                            if "Monto Total" not in df_guardar.columns and cols_precio:
                                df_guardar["Monto Total"] = df_guardar["Precio Unitario"] * pd.to_numeric(df_guardar["Cantidad"], errors="coerce")

                            df_guardar["Fecha"] = str(fecha_idp)
                            df_guardar["Código Proyecto"] = codigo_proyecto_sel
                            df_guardar["Nombre Proyecto"] = nombre_proyecto_sel
                            df_guardar["Contratista"] = contrata_sel

                            cols_frente = ["IDP N°", "Fecha", "Código Proyecto", "Nombre Proyecto", "Contratista"]
                            otras_cols = [c for c in df_guardar.columns if c not in cols_frente]
                            df_guardar = df_guardar[cols_frente + otras_cols]

                            if os.path.exists(archivo_historial):
                                df_guardar.to_csv(
                                    archivo_historial, mode="a", header=False, index=False
                                )
                            else:
                                df_guardar.to_csv(archivo_historial, index=False)

                            st.success(
                                "¡IDP guardado exitosamente en el historial general de la aplicación!"
                            )
                        except Exception as e:
                            st.error(f"Error al guardar en el historial: {e}")

                archivo_historial = "historial_idp_general.csv"
                if os.path.exists(archivo_historial):
                    with st.expander("📂 Ver / Consultar Historial Consolidado de IDP"):
                        try:
                            df_hist = pd.read_csv(archivo_historial)
                            st.dataframe(df_hist, use_container_width=True)

                            csv_hist = df_hist.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="📥 Descargar Todo el Historial en CSV",
                                data=csv_hist,
                                file_name="Historial_Consolidado_IDP.csv",
                                mime="text/csv",
                            )
                        except Exception as e:
                            st.warning("No se pudo leer el archivo de historial aún.")

                st.markdown("---")
                if st.button("Limpiar Todo el IDP Actual"):
                    st.session_state.lista_idp = []
                    st.rerun()

# ==========================================
# SECCIÓN: CONSULTA RÁPIDA POR PROYECTO & MODIFICAR MANO DE OBRA
# ==========================================
st.markdown("---")
st.subheader("🔍 Consultar Historial Consolidado por Proyecto")

archivo_historial = "historial_idp_general.csv"

# Actualizado para aceptar archivos Excel (.xlsx) y CSV
archivo_subido = st.file_uploader("📂 (Opcional) Subir respaldo anterior de Historial (Excel o CSV)", type=["xlsx", "csv"])
if archivo_subido is not None:
    try:
        if archivo_subido.name.endswith('.xlsx'):
            df_subido = pd.read_excel(archivo_subido, sheet_name="Historial_Estructuras")
        else:
            df_subido = pd.read_csv(archivo_subido)
            
        df_subido.to_csv(archivo_historial, index=False)
        st.success("¡Historial restaurado exitosamente desde tu archivo de respaldo!")
        st.rerun()
    except Exception as e:
        st.error(f"No se pudo cargar el archivo subido: {e}")

if os.path.exists(archivo_historial):
    try:
        df_hist_total = pd.read_csv(archivo_historial)
        
        cols_p_excel = [c for c in df.columns if "precio" in c.lower() or "costo" in c.lower()]
        if cols_p_excel:
            col_p_nom = cols_p_excel[0]
            dict_tarifas_maestro = {}
            for _, r_t in df.iterrows():
                c_cont_m = str(r_t.get("Contrata", "")).strip().lower()
                c_act_m = str(r_t.get("Actividad", "")).strip().lower()
                val_pr = pd.to_numeric(str(r_t.get(col_p_nom, 0)).replace("$", "").replace(",", ""), errors="coerce") or 0.0
                dict_tarifas_maestro[(c_cont_m, c_act_m)] = val_pr

            precios_reparados = []
            for _, row_h in df_hist_total.iterrows():
                act_val = str(row_h.get("Actividad", row_h.get("Código", ""))).strip().lower()
                cont_val = str(row_h.get("Contratista", row_h.get("Contrata", ""))).strip().lower()
                
                p_actual_raw = row_h.get("Precio Unitario", row_h.get("Costo Unitario", 0))
                p_actual = pd.to_numeric(str(p_actual_raw).replace("$", "").replace(",", ""), errors="coerce") or 0.0
                
                if p_actual == 0.0:
                    p_actual = dict_tarifas_maestro.get((cont_val, act_val), 0.0)
                
                precios_reparados.append(p_actual)
            
            df_hist_total["Precio Unitario"] = precios_reparados
        else:
            df_hist_total["Precio Unitario"] = 0.0

        if "Cantidad" in df_hist_total.columns:
            df_hist_total["Cantidad"] = pd.to_numeric(df_hist_total["Cantidad"], errors="coerce").fillna(0)
        else:
            df_hist_total["Cantidad"] = 0.0

        df_hist_total["Monto Total"] = df_hist_total["Precio Unitario"] * df_hist_total["Cantidad"]

        def formatear_columnas_tabla(df_in):
            df_fmt = df_in.copy()
            renombres_map = {
                "Actividad": "Código",
                "Descripción": "DETALLE",
                "Precio Unitario": "Costo Unitario",
                "Cantidad": "Cantidad",
                "Monto Total": "Costo Total",
                "IDP N°": "IDP",
                "Fecha": "Fec",
                "Contratista": "Contrata",
                "Código Proyecto": "Código Proyecto",
                "Nombre Proyecto": "Nombre Proyecto"
            }
            df_fmt = df_fmt.rename(columns=renombres_map)
            orden_columnas = ["Código", "DETALLE", "Costo Unitario", "Cantidad", "Costo Total", "IDP", "Fec", "Contrata", "Código Proyecto", "Nombre Proyecto"]
            cols_existentes = [c for c in orden_columnas if c in df_fmt.columns]
            otras = [c for c in df_fmt.columns if c not in cols_existentes]
            df_fmt = df_fmt[cols_existentes + otras]
            return df_fmt

        if "Código Proyecto" in df_hist_total.columns:
            proyectos_guardados = df_hist_total["Código Proyecto"].dropna().unique().tolist()
            if proyectos_guardados:
                opciones_menu = ["-- Seleccione el proyecto --"] + proyectos_guardados
                
                proj_seleccionado = st.selectbox(
                    "Selecciona el Código de Proyecto a Consultar en Pantalla:",
                    opciones_menu,
                    key="filtro_proyecto_historial_global"
                )
                
                col_down_gen1, col_down_gen2 = st.columns([2, 2])
                with col_down_gen1:
                    output_todos = io.BytesIO()
                    with pd.ExcelWriter(output_todos, engine="openpyxl") as writer:
                        df_hist_fmt_global = formatear_columnas_tabla(df_hist_total)
                        df_hist_fmt_global.to_excel(writer, sheet_name="Historial_Estructuras", index=False)
                        
                        if not df.empty and "Contratista" in df_hist_total.columns and "Actividad" in df_hist_total.columns and "Cantidad" in df_hist_total.columns:
                            df_all_agrupado = df_hist_total.groupby(["Contratista", "Actividad"])["Cantidad"].sum().reset_index()
                            df_mat_todos_acc = pd.DataFrame()
                            for _, row_g in df_all_agrupado.iterrows():
                                c_contratista = row_g["Contratista"]
                                c_actividad = row_g["Actividad"]
                                c_cant = row_g["Cantidad"]
                                df_match = df[(df["Contrata"].str.lower() == c_contratista.lower()) & (df["Actividad"] == c_actividad)].copy()
                                if not df_match.empty:
                                    df_match["Cant_IDP"] = c_cant
                                    col_cant_mat = [c for c in df_match.columns if "cant" in c.lower() and c.lower() != "cantidad" and c.lower() != "cant_idp"]
                                    if col_cant_mat:
                                        c_mat = col_cant_mat[0]
                                        df_match["Cantidad_Total"] = df_match[c_mat] * df_match["Cant_IDP"]
                                        df_mat_todos_acc = pd.concat([df_mat_todos_acc, df_match], ignore_index=True)
                            
                            if not df_mat_todos_acc.empty:
                                cols_cod = [c for c in df_mat_todos_acc.columns if "sap" in c.lower() or "codigo" in c.lower()]
                                cols_desc_mat = [c for c in df_mat_todos_acc.columns if "mat" in c.lower() or "descripci_mat" in c.lower() or (c.lower() != "descripción de la actividad" and "descripci" in c.lower())]
                                cols_und = [c for c in df_mat_todos_acc.columns if "unid" in c.lower()]

                                cod_col = cols_cod[0] if cols_cod else df_mat_todos_acc.columns[0]
                                desc_mat_col = cols_desc_mat[0] if cols_desc_mat else cod_col
                                und_col = cols_und[0] if cols_und else None

                                cols_agrupar_mat = [cod_col, desc_mat_col]
                                if und_col:
                                    cols_agrupar_mat.append(und_col)

                                df_mat_resumen_all = df_mat_todos_acc.groupby(cols_agrupar_mat, as_index=False).agg({"Cantidad_Total": "sum"})
                                df_mat_resumen_all[cod_col] = df_mat_resumen_all[cod_col].astype(str).str.replace(r"\.0$", "", regex=True)
                                df_mat_resumen_all["Cantidad_Total"] = pd.to_numeric(df_mat_resumen_all["Cantidad_Total"], errors="coerce").fillna(0).astype(int)

                                renombres_mat = {
                                    cod_col: "Código SAP",
                                    desc_mat_col: "Descripción de Material",
                                    "Cantidad_Total": "Cantidad Total"
                                }
                                if und_col:
                                    renombres_mat[und_col] = "Unidad"
                                df_mat_resumen_all = df_mat_resumen_all.rename(columns=renombres_mat)
                                df_mat_resumen_all.to_excel(writer, sheet_name="Requerimiento_Materiales_General", index=False)
                    output_todos.seek(0)

                    st.download_button(
                        label="📥 Descargar Reporte Maestro General (Todos los Proyectos)",
                        data=output_todos,
                        file_name="Reporte_General_Consolidado_IDP.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_descargar_maestro_todos"
                    )

                if proj_seleccionado != "-- Seleccione el proyecto --":
                    df_filtrado_proj = df_hist_total[df_hist_total["Código Proyecto"] == proj_seleccionado].copy()
                    
                    monto_acumulado_proyecto = df_filtrado_proj["Monto Total"].sum()

                    st.metric(
                        label=f"💰 Monto Total Acumulado Pagado en el Proyecto ({proj_seleccionado})",
                        value=f"${monto_acumulado_proyecto:,.2f}"
                    )

                    df_proj_fmt = formatear_columnas_tabla(df_filtrado_proj)
                    cols_a_mostrar_proj = [c for c in df_proj_fmt.columns if c not in ["Código Proyecto", "Nombre Proyecto"]]

                    st.info(f"👷 **Mano de obra proyecto : {proj_seleccionado}**")
                    
                    df_vistas_display = df_proj_fmt[cols_a_mostrar_proj].copy()
                    df_vistas_display["Costo Unitario"] = df_vistas_display["Costo Unitario"].map(lambda x: f"${x:,.2f}")
                    df_vistas_display["Costo Total"] = df_vistas_display["Costo Total"].map(lambda x: f"${x:,.2f}")
                    st.dataframe(df_vistas_display, use_container_width=True)

                    # ==========================================
                    # MODIFICAR MANO DE OBRA CON st.data_editor
                    # ==========================================
                    with st.expander("✏ Modificar mano de obra"):
                        st.info("💡 Haz doble clic sobre cualquier celda de la tabla de abajo para corregir la cantidad, el número de IDP, la fecha, la contrata o el código de proyecto. Al terminar, haz clic en **'Guardar Cambios en el Historial'**.")
                        
                        df_editado_en_pantalla = st.data_editor(
                            df_proj_fmt[cols_a_mostrar_proj + ["Código Proyecto", "Nombre Proyecto"]],
                            use_container_width=True,
                            key=f"editor_{proj_seleccionado}",
                            num_rows="dynamic"
                        )
                        
                        if st.button("💾 Guardar Cambios en el Historial General", key=f"btn_save_editor_{proj_seleccionado}"):
                            try:
                                df_otros_proyectos = df_hist_total[df_hist_total["Código Proyecto"] != proj_seleccionado]
                                
                                df_limpio = df_editado_en_pantalla.copy()
                                
                                # 1. Convertir cantidades a numérico
                                cants_num = pd.to_numeric(df_limpio["Cantidad"], errors="coerce").fillna(0)
                                df_limpio["Cantidad"] = cants_num
                                
                                # 2. Recuperar y recalcular los costos unitarios reales desde el diccionario maestro del Excel
                                costos_actualizados = []
                                for _, row_ed in df_limpio.iterrows():
                                    c_act = str(row_ed.get("Código", "")).strip().lower()
                                    c_cont = str(row_ed.get("Contrata", "")).strip().lower()
                                    
                                    # Buscar precio en el diccionario maestro o respaldo de pantalla
                                    precio_encontrado = dict_tarifas_maestro.get((c_cont, c_act), 0.0)
                                    if precio_encontrado == 0.0:
                                        val_pantalla = str(row_ed.get("Costo Unitario", "0")).replace("$", "").replace(",", "")
                                        precio_encontrado = pd.to_numeric(val_pantalla, errors="coerce") or 0.0
                                    costos_actualizados.append(precio_encontrado)
                                
                                df_limpio["Precio Unitario"] = costos_actualizados
                                df_limpio["Monto Total"] = df_limpio["Precio Unitario"] * df_limpio["Cantidad"]
                                
                                # Revertir nombres de columnas amigables a originales del historial
                                df_limpio = df_limpio.rename(columns={
                                    "Código": "Actividad",
                                    "DETALLE": "Descripción",
                                    "Costo Unitario": "Precio Unitario",
                                    "Costo Total": "Monto Total",
                                    "IDP": "IDP N°",
                                    "Fec": "Fecha",
                                    "Contrata": "Contratista"
                                })
                                
                                df_final_actualizado = pd.concat([df_otros_proyectos, df_limpio], ignore_index=True)
                                df_final_actualizado.to_csv(archivo_historial, index=False)
                                st.success("¡Cambios guardados con éxito en el historial general!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar los cambios: {e}")
    except Exception as e:
        st.warning(f"Error leyendo el historial: {e}")
else:
    st.info("💡 Aún no hay registros en el historial general. Tan pronto guardes el primer IDP, podrás consultar los montos totales acumulados directamente aquí.")
