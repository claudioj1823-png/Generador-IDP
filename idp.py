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
    contratas = sorted(
        [c for c in df["Contrata"].unique() if c and c.lower() != "nan"]
    )
    contrata_sel = st.selectbox(
        "Selecciona la Compañía Contratista:", contratas
    )

  with col_idp_num:
    idp_numero = st.number_input("IDP N°:", min_value=1, value=1, step=1)

  with col_fecha:
    fecha_idp = st.date_input("Fecha:")

  with col_proj:
    lista_codigos = list(dict_proyectos.keys())
    codigo_proyecto_sel = st.selectbox("Código de Proyecto:", lista_codigos)

  # Mostrar el nombre completo del proyecto asociado de manera limpia arriba
  nombre_proyecto_sel = dict_proyectos.get(
      codigo_proyecto_sel, "Proyecto No Encontrado"
  )
  st.info(
      f"**Proyecto Seleccionado:** {nombre_proyecto_sel}  |  **IDP N°:**"
      f" {idp_numero}  |  **Fecha:** {fecha_idp}"
  )

  st.markdown("---")

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

      # Estilos mejorados con color de texto forzado a oscuro (#111111) para evitar conflictos en celulares
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

          # Estilos idénticos forzados a texto oscuro para la tabla de materiales
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
            df_guardar.insert(0, "IDP N°", idp_numero)
            df_guardar.insert(1, "Fecha", str(fecha_idp))
            df_guardar.insert(2, "Código Proyecto", codigo_proyecto_sel)
            df_guardar.insert(3, "Nombre Proyecto", nombre_proyecto_sel)

            if os.path.exists(archivo_historial):
              df_guardar.to_csv(
                  archivo_historial, mode="a", header=False, index=False
              )
            else:
              df_guardar.to_csv(archivo_historial, index=False)

            st.success(
                "¡IDP guardado exitosamente en el historial general de la"
                " aplicación!"
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
