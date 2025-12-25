import streamlit as st
import pandas as pd
import plotly.express as px

# Configuration de la page
st.set_page_config(page_title="Dashboard Superstore", layout="wide")
st.title("Analyse de Performance Superstore")

# chargement des données et le cleaning
@st.cache_data
def load_data():
    
    df = pd.read_csv(r"C:\Users\dell\Desktop\access2019\Sample - Superstore_CLEAN.csv", encoding="Latin-1")
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    
    return df

df = load_data()

# filtre de la sidebar
st.sidebar.header("Filtres")

# Filtre Date
col_d1, col_d2 = st.sidebar.columns(2)
with col_d1:
    d_start = st.date_input("Début", df['Order Date'].min())
with col_d2:
    d_end = st.date_input("Fin", df['Order Date'].max())

# Filtres Multiselect
f_cat = st.sidebar.multiselect("Category", df['Category'].unique(), default=df['Category'].unique())
f_sub = st.sidebar.multiselect("Sub-Category", df['Sub-Category'].unique(), default=df['Sub-Category'].unique())
f_seg = st.sidebar.multiselect("Segment", df['Segment'].unique(), default=df['Segment'].unique())
f_Region = st.sidebar.multiselect("Region", df['Region'].unique(), default=df['Region'].unique())

# Application du filtrage
df_selection = df[
    (df['Order Date'].dt.date >= d_start) & 
    (df['Order Date'].dt.date <= d_end) &
    (df['Category'].isin(f_cat)) &
    (df['Sub-Category'].isin(f_sub)) &
    (df['Segment'].isin(f_seg)) &
    (df['Region'].isin(f_Region))
]

# Remplacement de df par df_selection pour que les graphiques réagissent
df = df_selection

# CALCUL DES KPI
total_sales = df['Sales'].sum()
num_orders = df['Order ID'].nunique() # chaque order id on le compte une fois comme si c'est un seul panier
avg_order_value = total_sales / num_orders if num_orders > 0 else 0
num_customers = df['Customer ID'].nunique() # chaque customer on

# AFFICHAGE  KPI 
col1, col2, col3, col4 = st.columns(4)

with col1:
      st.metric("Chiffre d'Affaires", f"{total_sales:,.2f} $")

with col2:
 st.metric("Nombre de Commandes", num_orders)

with col3:
    st.metric("Panier Moyen", f"{avg_order_value:,.2f} $")

with col4:
        st.metric("Nombre de Clients", num_customers)

st.divider()




#visualisations 

# prep des dates 
df['Year'] = df['Order Date'].dt.year
df['Month'] = df['Order Date'].dt.month
df['YearMonth'] = df['Order Date'].dt.to_period('M')
df['Date'] = df['Order Date'].dt.date
df['DayName'] = df['Order Date'].dt.day_name()



# chiffre d'affaire par jours
ca_journalier = df.groupby('Date')['Sales'].sum().reset_index()
fig_day = px.line(ca_journalier, x='Date', y='Sales', 
                  title="Évolution du CA par Jour",
                  labels={'Sales': 'Chiffre d\'Affaires ($)', 'Date': 'Date'})


# chiffre d'affaire par mois

ca_mensuel = df.groupby('YearMonth')['Sales'].sum().reset_index()
ca_mensuel['YearMonth_str'] = ca_mensuel['YearMonth'].astype(str)

fig_month = px.line(ca_mensuel, 
                    x='YearMonth_str', 
                    y='Sales', 
                    title="Évolution du CA par Mois (Year-Month)",
                    markers=True,
                    labels={'YearMonth_str': 'Période', 'Sales': 'Chiffre d\'Affaires ($)'})

fig_month.update_xaxes(tickangle=45)


# chiffre d'affaire par année


ca_annee = df.groupby('Year')['Sales'].sum().reset_index()

fig_year = px.line(ca_annee, 
                   x='Year', 
                   y='Sales', 
                   title="Évolution du CA Total par Année",
                   markers=True,  
                   text='Sales')  

# pour ne pas afficher les demi année genre 2015,5
fig_year.update_traces(textposition="top center", line_width=3)
fig_year.update_layout(xaxis_type='category')


st.subheader("Analyses Temporelles")

tab1, tab2, tab3 = st.tabs(["Journalier", "Mensuel", "Annuel"])

with tab1:
    st.plotly_chart(fig_day, use_container_width=True)

with tab2:
    st.plotly_chart(fig_month, use_container_width=True)

with tab3:
    st.plotly_chart(fig_year, use_container_width=True)

st.divider()

# repsresenatation rfm


# calcul rfm comme celui de notebook
snapshot_date = df['Order Date'].max() + pd.Timedelta(days=1)
rfm = df.groupby('Customer ID').agg({
    'Order Date': lambda x: (snapshot_date - x.max()).days,
    'Order ID': 'nunique',
    'Sales': 'sum'
}).reset_index()

rfm.columns = ['Customer ID', 'Recency', 'Frequency', 'Monetary']

