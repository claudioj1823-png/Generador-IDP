import io
import os
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Generador de IDP", layout="wide")

# URL de exportación directa en CSV de tu Google Sheets (Historial de Mano de Obra)
URL_SHEET_CSV = "https://docs.google.com/spreadsheets/d/1uv-8bZLG8UtvhvpYt6FHOJaXoi6mtPcQB3aiR3zjir8/gviz/tq?tqx=out:csv&sheet=Historial_IDP"

# URL de exportación directa en CSV para el Historial de Materiales
URL_SHEET_MAT_CSV = "https://docs.google.com/spreadsheets/d/1uv-8bZLG8UtvhvpYt6FHOJaXoi6mtPcQB3aiR3zjir8/gviz/tq?tqx=out:csv&sheet=Historial_Materiales"

# URL de tu Aplicación Web de Google Apps Script para guardar datos de forma permanente
URL_WEB_APP = "https://script.google.com/macros/s/AKfycbw4rtdaMyiLi3JquNCZoXaV-TFn7DkieE2sP_BuD-ZBFzdT4TjX2fLqMVn_JvN-P63o/exec"
TOKEN_SECRETO = "proyectos2026"


def cargar_historial_permanente():
    try:
        df_hist = pd.read_csv(URL_SHEET_CSV)
        if df_hist is not None and not df_hist.empty:
            df_hist = df_hist.dropna(how="all")
            mapeo_renombrado = {
                "Código": "Actividad",
                "DETALLE": "Descripción",
                "Costo Unitario": "Precio Unitario",
                "Costo Total": "Monto Total",
                "IDP": "IDP N°",
                "Fec": "Fecha",
                "Contrata": "Contratista",
            }
            df_hist = df_hist.rename(columns=mapeo_renombrado)
            return df_hist
    except Exception as e:
        st.error(f"Error al leer el historial: {e}")
    return pd.DataFrame()


def cargar_historial_materiales_permanente():
    try:
        df_mat = pd.read_csv(URL_SHEET_MAT_CSV)
        if df_mat is not None and not df_mat.empty:
            df_mat = df_mat.dropna(how="all")
            return df_mat
    except Exception as e:
        pass
    return pd.DataFrame()


def guardar_idp_en_google_sheets(
    df_idp, df_resumen, idp_numero, fecha_idp, codigo_proyecto, contrata_sel
):
    nombre_proyecto_val = dict_proyectos.get(codigo_proyecto, codigo_proyecto)
    clave_unica = f"{codigo_proyecto}_{idp_numero}_{contrata_sel}_{fecha_idp}"

    actividades_data = []
    for _, row in df_idp.iterrows():
        actividades_data.append({
            "Código": str(row.get("Actividad", "")),
            "DETALLE": str(row.get("Descripción", "")),
            "Costo Unitario": float(
                str(row.get("Precio Unitario", 0))
                .replace("$", "")
                .replace(",", "")
                or 0
            ),
            "Cantidad": float(row.get("Cantidad", 0) or 0),
            "Costo Total": float(
                str(row.get("Monto Total", 0))
                .replace("$", "")
                .replace(",", "")
                or 0
            ),
            "IDP": int(idp_numero),
            "Fec": str(fecha_idp),
            "Contrata": str(contrata_sel),
            "Código Proyecto": str(codigo_proyecto),
            "Nombre Proyecto": str(nombre_proyecto_val),
        })

    materiales_data = []
    if not df_resumen.empty:
        for _, row in df_resumen.iterrows():
            materiales_data.append({
                "IDP": int(idp_numero),
                "Fec": str(fecha_idp),
                "Código Proyecto": str(codigo_proyecto),
                "Nombre Proyecto": str(nombre_proyecto_val),
                "Contrata": str(contrata_sel),
                "Código SAP": str(row.get("Código SAP", "")),
                "Descripción de Material": str(
                    row.get("Descripción de Material", "")
                ),
                "Unidad": str(row.get("Unidad", "")),
                "Cantidad Total": float(row.get("Cantidad Total", 0) or 0),
            })

    payload = {
        "token": TOKEN_SECRETO,
        "clave": clave_unica,
        "numero": int(idp_numero),
        "fecha": str(fecha_idp),
        "proyecto": str(codigo_proyecto),
        "contratista": str(contrata_sel),
        "actividades": actividades_data,
        "materiales": materiales_data,
    }

    try:
        response = requests.post(URL_WEB_APP, json=payload, timeout=30)
        resultado = response.json()
        return resultado
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


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
    "Calcula montos por contratista, proyecto y materiales excluyendo actividades sin insumos de almacén."
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
        return dict(zip(codigos, nombres))
    except Exception as e:
        return {"O-RP-24-368": f"Error al cargar proyectos: {e}"}


