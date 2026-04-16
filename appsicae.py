import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import calendar
import os # NOUVEAU : Pour vérifier si les fichiers de sauvegarde existent

# --- Configuration ---
st.set_page_config(page_title="Suivi SICAE Expert", layout="wide")
st.title("⚡ Analyse Temporelle de Consommation")

# --- SYSTÈME DE SAUVEGARDE DES TARIFS ---
def charger_tarifs():
    """Charge les tarifs depuis les fichiers de sauvegarde, ou utilise ceux par défaut."""
    # Tarifs par défaut (Février 2026)
    data_prix_defaut = {
        "Contrat": ["Option Base", "Option HP/HC", "Option HP/HC"],
        "Type": ["Prix Unique", "Heures Pleines", "Heures Creuses"],
        "Prix (€/kWh)": [0.1899, 0.1991, 0.1557]
    }
    data_abo_defaut = {
        "Puissance (kVA)": [6, 9, 12, 15, 18, 24, 30, 36],
        "Option Base (€)": [218.21, 261.68, 305.16, 348.06, 389.66, 479.49, 568.60, 657.14],
        "Option HP/HC (€)": [220.95, 266.81, 313.68, 358.52, 405.10, 505.02, 596.02, 687.73]
    }
    
    # Si des sauvegardes existent, on les utilise !
    if os.path.exists("tarifs_prix.csv") and os.path.exists("tarifs_abo.csv"):
        df_prix = pd.read_csv("tarifs_prix.csv")
        df_abo = pd.read_csv("tarifs_abo.csv")
    else:
        df_prix = pd.DataFrame(data_prix_defaut)
        df_abo = pd.DataFrame(data_abo_defaut)
        
    return df_prix, df_abo

def sauvegarder_tarifs(df_p, df_a):
    """Écrit les tableaux modifiés dans des fichiers CSV locaux."""
    df_p.to_csv("tarifs_prix.csv", index=False)
    df_a.to_csv("tarifs_abo.csv", index=False)

# On charge les bases de données tarifaires en mémoire
df_prix_actuel, df_abo_actuel = charger_tarifs()


# --- BARRE LATÉRALE ---
st.sidebar.header("📋 Mon Contrat")

# 1. LE MENU ADMINISTRATEUR (POPOVER)
with st.sidebar.popover("⚙️ Administration des tarifs", use_container_width=True):
    st.markdown("### Modifier la grille tarifaire")
    st.caption("Modifiez directement les cases ci-dessous et sauvegardez. (Astuce : Entrez vos prix TTC réels facturés)")
    
    st.write("**1. Prix du kWh (€)**")
    # st.data_editor permet de modifier le tableau ! 
    # On bloque (disabled) les colonnes "Contrat" et "Type" pour ne pas casser la logique du code.
    edited_prix = st.data_editor(df_prix_actuel, hide_index=True, disabled=("Contrat", "Type"), use_container_width=True)
    
    st.write("**2. Abonnements Annuels (€)**")
    edited_abo = st.data_editor(df_abo_actuel, hide_index=True, disabled=("Puissance (kVA)",), use_container_width=True)
    
    if st.button("💾 Sauvegarder les nouveaux tarifs", type="primary", use_container_width=True):
        sauvegarder_tarifs(edited_prix, edited_abo)
        st.success("Tarifs mis à jour avec succès !")
        st.rerun() # On recharge l'application pour appliquer les nouveaux prix

# 2. SÉLECTION DU CONTRAT PAR L'UTILISATEUR
type_contrat = st.sidebar.selectbox("Offre tarifaire :", ["Option HP/HC", "Option Base"])
puissance = st.sidebar.selectbox("Puissance souscrite (kVA) :", [6, 9, 12, 15, 18, 24, 30, 36], index=1)

# --- ATTRIBUTION AUTOMATIQUE DES PRIX DEPUIS LES TABLEAUX ---
abo_annuel = df_abo_actuel[df_abo_actuel["Puissance (kVA)"] == puissance][f"{type_contrat} (€)"].values[0]

