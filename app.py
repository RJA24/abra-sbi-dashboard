import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Abra SBI Dashboard", layout="wide", page_icon="💉", initial_sidebar_state="expanded")

# --- CUSTOM BANNER WITH OPACITY OVERLAY ---
st.markdown("""
<style>
.custom-header {
    /* We add a semi-transparent black layer (rgba 0,0,0, 0.2) over the image URL */
    background-image: linear-gradient(rgba(0, 0, 0, 0.2), rgba(0, 0, 0, 0.2)), url('https://github.com/RJA24/abra-sbi-dashboard/blob/main/EO8tVxSUUAEazoD.jpg?raw=true');
    background-size: cover;
    background-position: 50% 55%;
    padding: 50px 20px;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 20px;
    box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.3);
}
.custom-header h1 {
    color: white !important;
    /* Since the background is darker now, we can reduce the text shadow slightly for a cleaner look */
    text-shadow: 1px 1px 3px #000000;
    margin: 0;
    padding: 0;
    font-size: 2.8rem;
}
.custom-header p {
    color: #f1f2f6;
    text-shadow: 1px 1px 2px #000000;
    font-size: 1.2rem;
    margin-top: 10px;
}
</style>
<div class="custom-header">
    <h1>💉 Abra School-Based Immunization Dashboard</h1>
    <p>Official Provincial 2025 Summary • Live Google Sheets Sync</p>
</div>
""", unsafe_allow_html=True)
# --- DATA CONNECTION & TIMESTAMP ---
SHEET_ID = "1OkXvw0Rx8G2Pd1eeCaEe6SCi3axJ6qalbBL--1IQs7g"

@st.cache_data(ttl=60)
def load_all_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
    fetch_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%B %d, %Y at %I:%M %p")
    try:
        dfs = pd.read_excel(url, sheet_name=None)
        return dfs, None, fetch_time
    except Exception as e:
        return None, f"Connection Error: {e}", fetch_time

dfs, global_err, last_synced = load_all_data()

def process_sheet(sheet_name):
    if global_err: return pd.DataFrame(), global_err
    if dfs is None or sheet_name not in dfs: return pd.DataFrame(), f"Tab '{sheet_name}' not found."
    df = dfs[sheet_name].copy()
    df.columns = df.columns.astype(str).str.strip()
    if 'Province Name' in df.columns:
        df = df[df['Province Name'].astype(str).str.upper().str.contains('ABRA', na=False)]
    return df, None

df_g1, err1 = process_sheet("Grade1")
df_g4, err4 = process_sheet("Grade4")
df_g7, err7 = process_sheet("Grade7")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Dashboard Controls")
st.sidebar.info(f"🟢 **Last Synced:**\n{last_synced}")

if st.sidebar.button("🔄 Force Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Filter Location")

# Gather all unique municipalities for the multi-select dropdown
all_munis = set()
for d in [df_g1, df_g4, df_g7]:
    if not d.empty and 'City/Municipality Name' in d.columns:
        all_munis.update(d['City/Municipality Name'].dropna().unique())

muni_list = ["All Abra"] + sorted(list(all_munis))

# THE MULTI-SELECT BOX
selected_munis = st.sidebar.multiselect(
    "Select Municipalities", 
    options=muni_list,
    default=["All Abra"]
)

if not selected_munis or "All Abra" in selected_munis:
    display_loc = "All Abra"
    active_filter = [] 
elif len(selected_munis) <= 2:
    display_loc = " & ".join(selected_munis)
    active_filter = selected_munis
else:
    display_loc = f"{len(selected_munis)} Municipalities"
    active_filter = selected_munis

def filter_df(df):
    if not active_filter or df.empty or 'City/Municipality Name' not in df.columns:
        return df
    return df[df['City/Municipality Name'].isin(active_filter)]

df_g1 = filter_df(df_g1)
df_g4 = filter_df(df_g4)
df_g7 = filter_df(df_g7)

# --- TABS ---
# NOTE: We added "🗺️ Map View" right next to the Summary!
tsum, tmap, t1, t4, t7 = st.tabs(["📊 Summary", "🗺️ Map View", "📘 Grade 1", "🌸 Grade 4 (HPV)", "📗 Grade 7"])

