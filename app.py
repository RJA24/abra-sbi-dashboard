import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Abra SBI Dashboard", layout="wide", page_icon="💉")

# --- CUSTOM BANNER ---
st.markdown("""
<style>
.custom-header {
    background-image: url('https://github.com/RJA24/abra-sbi-dashboard/blob/main/EO8tVxSUUAEazoD.jpg?raw=true');
    background-size: cover;
    background-position: Bottom;
    padding: 50px 20px;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 25px;
    box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.3);
}
.custom-header h1 {
    color: white !important;
    text-shadow: 2px 2px 4px #000000;
    margin: 0;
    padding: 0;
    font-size: 2.8rem;
}
.custom-header p {
    color: #f1f2f6;
    text-shadow: 1px 1px 3px #000000;
    font-size: 1.2rem;
    margin-top: 10px;
}
</style>

<div class="custom-header">
    <h1>💉 Abra School-Based Immunization Dashboard</h1>
    <p>Official Provincial 2025 Summary • Live Google Sheets Sync</p>
</div>
""", unsafe_allow_html=True)

# --- DATA CONNECTION ---
SHEET_ID = "1OkXvw0Rx8G2Pd1eeCaEe6SCi3axJ6qalbBL--1IQs7g"

@st.cache_data(ttl=60)
def load_all_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
    try:
        dfs = pd.read_excel(url, sheet_name=None)
        return dfs, None
    except Exception as e:
        return None, f"Connection blocked or file not found. Ensure the Google Sheet is set to 'Anyone with the link can view'. Error: {e}"

col_text, col_btn = st.columns([8, 1])
col_text.markdown("Linked live to Google Sheets. Data refreshes automatically.")
if col_btn.button("🔄 Force Refresh All Data"):
    st.cache_data.clear()
    st.rerun()

dfs, global_err = load_all_data()

def process_sheet(sheet_name):
    if global_err:
        return pd.DataFrame(), global_err
    if dfs is None or sheet_name not in dfs:
        return pd.DataFrame(), f"Tab '{sheet_name}' not found."
    
    df = dfs[sheet_name].copy()
    df.columns = df.columns.astype(str).str.strip()
    if 'Province Name' in df.columns:
        df = df[df['Province Name'].astype(str).str.upper().str.contains('ABRA', na=False)]
    return df, None

df_g1, err1 = process_sheet("Grade1")
df_g4, err4 = process_sheet("Grade4")
df_g7, err7 = process_sheet("Grade7")

# --- TABS ---
tsum, t1, t4, t7 = st.tabs(["📊 Summary", "📘 Grade 1", "🌸 Grade 4 (HPV)", "📗 Grade 7"])

def get_school_col(df):
    return next((c for c in df.columns if 'SCHOOL ID' in c.upper() or 'FACILITY' in c.upper() or 'SCHOOL NAME' in c.upper()), None)

def render_vaccine_tab(df, err, g_label):
    if err:
        st.error(f"Sheet Error: {err}")
    elif df.empty:
        st.warning(f"⚠️ No Abra data found for {g_label}.")
    else:
        mr_m = next((c for c in df.columns if 'MR' in c.upper() and 'MALE' in c.upper() and 'FEMALE' not in c.upper()), None)
        mr_f = next((c for c in df.columns if 'MR' in c.upper() and 'FEMALE' in c.upper()), None)
        td_m = next((c for c in df.columns if 'TD' in c.upper() and 'MALE' in c.upper() and 'FEMALE' not in c.upper()), None)
        td_f = next((c for c in df.columns if 'TD' in c.upper() and 'FEMALE' in c.upper()), None)
        muni_col = 'City/Municipality Name'

        for c in filter(None, [mr_m, mr_f, td_m, td_f]):
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        c1, c2, c3 = st.columns(3)
        sc_col = get_school_col(df)
        c1.metric("Schools/Facilities", f"{df[sc_col].nunique() if sc_col else len(df):,}")
        
        tot_mr = int(df[mr_m].sum() + df[mr_f].sum()) if mr_m and mr_f else 0
        tot_td = int(df[td_m].sum() + df[td_f].sum()) if td_m and td_f else 0
        c2.metric("Total MR", f"{tot_mr:,}")
        c3.metric("Total TD", f"{tot_td:,}")

        if muni_col in df.columns and all([mr_m, mr_f, td_m, td_f]):
            m_data = df.groupby(muni_col)[[mr_m, mr_f, td_m, td_f]].sum().reset_index()
            m_data = m_data.rename(columns={mr_m: 'MR (Male)', td_m: 'TD (Male)', mr_f: 'MR (Female)', td_f: 'TD (Female)'})
            m_data['Total MR'] = m_data['MR (Male)'] + m_data['MR (Female)']
            m_data['Total TD'] = m_data['TD (Male)'] + m_data['TD (Female)']

            cola, colb = st.columns(2)
            with cola:
                fig_m = px.bar(m_data, x=muni_col, y=['MR (Male)', 'TD (Male)'], barmode='group', text_auto=True, title=f"Male Vaccinations ({g_label})", color_discrete_sequence=['#1E88E5', '#D81B60'])
                fig_m.update_layout(legend_title_text='Vaccine Type', yaxis_title='Doses')
                fig_m.update_traces(textfont_size=16, textposition='outside', cliponaxis=False) # Fix applied here!
                st.plotly_chart(fig_m, use_container_width=True, key=f"m_{g_label}")
            with colb:
                fig_f = px.bar(m_data, x=muni_col, y=['MR (Female)', 'TD (Female)'], barmode='group', text_auto=True, title=f"Female Vaccinations ({g_label})", color_discrete_sequence=['#1E88E5', '#D81B60'])
                fig_f.update_layout(legend_title_text='Vaccine Type', yaxis_title='Doses')
                fig_f.update_traces(textfont_size=16, textposition='outside', cliponaxis=False) # Fix applied here!
                st.plotly_chart(fig_f, use_container_width=True, key=f"f_{g_label}")
            
            fig_tot = px.bar(m_data, x=muni_col, y=['Total MR', 'Total TD'], barmode='group', text_auto=True, title=f"Grand Total ({g_label})", color_discrete_sequence=['#43A047', '#FFB300'])
            fig_tot.update_layout(legend_title_text='Total Vaccines', yaxis_title='Doses')
            fig_tot.update_traces(textfont_size=16, textposition='outside', cliponaxis=False) # Fix applied here!
            st.plotly_chart(fig_tot, use_container_width=True, key=f"tot_{g_label}")