if type_contrat == "Option HP/HC":
    prix_hp = df_prix_actuel[(df_prix_actuel["Contrat"] == "Option HP/HC") & (df_prix_actuel["Type"] == "Heures Pleines")]["Prix (€/kWh)"].values[0]
    prix_hc = df_prix_actuel[(df_prix_actuel["Contrat"] == "Option HP/HC") & (df_prix_actuel["Type"] == "Heures Creuses")]["Prix (€/kWh)"].values[0]
else:
    prix_unique = df_prix_actuel[(df_prix_actuel["Contrat"] == "Option Base") & (df_prix_actuel["Type"] == "Prix Unique")]["Prix (€/kWh)"].values[0]
    prix_hp = prix_unique
    prix_hc = prix_unique

st.sidebar.info(f"Prix appliqué : HP **{prix_hp:.4f} €** | HC **{prix_hc:.4f} €**\nAbo annuel : **{abo_annuel:.2f} €**")

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
        
        # --- INITIALISATION MÉMOIRE ET LIMITES ---
        date_min_file = df.index.min().date()
        date_max_file = df.index.max().date()

        if 'start_date' not in st.session_state:
            st.session_state.start_date = date_min_file
            st.session_state.end_date = date_max_file
        if 'freq_selector' not in st.session_state:
            st.session_state.freq_selector = "Jour"

        st.session_state.start_date = max(date_min_file, min(st.session_state.start_date, date_max_file))
        st.session_state.end_date = max(date_min_file, min(st.session_state.end_date, date_max_file))

        # --- FILTRES DE PÉRIODE ---
        st.sidebar.subheader("🗓️ Sélection de la période")

        date_range = st.sidebar.date_input(
            "Calendrier :", 
            value=(st.session_state.start_date, st.session_state.end_date), 
            min_value=date_min_file, 
            max_value=date_max_file, 
            format="DD/MM/YYYY", 
            label_visibility="collapsed"
        )
        
        if isinstance(date_range, tuple):
            if len(date_range) == 1:
                st.session_state.start_date = date_range[0]
                st.session_state.end_date = min(date_range[0] + datetime.timedelta(days=6), date_max_file)
                st.session_state.freq_selector = "Jour" 
                st.rerun()
            elif len(date_range) == 2:
                st.session_state.start_date, st.session_state.end_date = date_range

        col_btn_gauche, col_btn_droite = st.sidebar.columns(2)
        if col_btn_gauche.button("◀️", key="prev_semaine", use_container_width=True):
            st.session_state.start_date = max(st.session_state.start_date - datetime.timedelta(days=7), date_min_file)
            st.session_state.end_date = max(st.session_state.end_date - datetime.timedelta(days=7), date_min_file)
            st.rerun()
        if col_btn_droite.button("▶️", key="next_semaine", use_container_width=True):
            st.session_state.start_date = min(st.session_state.start_date + datetime.timedelta(days=7), date_max_file)
            st.session_state.end_date = min(st.session_state.end_date + datetime.timedelta(days=7), date_max_file)
            st.rerun()

        st.sidebar.write("**Sélection par mois :**")
        liste_mois = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        mois_nom = st.sidebar.selectbox("Mois", options=liste_mois, index=st.session_state.start_date.month - 1, label_visibility="collapsed")
        
        annee_sel = st.sidebar.number_input(
            "Année", 
            value=st.session_state.start_date.year, 
            min_value=date_min_file.year, 
            max_value=date_max_file.year, 
            label_visibility="collapsed"
        )

        selected_month_index = liste_mois.index(mois_nom) + 1
        if selected_month_index != st.session_state.start_date.month or annee_sel != st.session_state.start_date.year:
            dernier_jour = calendar.monthrange(annee_sel, selected_month_index)[1]
            new_start = max(datetime.date(annee_sel, selected_month_index, 1), date_min_file)
            new_end = min(datetime.date(annee_sel, selected_month_index, dernier_jour), date_max_file)
            
            st.session_state.start_date = new_start
            st.session_state.end_date = new_end
            st.session_state.freq_selector = "Semaine"
            st.rerun()

        st.sidebar.write("**Années disponibles :**")
        annees_dispo = sorted(df.index.year.unique().tolist()) 
        cols_annees = st.sidebar.columns(len(annees_dispo))
        
        for c, y in zip(cols_annees, annees_dispo):
            if c.button(str(y), use_container_width=True):
                st.session_state.start_date = max(datetime.date(y, 1, 1), date_min_file)
                st.session_state.end_date = min(datetime.date(y, 12, 31), date_max_file)
                st.session_state.freq_selector = "Mois"
                st.rerun()

        st.sidebar.divider()

        # --- LOGIQUE D'AFFICHAGE ---
        df_filtre = df.loc[str(st.session_state.start_date):str(st.session_state.end_date)].copy()

        if not df_filtre.empty:
            st.sidebar.subheader("📊 Affichage")
            
            afficher_kwh = st.sidebar.toggle("Passer en mode kWh ⚡", value=False, key="unite_toggle")
            
            if afficher_kwh:
                unite = "Consommation (kWh)"
            else:
                unite = "Euros (€)"
            
            frequence = st.sidebar.selectbox("Grouper par :", options=["Jour", "Semaine", "Mois"], key="freq_selector")
            freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME"}
            
            df_filtre['Cout_HP'] = df_filtre['Conso_HP'] * prix_hp
            df_filtre['Cout_HC'] = df_filtre['Conso_HC'] * prix_hc
            df_filtre['Abonnement'] = abo_annuel / 365
            
            df_resampled = df_filtre.resample(freq_map[frequence]).agg({
                'Conso_HP': 'sum', 'Conso_HC': 'sum',
                'Cout_HP': 'sum', 'Cout_HC': 'sum', 'Abonnement': 'sum'
            })
            
            dict_mois = {1: "Jan.", 2: "Fév.", 3: "Mars", 4: "Avr.", 5: "Mai", 6: "Juin", 7: "Juil.", 8: "Août", 9: "Sept.", 10: "Oct.", 11: "Nov.", 12: "Déc."}
            if frequence == "Mois":
                df_resampled['Label_X'] = df_resampled.index.month.map(dict_mois) + " " + df_resampled.index.year.astype(str)
            elif frequence == "Semaine":
                df_resampled['Label_X'] = "Du " + (df_resampled.index - pd.Timedelta(days=6)).strftime('%d/%m') + " au " + df_resampled.index.strftime('%d/%m')
            else:
                df_resampled['Label_X'] = df_resampled.index.strftime('%d/%m/%Y')

            if unite == "Euros (€)":
                cols_plot = ['Cout_HP', 'Cout_HC', 'Abonnement']
                palette = {'Cout_HP': '#1f77b4', 'Cout_HC': '#2ca02c', 'Abonnement': '#7f7f7f'}
                suffixe = " €"
                format_val = ".2f"
                df_resampled['Total_Affichage'] = df_resampled['Cout_HP'] + df_resampled['Cout_HC'] + df_resampled['Abonnement']
            else:
                cols_plot = ['Conso_HP', 'Conso_HC'] 
                palette = {'Conso_HP': '#1f77b4', 'Conso_HC': '#2ca02c'}
                suffixe = " kWh"
                format_val = ".1f"
                df_resampled['Total_Affichage'] = df_resampled['Conso_HP'] + df_resampled['Conso_HC']

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

            c1, c2, c3 = st.columns(3)
            c1.metric("Total", f"{df_resampled['Total_Affichage'].sum():{format_val}}{suffixe}")
            c2.metric("Moyenne", f"{df_resampled['Total_Affichage'].mean():{format_val}}{suffixe}")
            c3.metric("Max", f"{df_resampled['Total_Affichage'].max():{format_val}}{suffixe}")

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