dict_proyectos = cargar_proyectos()


@st.cache_data
def cargar_datos():
    try:
        ruta = os.path.join(
            os.path.dirname(__file__), "Actividades contratistas.xlsx"
        )
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

    # --- CABECERA SUPERIOR CON KEYS PARA LIMPIEZA ---
    col_cont, col_idp_num, col_fecha, col_proj = st.columns([2, 1.2, 1.5, 2.5])

    with col_cont:
        contratas_puras = sorted(
            [c for c in df["Contrata"].unique() if c and c.lower() != "nan"]
        )
        opciones_contrata_menu = [
            "-- Seleccione la contrata --"
        ] + contratas_puras
        contrata_sel_menu = st.selectbox(
            "Selecciona la Compañía Contratista:",
            opciones_contrata_menu,
            key="menu_contrata",
        )
        contrata_sel = (
            contrata_sel_menu
            if contrata_sel_menu != "-- Seleccione la contrata --"
            else None
        )

    with col_idp_num:
        idp_numero = st.number_input(
            "IDP N°:", min_value=1, value=1, step=1, key="menu_idp_num"
        )

    with col_fecha:
        fecha_idp = st.date_input("Fecha:", key="menu_fecha")

    with col_proj:
        lista_codigos = list(dict_proyectos.keys())
        opciones_proyecto_menu = [
            "-- Seleccione el proyecto --"
        ] + lista_codigos
        proyecto_sel_menu = st.selectbox(
            "Código de Proyecto:",
            opciones_proyecto_menu,
            key="menu_proyecto",
        )
        codigo_proyecto_sel = (
            proyecto_sel_menu
            if proyecto_sel_menu != "-- Seleccione el proyecto --"
            else None
        )

    if contrata_sel and codigo_proyecto_sel:
        nombre_proyecto_sel = dict_proyectos.get(
            codigo_proyecto_sel, "Proyecto No Encontrado"
        )
        st.info(
            f"**Contratista:** {contrata_sel}  |  **Proyecto Seleccionado:** {nombre_proyecto_sel}  |  **IDP N°:** {idp_numero}  |  **Fecha:** {fecha_idp}"
        )
    else:
        st.info(
            "💡 **Por favor, seleccione tanto la Compañía Contratista como el Código de Proyecto arriba para continuar.**"
        )

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
                act_sel = st.selectbox(
                    "Unidad Constructiva (UU.TT.):", opciones
                )
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
                st.subheader(
                    "Resumen del IDP Actual (Estructuras / Actividades)"
                )
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
                    df_idp["Monto Total"] = df_idp[
                        "Precio Unitario"
                    ] * pd.to_numeric(df_idp["Cantidad"], errors="coerce")

                df_idp_show = df_idp[[
                    "Actividad",
                    "Descripción",
                    "Cantidad",
                    "Precio Unitario",
                    "Monto Total",
                ]].copy()

                df_idp_show["Precio Unitario"] = df_idp_show[
                    "Precio Unitario"
                ].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00")
                df_idp_show["Monto Total"] = df_idp_show["Monto Total"].map(
                    lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                )

                html_est = df_idp_show.to_html(
                    classes="custom-table", escape=False, index=False
                )
                st.html(f"""
                    <style>
                    .custom-table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; background-color: white !important; margin-bottom: 15px; }}
                    .custom-table th {{ padding: 10px 12px; border-bottom: 1px solid #e0e0e0; text-align: left; background-color: #0b2545 !important; color: white !important; font-weight: bold; border: 1px solid #0b2545; }}
                    .custom-table td {{ padding: 10px 12px; border-bottom: 1px solid #e0e0e0; text-align: left; background-color: white !important; color: #111111 !important; }}
                    .custom-table tr:hover td {{ background-color: #f8f9fa !important; }}
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
                        st.success(
                            f"Fila {fila_a_borrar} eliminada correctamente."
                        )
                        st.rerun()

                if cols_precio:
                    total_estructuras = df_idp["Monto Total"].sum()
                    st.metric(
                        label="Monto Total de Estructuras / Actividades",
                        value=f"${total_estructuras:,.2f}",
                    )

                st.subheader("Requerimiento Consolidado de Materiales")
                df_idp_agrupado = (
                    df_idp.groupby("Actividad")["Cantidad"].sum().to_dict()
                )
                df_filtrado = df_c[
                    df_c["Actividad"].isin(df_idp_agrupado.keys())
                ].copy()

                df_resumen = pd.DataFrame()
                if not df_filtrado.empty:
                    df_filtrado["Cant_IDP"] = df_filtrado["Actividad"].map(
                        df_idp_agrupado
                    )
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
                        cols_und = [
                            c
                            for c in df_filtrado.columns
                            if "unid" in c.lower()
                        ]

                        cod_col = (
                            cols_cod[0]
                            if cols_cod
                            else df_filtrado.columns[0]
                        )
                        desc_mat_col = (
                            cols_desc_mat[0] if cols_desc_mat else cod_col
                        )
                        und_col = cols_und[0] if cols_und else None

                        columnas_agrupacion = [cod_col, desc_mat_col]
                        if und_col:
                            columnas_agrupacion.append(und_col)

                        df_resumen = df_filtrado.groupby(
                            columnas_agrupacion, as_index=False
                        ).agg({"Cantidad_Total": "sum"})
                        df_resumen[cod_col] = (
                            df_resumen[cod_col]
                            .astype(str)
                            .str.replace(r"\.0$", "", regex=True)
                        )
                        df_resumen["Cantidad_Total"] = (
                            pd.to_numeric(
                                df_resumen["Cantidad_Total"], errors="coerce"
                            )
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
                            classes="custom-table-mat",
                            escape=False,
                            index=False,
                        )
                        st.html(f"""
                            <style>
                            .custom-table-mat {{ width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; background-color: white !important; margin-bottom: 15px; }}
                            .custom-table-mat th {{ padding: 10px 12px; border-bottom: 1px solid #e0e0e0; text-align: left; background-color: #0b2545 !important; color: white !important; font-weight: bold; border: 1px solid #0b2545; }}
                            .custom-table-mat td {{ padding: 10px 12px; border-bottom: 1px solid #e0e0e0; text-align: left; background-color: white !important; color: #111111 !important; }}
                            .custom-table-mat tr:hover td {{ background-color: #f8f9fa !important; }}
                            </style>
                            {html_mat}
                        """)
                    else:
                        st.dataframe(df_filtrado, use_container_width=True)
                else:
                    st.info(
                        "No hay materiales asociados a las actividades seleccionadas."
                    )

                st.markdown("---")
                st.subheader("Exportar Resultados y Registro Histórico")
                col_exp1, col_exp2 = st.columns([1, 1])

                with col_exp1:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        df_idp.to_excel(
                            writer,
                            sheet_name="Estructuras_Actividades",
                            index=False,
                        )
                        if not df_resumen.empty:
                            df_resumen.to_excel(
                                writer,
                                sheet_name="Requerimiento_Materiales",
                                index=False,
                            )
                    output.seek(0)
                    st.download_button(
                        label="📥 Descargar IDP Completo en Excel",
                        data=output,
                        file_name=(
                            f"IDP_{idp_numero}_{contrata_sel.replace(' ', '_')}.xlsx"
                        ),
                        mime=(
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        ),
                    )

                with col_exp2:
                    if st.button("💾 Guardar IDP en el Historial General"):
                        if not df_idp.empty:
                            with st.spinner("Guardando IDP en la nube..."):
                                res = guardar_idp_en_google_sheets(
                                    df_idp,
                                    df_resumen,
                                    idp_numero,
                                    fecha_idp,
                                    codigo_proyecto_sel,
                                    contrata_sel,
                                )
                                if res.get("ok"):
                                    st.success(
                                        "¡IDP guardado con éxito en Google Sheets! 🎉"
                                    )
                                    # 🧹 LIMPIEZA TOTAL: Vaciamos lista y reseteamos menús superiores
                                    st.session_state.lista_idp = []
                                    st.session_state["menu_contrata"] = (
                                        "-- Seleccione la contrata --"
                                    )
                                    st.session_state["menu_proyecto"] = (
                                        "-- Seleccione el proyecto --"
                                    )
                                    st.rerun()
                                elif res.get("duplicado"):
                                    st.warning(
                                        "⚠️ Este IDP ya fue registrado anteriormente."
                                    )
                                else:
                                    st.error(
                                        f"Error al guardar: {res.get('mensaje')}"
                                    )
                        else:
                            st.warning(
                                "No hay actividades en el IDP actual para guardar."
                            )

                st.markdown("---")
                if st.button("Limpiar Todo el IDP Actual"):
                    st.session_state.lista_idp = []
                    st.session_state["menu_contrata"] = (
                        "-- Seleccione la contrata --"
                    )
                    st.session_state["menu_proyecto"] = (
                        "-- Seleccione el proyecto --"
                    )
                    st.rerun()

# ==========================================
# SECCIÓN: CONSULTA RÁPIDA DE HISTORIAL PERMANENTE
# ==========================================
st.markdown("---")
st.subheader("🔍 Consultar Historial Consolidado por Proyecto")

df_hist_total = cargar_historial_permanente()
df_hist_mat_total = cargar_historial_materiales_permanente()

if not df_hist_total.empty:
    df_hist_total = df_hist_total.loc[:, ~df_hist_total.columns.duplicated()]

    if "Fecha" in df_hist_total.columns:
        df_hist_total["Fecha"] = (
            df_hist_total["Fecha"]
            .astype(str)
            .str.split(" ")
            .str[0]
            .str.strip()
        )

    cols_p_excel = [
        c for c in df.columns if "precio" in c.lower() or "costo" in c.lower()
    ]
    if cols_p_excel:
        col_p_nom = cols_p_excel[0]
        dict_tarifas_maestro = {}
        for _, r_t in df.iterrows():
            c_cont_m = str(r_t.get("Contrata", "")).strip().lower()
            c_act_m = str(r_t.get("Actividad", "")).strip().lower()
            val_pr = (
                pd.to_numeric(
                    str(r_t.get(col_p_nom, 0))
                    .replace("$", "")
                    .replace(",", ""),
                    errors="coerce",
                )
                or 0.0
            )
            dict_tarifas_maestro[(c_cont_m, c_act_m)] = val_pr

        precios_reparados = []
        for _, row_h in df_hist_total.iterrows():
            act_val = (
                str(row_h.get("Actividad", row_h.get("Código", "")))
                .strip()
                .lower()
            )
            cont_val = (
                str(row_h.get("Contratista", row_h.get("Contrata", "")))
                .strip()
                .lower()
            )
            p_actual_raw = row_h.get(
                "Precio Unitario", row_h.get("Costo Unitario", 0)
            )
            p_actual = (
                pd.to_numeric(
                    str(p_actual_raw).replace("$", "").replace(",", ""),
                    errors="coerce",
                )
                or 0.0
            )

            if p_actual == 0.0:
                p_actual = dict_tarifas_maestro.get((cont_val, act_val), 0.0)

            precios_reparados.append(p_actual)

        df_hist_total["Precio Unitario"] = precios_reparados
    else:
        df_hist_total["Precio Unitario"] = 0.0

    if "Cantidad" in df_hist_total.columns:
        df_hist_total["Cantidad"] = pd.to_numeric(
            df_hist_total["Cantidad"], errors="coerce"
        ).fillna(0)
    else:
        df_hist_total["Cantidad"] = 0.0

    df_hist_total["Monto Total"] = (
        df_hist_total["Precio Unitario"] * df_hist_total["Cantidad"]
    )


    def formatear_columnas_tabla(df_in):
        df_fmt = df_in.copy()
        df_fmt = df_fmt.loc[:, ~df_fmt.columns.duplicated()]
        if "Fecha" in df_fmt.columns:
            df_fmt["Fecha"] = (
                df_fmt["Fecha"].astype(str).str.split(" ").str[0].str.strip()
            )

        renombres_map = {
            "Actividad": "Código",
            "Descripción": "DETALLE",
            "Precio Unitario": "Costo Unitario",
            "Cantidad": "Cantidad",
            "Monto Total": "Costo Total",
            "IDP N°": "IDP",
            "Fecha": "Fec",
            "Contrata": "Contrata",
            "Código Proyecto": "Código Proyecto",
            "Nombre Proyecto": "Nombre Proyecto",
        }
        df_fmt = df_fmt.rename(columns=renombres_map)
        orden_columnas = [
            "Código",
            "DETALLE",
            "Costo Unitario",
            "Cantidad",
            "Costo Total",
            "IDP",
            "Fec",
            "Contrata",
            "Código Proyecto",
            "Nombre Proyecto",
        ]
        cols_existentes = [c for c in orden_columnas if c in df_fmt.columns]
        otras = [c for c in df_fmt.columns if c not in cols_existentes]
        return df_fmt[cols_existentes + otras]


    if "Código Proyecto" in df_hist_total.columns:
        proyectos_guardados = (
            df_hist_total["Código Proyecto"].dropna().unique().tolist()
        )
        if proyectos_guardados:
            opciones_menu = [
                "-- Seleccione el proyecto --"
            ] + proyectos_guardados
            proj_seleccionado = st.selectbox(
                "Selecciona el Código de Proyecto a Consultar en Pantalla:",
                opciones_menu,
                key="filtro_proyecto_historial_global",
            )

            if proj_seleccionado != "-- Seleccione el proyecto --":
                df_filtrado_proj = df_hist_total[
                    df_hist_total["Código Proyecto"] == proj_seleccionado
                ].copy()
                monto_acumulado_proyecto = df_filtrado_proj[
                    "Monto Total"
                ].sum()
                nombre_proj_actual = dict_proyectos.get(
                    proj_seleccionado, proj_seleccionado
                )

                st.metric(
                    label=(
                        "💰 Monto Total Acumulado Pagado en el Proyecto"
                        f" ({nombre_proj_actual})"
                    ),
                    value=f"${monto_acumulado_proyecto:,.2f}",
                )

                df_proj_fmt = formatear_columnas_tabla(df_filtrado_proj)
                cols_a_mostrar_proj = [
                    c
                    for c in df_proj_fmt.columns
                    if c not in ["Código Proyecto", "Nombre Proyecto"]
                ]

                st.info(
                    f"👷 **Mano de obra proyecto : {nombre_proj_actual}**"
                )
                df_vistas_display = df_proj_fmt[cols_a_mostrar_proj].copy()
                df_vistas_display["Costo Unitario"] = df_vistas_display[
                    "Costo Unitario"
                ].map(lambda x: f"${x:,.2f}")
                df_vistas_display["Costo Total"] = df_vistas_display[
                    "Costo Total"
                ].map(lambda x: f"${x:,.2f}")
                st.dataframe(df_vistas_display, use_container_width=True)

                # --- DESPLEGABLE DE MATERIALES INSTALADOS (SAP) EN EL HISTORIAL (CORREGIDO) ---
                with st.expander("🛠️ Ver Detalle de Materiales Instalados (SAP)"):
                    if not df_hist_mat_total.empty:
                        col_proj_mat = [
                            c
                            for c in df_hist_mat_total.columns
                            if "proyecto" in c.lower() or "código" in c.lower()
                        ]
                        if col_proj_mat:
                            c_p_m = col_proj_mat[0]
                            df_mat_proj = df_hist_mat_total[
                                df_hist_mat_total[c_p_m].astype(str).str.strip()
                                == str(proj_seleccionado).strip()
                            ].copy()

                            if not df_mat_proj.empty:
                                # Búsqueda estricta del Código SAP real
                                cols_mat_sap = [
                                    c
                                    for c in df_mat_proj.columns
                                    if "sap" in c.lower()
                                ]
                                if not cols_mat_sap:
                                    cols_mat_sap = [
                                        c
                                        for c in df_mat_proj.columns
                                        if "código" in c.lower()
                                        and "proyecto" not in c.lower()
                                    ]

                                cols_mat_desc = [
                                    c
                                    for c in df_mat_proj.columns
                                    if "descripci" in c.lower()
                                    or "material" in c.lower()
                                ]
                                cols_mat_cant = [
                                    c
                                    for c in df_mat_proj.columns
                                    if "cant" in c.lower()
                                ]

                                if cols_mat_sap and cols_mat_cant:
                                    cs_sap = cols_mat_sap[0]
                                    cs_cant = cols_mat_cant[0]
                                    cs_desc = (
                                        cols_mat_desc[0]
                                        if cols_mat_desc
                                        else cs_sap
                                    )

                                    df_mat_proj[cs_cant] = pd.to_numeric(
                                        df_mat_proj[cs_cant], errors="coerce"
                                    ).fillna(0)
                                    df_mat_cons = (
                                        df_mat_proj.groupby(
                                            [cs_sap, cs_desc], as_index=False
                                        )[cs_cant]
                                        .sum()
                                        .rename(
                                            columns={
                                                cs_sap: "Código SAP",
                                                cs_desc: (
                                                    "Descripción de Material"
                                                ),
                                                cs_cant: "Cantidad Total",
                                            }
                                        )
                                    )
                                    st.dataframe(
                                        df_mat_cons, use_container_width=True
                                    )
                                else:
                                    st.dataframe(
                                        df_mat_proj, use_container_width=True
                                    )
                            else:
                                st.info(
                                    "No hay registros de materiales asociados a este proyecto en el historial."
                                )
                        else:
                            st.info(
                                "La pestaña Historial_Materiales no contiene una columna de proyecto identificable."
                            )
                    else:
                        st.info(
                            "La pestaña Historial_Materiales está vacía o no se pudo cargar."
                        )
else:
    st.info(
        "💡 No se pudieron cargar los registros o la hoja está vacía. Verifica"
        " que la hoja de Google Sheets tenga los permisos públicos de lectura"
        " ('Cualquier persona con el vínculo')."
    )
