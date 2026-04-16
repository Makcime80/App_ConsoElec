import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import calendar

# --- Configuration ---
st.set_page_config(page_title="Suivi SICAE Expert", layout="wide")
st.title("⚡ Analyse Temporelle de Consommation")

# --- BARRE LATÉRALE ---
st.sidebar.header("Configuration des tarifs")

# 1. LE BOUTON ENGRENAGE (POPOVER)
with st.sidebar.popover("⚙️ Réglages des tarifs"):
    st.markdown("### Paramètres TTC (01/02/2026)")
    prix_hp = st.number_input("Heures Pleines (€)", value=0.20646, format="%.5f")
    prix_hc = st.number_input("Heures Creuses (€)", value=0.15786, format="%.5f")
    abo_annuel = st.number_input("Abo + CTA Annuel (€)", value=190.26, format="%.2f")

st.sidebar.divider()

# --- IMPORT MULTIPLE ---
fichiers_csv = st.file_uploader("Importer vos fichiers CSV SICAE", type=['csv'], accept_multiple_files=True)

if fichiers_csv:
    try:
        liste_df = []
        for fichier in fichiers_csv:
            df_temp = pd.read_csv(fichier, sep=";", header=1, encoding="latin1")
            df_temp['Date'] = pd.to_datetime(df_temp['Date'], format='%d-%m-%Y')
            df_temp = df_temp[['Date', 'Consommation (kWh)', 'Consommation (kWh).1']].copy()
            df_temp.columns = ['Date', 'Conso_HC', 'Conso_HP']
            liste_df.append(df_temp)
            
        df = pd.concat(liste_df, ignore_index=True)
        df.drop_duplicates(subset=['Date'], inplace=True)
        df.sort_values(by='Date', inplace=True)
        df.fillna(0, inplace=True)
        df.set_index('Date', inplace=True) 
        
        # --- INITIALISATION MÉMOIRE ---
        date_min_file = df.index.min().date()
        date_max_file = df.index.max().date()
        today = datetime.date.today()

        if 'start_date' not in st.session_state:
            st.session_state.start_date = date_min_file
            st.session_state.end_date = date_max_file
        if 'freq_selector' not in st.session_state:
            st.session_state.freq_selector = "Jour"

        # --- FILTRES DE PÉRIODE ---
        st.sidebar.subheader("🗓️ Sélection de la période")

        # Calendrier / Semaine
        date_range = st.sidebar.date_input("Calendrier :", value=(st.session_state.start_date, st.session_state.end_date), format="DD/MM/YYYY", label_visibility="collapsed")
        
        if isinstance(date_range, tuple):
            if len(date_range) == 1:
                st.session_state.start_date = date_range[0]
                st.session_state.end_date = date_range[0] + datetime.timedelta(days=6)
                st.session_state.freq_selector = "Jour" 
                st.rerun()
            elif len(date_range) == 2:
                st.session_state.start_date, st.session_state.end_date = date_range

        # Boutons semaine
        col_btn_gauche, col_btn_droite = st.sidebar.columns(2)
        if col_btn_gauche.button("◀️", key="prev_semaine", use_container_width=True):
            st.session_state.start_date -= datetime.timedelta(days=7)
            st.session_state.end_date -= datetime.timedelta(days=7)
            st.rerun()
        if col_btn_droite.button("▶️", key="next_semaine", use_container_width=True):
            st.session_state.start_date += datetime.timedelta(days=7)
            st.session_state.end_date += datetime.timedelta(days=7)
            st.rerun()

        # Bloc Mois
        st.sidebar.write("**Sélection par mois :**")
        liste_mois = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        mois_nom = st.sidebar.selectbox("Mois", options=liste_mois, index=st.session_state.start_date.month - 1, label_visibility="collapsed")
        annee_sel = st.sidebar.number_input("Année", value=st.session_state.start_date.year, min_value=2020, max_value=2030, label_visibility="collapsed")

        selected_month_index = liste_mois.index(mois_nom) + 1
        if selected_month_index != st.session_state.start_date.month or annee_sel != st.session_state.start_date.year:
            dernier_jour = calendar.monthrange(annee_sel, selected_month_index)[1]
            st.session_state.start_date = datetime.date(annee_sel, selected_month_index, 1)
            st.session_state.end_date = datetime.date(annee_sel, selected_month_index, dernier_jour)
            st.session_state.freq_selector = "Semaine"
            st.rerun()

        # Boutons années rapides
        st.sidebar.write("**Années :**")
        c24, c25, c26, c27 = st.sidebar.columns(4)
        for c, y in zip([c24, c25, c26, c27], [2024, 2025, 2026, 2027]):
            if c.button(str(y), use_container_width=True):
                st.session_state.start_date, st.session_state.end_date = datetime.date(y, 1, 1), datetime.date(y, 12, 31)
                st.session_state.freq_selector = "Mois"; st.rerun()

        st.sidebar.divider()

        # --- LOGIQUE D'AFFICHAGE ---
        df_filtre = df.loc[str(st.session_state.start_date):str(st.session_state.end_date)].copy()

        if not df_filtre.empty:
            st.sidebar.subheader("📊 Affichage")
            
            # --- LE NOUVEAU BOUTON SWITCH EST ICI ---
            afficher_kwh = st.sidebar.toggle(
                "Passer en mode kWh ⚡", 
                value=False, 
                key="unite_toggle" # Mémorisation automatique et robuste !
            )
            
            # On définit l'unité en fonction de la position du switch
            if afficher_kwh:
                unite = "Consommation (kWh)"
            else:
                unite = "Euros (€)"
            
            frequence = st.sidebar.selectbox("Grouper par :", options=["Jour", "Semaine", "Mois"], key="freq_selector")
            freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME"}
            
            # Calculs de base
            df_filtre['Cout_HP'] = df_filtre['Conso_HP'] * prix_hp
            df_filtre['Cout_HC'] = df_filtre['Conso_HC'] * prix_hc
            df_filtre['Abonnement'] = abo_annuel / 365
            
            df_resampled = df_filtre.resample(freq_map[frequence]).agg({
                'Conso_HP': 'sum', 'Conso_HC': 'sum',
                'Cout_HP': 'sum', 'Cout_HC': 'sum', 'Abonnement': 'sum'
            })
            
            # Étiquettes X
            dict_mois = {1: "Jan.", 2: "Fév.", 3: "Mars", 4: "Avr.", 5: "Mai", 6: "Juin", 7: "Juil.", 8: "Août", 9: "Sept.", 10: "Oct.", 11: "Nov.", 12: "Déc."}
            if frequence == "Mois":
                df_resampled['Label_X'] = df_resampled.index.month.map(dict_mois) + " " + df_resampled.index.year.astype(str)
            elif frequence == "Semaine":
                df_resampled['Label_X'] = "Du " + (df_resampled.index - pd.Timedelta(days=6)).strftime('%d/%m') + " au " + df_resampled.index.strftime('%d/%m')
            else:
                df_resampled['Label_X'] = df_resampled.index.strftime('%d/%m/%Y')

            # --- PRÉPARATION DES DONNÉES SELON L'UNITÉ ---
            if unite == "Euros (€)":
                cols_plot = ['Cout_HP', 'Cout_HC', 'Abonnement']
                palette = {'Cout_HP': '#1f77b4', 'Cout_HC': '#2ca02c', 'Abonnement': '#7f7f7f'}
                suffixe = " €"
                format_val = ".2f"
                df_resampled['Total_Affichage'] = df_resampled['Cout_HP'] + df_resampled['Cout_HC'] + df_resampled['Abonnement']
            else:
                cols_plot = ['Conso_HP', 'Conso_HC'] # Pas d'abonnement en kWh
                palette = {'Conso_HP': '#1f77b4', 'Conso_HC': '#2ca02c'}
                suffixe = " kWh"
                format_val = ".1f"
                df_resampled['Total_Affichage'] = df_resampled['Conso_HP'] + df_resampled['Conso_HC']

            # --- TITRE DYNAMIQUE DU HAUT ---
            d_debut = st.session_state.start_date.strftime('%d/%m/%Y')
            d_fin = st.session_state.end_date.strftime('%d/%m/%Y')
            
            if frequence == "Mois":
                nom_mois = liste_mois[st.session_state.start_date.month - 1]
                annee_en_cours = st.session_state.start_date.year
                titre_stats = f"Statistiques de {nom_mois} {annee_en_cours}"
            elif frequence == "Semaine":
                titre_stats = f"Statistiques de la semaine du {d_debut} au {d_fin}"
            else:
                titre_stats = f"Statistiques du {d_debut} au {d_fin}"

            st.subheader(titre_stats)

            # Statistiques
            c1, c2, c3 = st.columns(3)
            c1.metric("Total", f"{df_resampled['Total_Affichage'].sum():{format_val}}{suffixe}")
            c2.metric("Moyenne", f"{df_resampled['Total_Affichage'].mean():{format_val}}{suffixe}")
            c3.metric("Max", f"{df_resampled['Total_Affichage'].max():{format_val}}{suffixe}")

            # Graphique
            df_plot = df_resampled.reset_index()[['Label_X'] + cols_plot].melt(id_vars='Label_X', var_name='Type', value_name='Valeur')
            fig = px.bar(df_plot, x='Label_X', y='Valeur', color='Type', 
                         category_orders={"Type": cols_plot[::-1]},
                         title=f"Analyse en {unite}", color_discrete_map=palette)
            
            fig.update_traces(texttemplate='%{y:' + format_val + '}' + suffixe, textposition="inside", textfont_color="white")
            for _, row in df_resampled.iterrows():
                fig.add_annotation(x=row['Label_X'], y=row['Total_Affichage'], text=f"<b>{row['Total_Affichage']:{format_val}}{suffixe}</b>", showarrow=False, yshift=10)

            fig.update_layout(xaxis_title="Période", yaxis_title=unite, barcornerradius=15)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Voir les données brutes"):
                st.dataframe(df_resampled.drop(columns=['Label_X']).style.format("{:.2f}"))

    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.info("👋 Importez vos CSV pour commencer.")