def get_school_col(df):
    return next((c for c in df.columns if 'SCHOOL ID' in c.upper() or 'FACILITY' in c.upper() or 'SCHOOL NAME' in c.upper()), None)

def render_vaccine_tab(df, err, g_label):
    if err:
        st.error(f"Sheet Error: {err}")
    elif df.empty:
        st.warning(f"⚠️ No data found for {g_label} in {display_loc}.")
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

            csv = m_data.to_csv(index=False).encode('utf-8')
            st.download_button(label=f"📥 Download {g_label} Summary Report (CSV)", data=csv, file_name=f"{g_label}_{display_loc.replace(' ', '_')}_summary.csv", mime='text/csv')

            st.markdown("<br>", unsafe_allow_html=True)
            cola, colb = st.columns(2)
            with cola:
                fig_m = px.bar(m_data, x=muni_col, y=['MR (Male)', 'TD (Male)'], barmode='group', text_auto=True, title=f"Male Vaccinations ({g_label})", color_discrete_sequence=['#1E88E5', '#D81B60'])
                fig_m.update_layout(legend_title_text='Vaccine Type', yaxis_title='Doses')
                fig_m.update_traces(textfont_size=16, textposition='outside', cliponaxis=False)
                st.plotly_chart(fig_m, use_container_width=True, key=f"m_{g_label}")
            with colb:
                fig_f = px.bar(m_data, x=muni_col, y=['MR (Female)', 'TD (Female)'], barmode='group', text_auto=True, title=f"Female Vaccinations ({g_label})", color_discrete_sequence=['#1E88E5', '#D81B60'])
                fig_f.update_layout(legend_title_text='Vaccine Type', yaxis_title='Doses')
                fig_f.update_traces(textfont_size=16, textposition='outside', cliponaxis=False)
                st.plotly_chart(fig_f, use_container_width=True, key=f"f_{g_label}")
            
            fig_tot = px.bar(m_data, x=muni_col, y=['Total MR', 'Total TD'], barmode='group', text_auto=True, title=f"Grand Total ({g_label})", color_discrete_sequence=['#43A047', '#FFB300'])
            fig_tot.update_layout(legend_title_text='Total Vaccines', yaxis_title='Doses')
            fig_tot.update_traces(textfont_size=16, textposition='outside', cliponaxis=False)
            st.plotly_chart(fig_tot, use_container_width=True, key=f"tot_{g_label}")

# --- SUMMARY TAB ---
with tsum:
    st.subheader(f"Cumulative Totals ({display_loc})")
    def get_val(df, k1, k2=None):
        if df.empty: return 0
        t = next((c for c in df.columns if k1 in c.upper() and (k2 in c.upper() if k2 else True)), None)
        return pd.to_numeric(df[t], errors='coerce').sum() if t else 0

    total_mr = get_val(df_g1, 'MR', 'MALE') + get_val(df_g1, 'MR', 'FEMALE') + get_val(df_g7, 'MR', 'MALE') + get_val(df_g7, 'MR', 'FEMALE')
    total_td = get_val(df_g1, 'TD', 'MALE') + get_val(df_g1, 'TD', 'FEMALE') + get_val(df_g7, 'TD', 'MALE') + get_val(df_g7, 'TD', 'FEMALE')
    
    total_hpv = 0
    if not df_g4.empty:
        total_hpv = sum(pd.to_numeric(df_g4[c], errors='coerce').sum() for c in df_g4.columns if 'HPV' in c.upper())

    all_schools = pd.Series(dtype=str)
    for d in [df_g1, df_g4, df_g7]:
        sc = get_school_col(d)
        if sc and not d.empty:
            all_schools = pd.concat([all_schools, d[sc].astype(str)])

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Combined MR (G1+G7)", f"{int(total_mr):,}")
    sc2.metric("Total HPV Doses (G4)", f"{int(total_hpv):,}")
    sc3.metric("Unique Facilities Reached", f"{all_schools.nunique():,}")

    st.markdown("---")
    st.subheader("Visual Breakdown")
    
    pc1, pc2 = st.columns(2)
    with pc1:
        male_doses = get_val(df_g1, 'MR', 'MALE') + get_val(df_g1, 'TD', 'MALE') + get_val(df_g7, 'MR', 'MALE') + get_val(df_g7, 'TD', 'MALE')
        female_doses = get_val(df_g1, 'MR', 'FEMALE') + get_val(df_g1, 'TD', 'FEMALE') + get_val(df_g7, 'MR', 'FEMALE') + get_val(df_g7, 'TD', 'FEMALE')
        
        df_gender = pd.DataFrame({'Gender': ['Male', 'Female'], 'Doses': [male_doses, female_doses]})
        if df_gender['Doses'].sum() > 0:
            fig_gender = px.pie(df_gender, names='Gender', values='Doses', title="MR & TD by Gender", hole=0.4, color='Gender', color_discrete_map={'Male':'#1E88E5', 'Female':'#D81B60'})
            fig_gender.update_traces(textposition='inside', textinfo='percent+label', textfont_size=14)
            st.plotly_chart(fig_gender, use_container_width=True, key="pie_gender")
            
    with pc2:
        df_vax = pd.DataFrame({'Vaccine': ['MR', 'TD', 'HPV'], 'Doses': [total_mr, total_td, total_hpv]})
        if df_vax['Doses'].sum() > 0:
            fig_vax = px.pie(df_vax, names='Vaccine', values='Doses', title="Overall Vaccine Distribution", hole=0.4, color='Vaccine', color_discrete_map={'MR':'#43A047', 'TD':'#FFB300', 'HPV':'#8E24AA'})
            fig_vax.update_traces(textposition='inside', textinfo='percent+label', textfont_size=14)
            st.plotly_chart(fig_vax, use_container_width=True, key="pie_vax")