# Scores
if len(rfm) >= 5: 
    rfm['R_Score'] = pd.qcut(rfm['Recency'], 5, labels=[5,4,3,2,1])
    rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'), 5, labels=[1,2,3,4,5])
    rfm['M_Score'] = pd.qcut(rfm['Monetary'], 5, labels=[1,2,3,4,5])

    # Segmentation
    def rfm_segment(row):
        r, f, m = int(row['R_Score']), int(row['F_Score']), int(row['M_Score'])
        if r >= 4 and f >= 4 and m >= 4: return 'extra fidèle'
        elif r >= 4 and f >= 3: return 'fidèle'
        elif r <= 2: return 'Pas ouf'
        else: return 'autres'


    #le petit tableau que j'ai afficher dnas le notebook : Une simple liste du nombre de clients par catégorie
    rfm['Segment'] = rfm.apply(rfm_segment, axis=1)
    segment_counts = rfm['Segment'].value_counts().reset_index()
    segment_counts.columns = ['Segment', 'Nombre de Clients']


    #calcule le CA total par segment 
    ca_segment = rfm.groupby('Segment')['Monetary'].sum().reset_index()
    total_ca_global = ca_segment['Monetary'].sum() 
    ca_segment['Contribution %'] = (ca_segment['Monetary'] / total_ca_global) * 100 #  le pourcentage de contribution de chaque segment
    ca_percent_columns = ca_segment[['Segment', 'Contribution %']] # tableau des %

    st.subheader("Segments Clients")

    # gauche dessin /droite tableau (separation de l'ecran)
    col_gauche, col_droite = st.columns([2, 1])

    with col_gauche:
        # Le graphique en forme de Donut
        fig_rfm = px.pie(segment_counts, 
                         values='Nombre de Clients', 
                          names='Segment',
                         hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_rfm, use_container_width=True)

    with col_droite:
       
        st.write("### Nombre de clients")
        st.dataframe(segment_counts, hide_index=True)

        # % du CA de chaque segment
        st.write("###  % du Chiffre d'Affaires")
        ca_percent_columns = ca_segment[['Segment', 'Contribution %']]
        st.table(ca_percent_columns.style.format({'Contribution %': '{:.1f} %'}))
else:
    st.warning("Pas assez de données pour l'analyse RFM avec ces filtres.")




st.divider()
st.subheader(" Performance des Produits (Top vs Flop)")

#creatio, de filtree pas categorie
categories_list = ['Toutes'] + list(df['Category'].unique())

cat_choice = st.selectbox("Filtrer par catégorie interne (Top/Flop) :", categories_list)

# filtrer la dataset par le choix
if cat_choice == 'Toutes':
    df_filtered = df
else:
    df_filtered = df[df['Category'] == cat_choice]

# prep des columns top et flop
col_top, col_flop = st.columns(2)

with col_top:
    st.write("###  Top 10 - Plus gros CA")
    top_products = df_filtered.groupby('Product Name')['Sales'].sum().sort_values(ascending=False).head(10).reset_index()
    
    fig_top = px.bar(top_products, 
                     x='Sales', 
                     y='Product Name', 
                     orientation='h',
                     color='Sales',
                     color_continuous_scale='Greens',
                     labels={'Sales': 'Ventes ($)', 'Product Name': ''})
    
    # On inverse l'axe Y pour avoir le 1er en haut
    fig_top.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_top, use_container_width=True)

with col_flop:
    st.write("###  Top 10 - Moins de Profit (Pertes)")
    # Ici on regarde le Profit négatif (les Flops)
    flop_products = df_filtered.groupby('Product Name')['Profit'].sum().sort_values(ascending=True).head(10).reset_index()
    
    fig_flop = px.bar(flop_products, 
                      x='Profit', 
                      y='Product Name', 
                      orientation='h',
                      color='Profit',
                      color_continuous_scale='Reds_r',
                      labels={'Profit': 'Pertes ($)', 'Product Name': ''})
    
    fig_flop.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_flop, use_container_width=True)






st.divider()
st.subheader(" Analyse de la Saisonnalité")

 # Préparation des données par mois 
ca_mensuel_total = df.groupby(['Year', 'Month'])['Sales'].sum().reset_index() # ca total de chaque mois de chaque annéé
saisonnalite_reelle = ca_mensuel_total.groupby('Month')['Sales'].mean().reset_index() # moy du meme mois de chaque année
nom_mois = {1:'Jan', 2:'Fév', 3:'Mar', 4:'Avr', 5:'Mai', 6:'Juin', 
                7:'Juil', 8:'Août', 9:'Sept', 10:'Oct', 11:'Nov', 12:'Déc'}
saisonnalite_reelle['Month_Name'] = saisonnalite_reelle['Month'].map(nom_mois)

# Préparation des données par jour de la semaine
ca_par_date = df.groupby(['Date', 'DayName'])['Sales'].sum().reset_index() #ca de chaque jour de tout les années
ordre_jours = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] # la moy du meme jour pour chaque semaine/moi/anne
ca_jour_semaine = ca_par_date.groupby('DayName')['Sales'].mean().reindex(ordre_jours).reset_index()

#Affichage des 2 graphiques
col_month, col_day = st.columns(2)

with col_month:
    st.write("###  Moyenne d'un Mois Type")
    fig_month_season = px.bar(saisonnalite_reelle, 
                              x='Month_Name', 
                              y='Sales', 
                              color='Sales',
                              title="Saisonnalité Mensuelle (Moyenne)",
                              color_continuous_scale='Blues',
                              labels={'Sales': 'Ventes Moyennes ($)', 'Month_Name': 'Mois'})
    
    st.plotly_chart(fig_month_season, use_container_width=True)
    
    
with col_day:
    st.write("###  Moyenne d'un Jour Type")
    
    fig_day_season = px.bar(ca_jour_semaine, 
                            x='DayName', 
                            y='Sales',
                            color='Sales',
                            title="Ventes moyennes selon le jour de la semaine",
                            color_continuous_scale='Viridis',
                            labels={'Sales': 'Moyenne des ventes ($)', 'DayName': 'Jour'})
    
    st.plotly_chart(fig_day_season, use_container_width=True)