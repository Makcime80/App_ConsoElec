import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import calendar
import os

# --- Configuration ---
st.set_page_config(page_title="Suivi SICAE Expert", layout="wide")
st.title("⚡ Analyse Temporelle de Consommation")

# --- SYSTÈME DE SAUVEGARDE DES TARIFS ---
def charger_tarifs():
    """Charge les tarifs depuis les fichiers de sauvegarde, ou utilise ceux par défaut."""
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

df_prix_actuel, df_abo_actuel = charger_tarifs()


# --- BARRE LATÉRALE ---
st.sidebar.header("📋 Mon Contrat")

# 1. LE MENU ADMINISTRATEUR (POPOVER) SÉCURISÉ
with st.sidebar.popover("⚙️ Administration des tarifs", use_container_width=True):
    st.markdown("### 🔒 Accès Restreint")
    
    # Gestion de la connexion dans le session_state
    if 'admin_ok' not in st.session_state:
        st.session_state.admin_ok = False

    if not st.session_state.admin_ok:
        # Champ de saisie du mot de passe
        code_saisi = st.text_input("Code secret :", type="password")
        if st.button("Déverrouiller", use_container_width=True):
            # CHANGE TON MOT DE PASSE ICI (Garde les guillemets)
            if code_saisi == st.secrets["mot_de_passe_admin"]: 
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Code incorrect ❌")
                
    else:
        # SI CONNECTÉ : Affichage de l'éditeur
        st.success("Mode Édition activé")
        
        st.write("**1. Prix du kWh (€)**")
        edited_prix = st.data_editor(df_prix_actuel, hide_index=True, disabled=("Contrat", "Type"), use_container_width=True)
        
        st.write("**2. Abonnements Annuels (€)**")
        edited_abo = st.data_editor(df_abo_actuel, hide_index=True, disabled=("Puissance (kVA)",), use_container_width=True)
        
        col_save, col_lock = st.columns(2)
        if col_save.button("💾 Sauvegarder", type="primary", use_container_width=True):
            sauvegarder_tarifs(edited_prix, edited_abo)
            st.success("Enregistré !")
            st.session_state.admin_ok = False # On reverrouille après sauvegarde
            st.rerun()
            
        if col_lock.button("🔒 Quitter", use_container_width=True):
            st.session_state.admin_ok = False
            st.rerun()

# 2. SÉLECTION UTILISATEUR
type_contrat = st.sidebar.selectbox("Offre tarifaire :", ["Option HP/HC", "Option Base"])
puissance = st.sidebar.selectbox("Puissance souscrite (kVA) :", [6, 9, 12, 15, 18, 24, 30, 36], index=1)

# Calculs des prix selon sélection
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

# --- IMPORT ET ANALYSE ---
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
        
        # --- FILTRES TEMPORELS ---
        date_min_file = df.index.min().date()
        date_max_file = df.index.max().date()

        if 'start_date' not in st.session_state:
            st.session_state.start_date, st.session_state.end_date = date_min_file, date_max_file
        if 'freq_selector' not in st.session_state:
            st.session_state.freq_selector = "Jour"

        st.sidebar.subheader("🗓️ Sélection de la période")
        date_range = st.sidebar.date_input("Calendrier :", value=(st.session_state.start_date, st.session_state.end_date), 
                                           min_value=date_min_file, max_value=date_max_file, format="DD/MM/YYYY", label_visibility="collapsed")
        
        if isinstance(date_range, tuple) and len(date_range) == 2:
            st.session_state.start_date, st.session_state.end_date = date_range

        # Boutons années automatiques
        st.sidebar.write("**Années disponibles :**")
        annees_dispo = sorted(df.index.year.unique().tolist())
        cols_y = st.sidebar.columns(len(annees_dispo))
        for c, y in zip(cols_y, annees_dispo):
            if c.button(str(y), use_container_width=True):
                st.session_state.start_date, st.session_state.end_date = datetime.date(y, 1, 1), datetime.date(y, 12, 31)
                st.session_state.freq_selector = "Mois"; st.rerun()

        st.sidebar.divider()

        # --- AFFICHAGE GRAPHIQUE ---
        df_filtre = df.loc[str(st.session_state.start_date):str(st.session_state.end_date)].copy()

        if not df_filtre.empty:
            st.sidebar.subheader("📊 Affichage")
            mode_kwh = st.sidebar.toggle("Passer en mode kWh ⚡", value=False)
            unite = "Consommation (kWh)" if mode_kwh else "Euros (€)"
            frequence = st.sidebar.selectbox("Grouper par :", options=["Jour", "Semaine", "Mois"], key="freq_selector")
            
            # Calculs
            df_filtre['Cout_HP'] = df_filtre['Conso_HP'] * prix_hp
            df_filtre['Cout_HC'] = df_filtre['Conso_HC'] * prix_hc
            df_filtre['Abonnement'] = abo_annuel / 365
            
            freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME"}
            df_resampled = df_filtre.resample(freq_map[frequence]).agg({'Conso_HP':'sum','Conso_HC':'sum','Cout_HP':'sum','Cout_HC':'sum','Abonnement':'sum'})
            
            # Formatage X
            df_resampled['Label_X'] = df_resampled.index.strftime('%d/%m/%Y')
            if frequence == "Mois":
                df_resampled['Label_X'] = df_resampled.index.strftime('%b %Y')

            # Plot
            cols_plot = ['Cout_HP', 'Cout_HC', 'Abonnement'] if not mode_kwh else ['Conso_HP', 'Conso_HC']
            palette = {'Cout_HP': '#1f77b4', 'Cout_HC': '#2ca02c', 'Abonnement': '#7f7f7f', 'Conso_HP': '#1f77b4', 'Conso_HC': '#2ca02c'}
            
            df_resampled['Total_Affichage'] = df_resampled[cols_plot].sum(axis=1)
            
            st.subheader(f"Statistiques du {st.session_state.start_date.strftime('%d/%m/%Y')} au {st.session_state.end_date.strftime('%d/%m/%Y')}")
            c1, c2, c3 = st.columns(3)
            suffixe = " kWh" if mode_kwh else " €"
            fmt = ".1f" if mode_kwh else ".2f"
            c1.metric("Total", f"{df_resampled['Total_Affichage'].sum():{fmt}}{suffixe}")
            c2.metric("Moyenne", f"{df_resampled['Total_Affichage'].mean():{fmt}}{suffixe}")
            c3.metric("Max", f"{df_resampled['Total_Affichage'].max():{fmt}}{suffixe}")

            df_p = df_resampled.reset_index()[['Label_X'] + cols_plot].melt(id_vars='Label_X', var_name='Type', value_name='Valeur')
            fig = px.bar(df_p, x='Label_X', y='Valeur', color='Type', color_discrete_map=palette, title=f"Analyse en {unite}")
            fig.update_layout(xaxis_title="Période", yaxis_title=unite, barcornerradius=10)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.info("👋 Importez vos CSV pour commencer.")