# --- MAP TAB ---
with tmap:
    st.subheader(f"📍 Vaccination Density Map ({display_loc})")
    st.markdown("Geographic distribution of all administered doses (MR, TD, and HPV combined). Larger bubbles indicate higher vaccination counts.")
    
    # Internal Coordinate System for Abra Municipalities
    ABRA_COORDS = {
        "BANGUED": (17.5962, 120.6133), "BANGUED (CAPITAL)": (17.5962, 120.6133),
        "BOLINEY": (17.3820, 120.9405), "BUCAY": (17.5255, 120.7302),
        "BUCLOC": (17.4431, 120.8404), "DAGUIOMAN": (17.4475, 120.9324),
        "DANGLAS": (17.6586, 120.6558), "DOLORES": (17.6475, 120.7107),
        "LA PAZ": (17.6698, 120.6725), "LACUB": (17.6669, 120.9439),
        "LAGANGILANG": (17.6167, 120.7333), "LAGAYAN": (17.7289, 120.7364),
        "LANGIDEN": (17.5833, 120.5667), "LICUAN-BAAY": (17.5681, 120.8872),
        "LICUAN-BAAY (LICUAN)": (17.5681, 120.8872), "LUBA": (17.3197, 120.6975),
        "MALIBCONG": (17.5639, 120.9908), "MANABO": (17.4333, 120.7000),
        "PEÑARRUBIA": (17.5656, 120.6389), "PIDIGAN": (17.5750, 120.5833),
        "PILAR": (17.4167, 120.5833), "SALLAPADAN": (17.4589, 120.7631),
        "SAN ISIDRO": (17.4667, 120.6000), "SAN JUAN": (17.7122, 120.7411),
        "SAN QUINTIN": (17.5447, 120.5217), "TAYUM": (17.6000, 120.6500),
        "TINEG": (17.7806, 120.9403), "TUBO": (17.2289, 120.7936),
        "VILLAVICIOSA": (17.4372, 120.6275)
    }
    
    map_df = pd.DataFrame()
    for d in [df_g1, df_g4, df_g7]:
        if not d.empty and 'City/Municipality Name' in d.columns:
            d_copy = d.copy()
            d_copy['Row Total'] = d_copy.select_dtypes(include='number').sum(axis=1)
            agg = d_copy.groupby('City/Municipality Name')['Row Total'].sum().reset_index()
            map_df = pd.concat([map_df, agg])
            
    if not map_df.empty:
        map_data = map_df.groupby('City/Municipality Name')['Row Total'].sum().reset_index()
        map_data = map_data[map_data['Row Total'] > 0] 
        
        map_data['Lat'] = map_data['City/Municipality Name'].str.strip().str.upper().map(lambda x: ABRA_COORDS.get(x, (None, None))[0])
        map_data['Lon'] = map_data['City/Municipality Name'].str.strip().str.upper().map(lambda x: ABRA_COORDS.get(x, (None, None))[1])
        
        map_data_clean = map_data.dropna(subset=['Lat', 'Lon'])
        
        if not map_data_clean.empty:
            # Create a glowing dark-theme bubble map!
            fig_map = px.scatter_mapbox(
                map_data_clean, 
                lat="Lat", lon="Lon", 
                size="Row Total", 
                hover_name="City/Municipality Name",
                color="Row Total", 
                color_continuous_scale="Plasma",
                size_max=40,
                zoom=8.5, 
                center={"lat": 17.58, "lon": 120.61},
                mapbox_style="carto-darkmatter"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("No matching map coordinates found for the selected area.")
    else:
        st.warning("No data available to map yet.")


with t1: render_vaccine_tab(df_g1, err1, "G1")
with t7: render_vaccine_tab(df_g7, err7, "G7")

# --- GRADE 4 TAB ---
with t4:
    if err4:
        st.error(f"Sheet Error: {err4}")
    elif df_g4.empty:
        st.warning(f"⚠️ No data found for Grade 4 in {display_loc}.")
    else:
        c1, c2, c3 = st.columns(3)
        sc_col = get_school_col(df_g4)
        c1.metric("Schools/Facilities (G4)", f"{df_g4[sc_col].nunique() if sc_col else len(df_g4):,}")
        
        hpv_cols = [c for c in df_g4.columns if 'HPV' in c.upper()]
        
        if hpv_cols:
            d1_col = hpv_cols[0]
            d2_col = hpv_cols[1] if len(hpv_cols) > 1 else None
            
            df_g4[d1_col] = pd.to_numeric(df_g4[d1_col], errors='coerce').fillna(0)
            c2.metric("Total HPV (Dose 1)", f"{int(df_g4[d1_col].sum()):,}")
            
            if d2_col:
                df_g4[d2_col] = pd.to_numeric(df_g4[d2_col], errors='coerce').fillna(0)
                c3.metric("Total HPV (Dose 2)", f"{int(df_g4[d2_col].sum()):,}")
            else:
                c3.metric("Total HPV (Dose 2)", "0")
            
            muni_col = 'City/Municipality Name'
            if muni_col in df_g4.columns:
                cols_to_sum = [d1_col] if not d2_col else [d1_col, d2_col]
                m_hpv = df_g4.groupby(muni_col)[cols_to_sum].sum().reset_index()
                
                rename_dict = {d1_col: 'Dose 1'}
                if d2_col: rename_dict[d2_col] = 'Dose 2'
                m_hpv = m_hpv.rename(columns=rename_dict)
                
                csv_hpv = m_hpv.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Download Grade 4 Summary Report (CSV)", data=csv_hpv, file_name=f"G4_{display_loc.replace(' ', '_')}_summary.csv", mime='text/csv')
                
                y_cols = ['Dose 1'] if not d2_col else ['Dose 1', 'Dose 2']
                fig_hpv = px.bar(m_hpv, x=muni_col, y=y_cols, barmode='group', text_auto=True, title="HPV Vaccinations by Municipality", color_discrete_sequence=['#8E24AA', '#E53935'])
                fig_hpv.update_layout(legend_title_text='Dose Number', yaxis_title='Doses')
                fig_hpv.update_traces(textfont_size=16, textposition='outside', cliponaxis=False)
                st.plotly_chart(fig_hpv, use_container_width=True, key="hpv_plot")
        else:
            c2.metric("Total HPV", "0")
            c3.metric("", "")
            st.error("⚠️ Could not find an 'HPV' column in the Grade 4 tab. Please check your headers.")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888888; padding: 10px;'>
        <p>Developed by <strong>JangTV</strong></p>
        <img src="https://github.com/RJA24/abra-sbi-dashboard/blob/main/357094382_2458785624282603_4372984338912374777_n.png?raw=true" width="80" style="margin-top: -10px; opacity: 0.8;">
    </div>
    """, 
    unsafe_allow_html=True
)