# --- SUMMARY TAB ---
with tsum:
    st.subheader("Province-wide Cumulative Totals (Abra)")
    def get_val(df, k1, k2=None):
        if df.empty: return 0
        t = next((c for c in df.columns if k1 in c.upper() and (k2 in c.upper() if k2 else True)), None)
        return pd.to_numeric(df[t], errors='coerce').sum() if t else 0

    total_mr = (get_val(df_g1, 'MR', 'MALE') + get_val(df_g1, 'MR', 'FEMALE') +
                get_val(df_g7, 'MR', 'MALE') + get_val(df_g7, 'MR', 'FEMALE'))
    total_hpv = get_val(df_g4, 'HPV')

    all_schools = pd.Series(dtype=str)
    for d in [df_g1, df_g4, df_g7]:
        sc = get_school_col(d)
        if sc and not d.empty:
            all_schools = pd.concat([all_schools, d[sc].astype(str)])

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Combined MR (G1+G7)", f"{int(total_mr):,}")
    sc2.metric("Total HPV (G4)", f"{int(total_hpv):,}")
    sc3.metric("Unique Facilities Reached", f"{all_schools.nunique():,}")

with t1: render_vaccine_tab(df_g1, err1, "G1")
with t7: render_vaccine_tab(df_g7, err7, "G7")

# --- GRADE 4 TAB ---
with t4:
    if err4:
        st.error(f"Sheet Error: {err4}")
    elif df_g4.empty:
        st.warning("⚠️ No Abra data found for Grade 4.")
    else:
        c1, c2 = st.columns(2)
        sc_col = get_school_col(df_g4)
        c1.metric("Schools/Facilities (G4)", f"{df_g4[sc_col].nunique() if sc_col else len(df_g4):,}")
        
        hpv_c = next((c for c in df_g4.columns if 'HPV' in c.upper()), None)
        if hpv_c:
            df_g4[hpv_c] = pd.to_numeric(df_g4[hpv_c], errors='coerce').fillna(0)
            c2.metric("Total HPV (Abra)", f"{int(df_g4[hpv_c].sum()):,}")
            
            muni_col = 'City/Municipality Name'
            if muni_col in df_g4.columns:
                m_hpv = df_g4.groupby(muni_col)[hpv_c].sum().reset_index()
                m_hpv = m_hpv.rename(columns={hpv_c: 'HPV Doses'})
                fig_hpv = px.bar(m_hpv, x=muni_col, y='HPV Doses', text_auto=True, title="HPV by Municipality", color_discrete_sequence=['#8E24AA'])
                fig_hpv.update_traces(textfont_size=16, textposition='outside', cliponaxis=False) # Fix applied here!
                st.plotly_chart(fig_hpv, use_container_width=True, key="hpv_unique_plot")
        else:
            c2.metric("Total HPV (Abra)", "0")
            st.error("⚠️ Could not find an 'HPV' column in the Grade 4 tab. Please check your Google Sheet headers.")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888888; padding: 10px;'>
        <p>Developed by <strong>JangTV</strong></p>
    </div>
    """, 
    unsafe_allow_html=True
)





