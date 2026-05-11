import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import calendar
import os
import io
from fpdf import FPDF

# --- Configuration ---
st.set_page_config(page_title="Suivi SICAE Expert", layout="wide")
st.title("⚡ Analyse Temporelle de Consommation")

# --- SYSTÈME DE SAUVEGARDE DES TARIFS ---
def charger_tarifs():
    """Définit les tarifs directement dans le code."""
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
    
    df_prix = pd.DataFrame(data_prix_defaut)
    df_abo = pd.DataFrame(data_abo_defaut)
        
    return df_prix, df_abo

df_prix_actuel, df_abo_actuel = charger_tarifs()

def generer_pdf(fig, df_table, periode_str, unite):
    """Génère un PDF contenant le graphique et le tableau de données."""
    pdf = FPDF()
    pdf.add_page()
    
    # Nettoyage de l'unité pour le PDF (remplacement de € par EUR)
    unite_pdf = unite.replace("€", "EUR")
    periode_str = periode_str.replace("€", "EUR")
    
    # Titre
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Rapport d'Analyse de Consommation Electrique", ln=True, align="C")
    
    # Période
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, f"Periode : {periode_str}", ln=True, align="C")
    pdf.ln(5)
    
    # Graphique (Conversion Plotly -> PNG)
    try:
        img_bytes = fig.to_image(format="png", width=1000, height=500, scale=2)
        img_stream = io.BytesIO(img_bytes)
        pdf.image(img_stream, x=10, y=35, w=190)
    except Exception as e:
        pdf.set_font("helvetica", "I", 10)
        pdf.cell(0, 10, f"(Graphique non disponible : {e})", ln=True)
    
    # Tableau de données
    pdf.set_y(145) # Se positionne sous le graphique
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Detail des donnees ({unite_pdf})", ln=True)
    
    pdf.set_font("helvetica", "B", 8)
    # Entêtes du tableau
    cols = ["Periode"] + list(df_table.columns)
    col_width = 190 / len(cols)
    for col in cols:
        pdf.cell(col_width, 8, col.replace("€", "EUR"), border=1, align="C")
    pdf.ln()
    
    # Lignes du tableau
    pdf.set_font("helvetica", "", 7)
    for index, row in df_table.iterrows():
        # On vérifie si on arrive en bas de page
        if pdf.get_y() > 260:
            pdf.add_page()
        
        pdf.cell(col_width, 7, str(index).replace("€", "EUR"), border=1)
        for val in row:
            pdf.cell(col_width, 7, str(val).replace("€", "EUR"), border=1, align="R")
        pdf.ln()
        
    return pdf.output()


# --- BARRE LATÉRALE ---
st.sidebar.header("📋 Mon Contrat")

# 2. SÉLECTION UTILISATEUR
type_contrat = st.sidebar.selectbox("Offre tarifaire :", ["Option HP/HC", "Option Base"])
puissance = st.sidebar.selectbox("Puissance souscrite (kVA) :", [6, 9, 12, 15, 18, 24, 30, 36], index=0)

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
            # Lecture brute sans conversion de date
            df_temp = pd.read_csv(fichier, sep=";", header=1, encoding="latin1")
            df_temp = df_temp[['Date', 'Consommation (kWh)', 'Consommation (kWh).1']].copy()
            df_temp.columns = ['Date', 'Conso_HC', 'Conso_HP']
            liste_df.append(df_temp)
            
        # Concaténation de tous les fichiers
        df = pd.concat(liste_df, ignore_index=True)
        
        # Conversion vectorisée des dates (plus rapide)
        df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
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
        if 'mode_kwh' not in st.session_state:
            st.session_state.mode_kwh = False

        # --- GESTION DU MODE kWh / EUROS ---
        st.sidebar.subheader("📊 Affichage")
        mode_kwh = st.sidebar.toggle("Passer en mode kWh ⚡", key="mode_kwh_toggle", value=st.session_state.mode_kwh)
        st.session_state.mode_kwh = mode_kwh
        unite = "Consommation (kWh)" if mode_kwh else "Euros (€)"

        st.sidebar.subheader("🗓️ Sélection de la période")
        
        # Boutons de navigation rapide
        col_prev, col_next = st.sidebar.columns(2)
        duration = (st.session_state.end_date - st.session_state.start_date).days
        
        if col_prev.button("⬅️ Précédent", use_container_width=True):
            if duration > 20:
                st.session_state.start_date = (pd.to_datetime(st.session_state.start_date) - pd.DateOffset(months=1)).date()
                st.session_state.end_date = (pd.to_datetime(st.session_state.end_date) - pd.DateOffset(months=1)).date()
            else:
                st.session_state.start_date -= datetime.timedelta(days=7)
                st.session_state.end_date -= datetime.timedelta(days=7)
            
            # Recalcul de l'affichage auto
            new_delta = (st.session_state.end_date - st.session_state.start_date).days
            if new_delta <= 6: st.session_state.freq_selector = "Jour"
            elif new_delta <= 60: st.session_state.freq_selector = "Semaine"
            else: st.session_state.freq_selector = "Mois"
            st.rerun()
            
        if col_next.button("Suivant ➡️", use_container_width=True):
            if duration > 20:
                st.session_state.start_date = (pd.to_datetime(st.session_state.start_date) + pd.DateOffset(months=1)).date()
                st.session_state.end_date = (pd.to_datetime(st.session_state.end_date) + pd.DateOffset(months=1)).date()
            else:
                st.session_state.start_date += datetime.timedelta(days=7)
                st.session_state.end_date += datetime.timedelta(days=7)
                
            # Recalcul de l'affichage auto
            new_delta = (st.session_state.end_date - st.session_state.start_date).days
            if new_delta <= 6: st.session_state.freq_selector = "Jour"
            elif new_delta <= 60: st.session_state.freq_selector = "Semaine"
            else: st.session_state.freq_selector = "Mois"
            st.rerun()

        date_selection = st.sidebar.date_input("Calendrier :", 
                                               value=(st.session_state.start_date, st.session_state.end_date), 
                                               min_value=date_min_file, max_value=date_max_file, 
                                               format="DD/MM/YYYY", label_visibility="collapsed")
        
        # Logique intelligente de sélection
        # Logique intelligente de sélection
        if isinstance(date_selection, (list, tuple)) and len(date_selection) == 2:
            start, end = date_selection
            
            # Si la sélection a changé par rapport à la session
            if start != st.session_state.start_date or end != st.session_state.end_date:
                st.session_state.start_date = start
                st.session_state.end_date = end
                
                delta = (end - start).days
                
                # 1. Gestion du double-clic (Sélection de 1 jour -> Expansion à 7 jours)
                if delta == 0:
                    end = min(start + datetime.timedelta(days=6), date_max_file)
                    st.session_state.end_date = end
                    delta = (end - start).days # On recalcule la durée
                
                # 2. Ajustement automatique du groupement (Grouper par)
                if delta <= 6: # 7 jours ou moins
                    st.session_state.freq_selector = "Jour"
                elif delta <= 60:
                    st.session_state.freq_selector = "Semaine"
                else:
                    st.session_state.freq_selector = "Mois"
                
                st.rerun()

        # Boutons années automatiques
        st.sidebar.write("**Années disponibles :**")
        annees_dispo = sorted(df.index.year.unique().tolist())
        cols_y = st.sidebar.columns(len(annees_dispo))
        for c, y in zip(cols_y, annees_dispo):
            if c.button(str(y), key=f"btn_{y}", use_container_width=True):
                # On bride les dates pour qu'elles restent dans les limites du fichier CSV
                st.session_state.start_date = max(datetime.date(y, 1, 1), date_min_file)
                st.session_state.end_date = min(datetime.date(y, 12, 31), date_max_file)
                st.session_state.freq_selector = "Mois"
                st.rerun()

        st.sidebar.divider()

        # --- AFFICHAGE GRAPHIQUE ---
        df_filtre = df.loc[str(st.session_state.start_date):str(st.session_state.end_date)].copy()

        if not df_filtre.empty:
            frequence = st.sidebar.selectbox("Grouper par :", options=["Jour", "Semaine", "Mois"], key="freq_selector")
            
            # Calculs
            df_filtre['Cout_HP'] = df_filtre['Conso_HP'] * prix_hp
            df_filtre['Cout_HC'] = df_filtre['Conso_HC'] * prix_hc
            df_filtre['Abonnement'] = abo_annuel / 365
            
            freq_map = {"Jour": "D", "Semaine": "W", "Mois": "ME"}
            df_resampled = df_filtre.resample(freq_map[frequence]).agg({'Conso_HP':'sum','Conso_HC':'sum','Cout_HP':'sum','Cout_HC':'sum','Abonnement':'sum'})
            
            # Formatage X
            df_resampled['Label_X'] = df_resampled.index.strftime('%d/%m/%Y')
            if frequence == "Semaine":
                # On affiche "Sem. du [Début] au [Fin]" bridé par la sélection réelle
                def formater_semaine(x):
                    debut_semaine = (x - datetime.timedelta(days=6)).date()
                    fin_semaine = x.date()
                    # On s'assure que le label ne dépasse pas la sélection de l'utilisateur
                    vrai_debut = max(debut_semaine, st.session_state.start_date)
                    vrai_fin = min(fin_semaine, st.session_state.end_date)
                    return f"Du {vrai_debut.strftime('%d/%m')} au {vrai_fin.strftime('%d/%m/%Y')}"
                
                df_resampled['Label_X'] = df_resampled.index.map(formater_semaine)
            elif frequence == "Mois":
                df_resampled['Label_X'] = df_resampled.index.strftime('%b %Y')

            # Plot
            cols_plot = ['Abonnement', 'Cout_HC', 'Cout_HP'] if not mode_kwh else ['Conso_HC', 'Conso_HP']
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
            # Ajout du symbole € si on est en mode Euros
            if not mode_kwh:
                df_p['Texte_Label'] = df_p['Valeur'].apply(lambda x: f"{x:.2f} €")
            else:
                df_p['Texte_Label'] = df_p['Valeur'].apply(lambda x: f"{x:.1f}")
            
            fig = px.bar(df_p, x='Label_X', y='Valeur', color='Type', color_discrete_map=palette, 
                         title=f"Analyse en {unite}", text='Texte_Label')
            
            # Ajout des totaux au-dessus des colonnes
            df_total = df_resampled.reset_index()
            if not mode_kwh:
                labels_total = [f"{v:.2f} €" for v in df_total['Total_Affichage']]
            else:
                labels_total = [f"{v:.1f}" for v in df_total['Total_Affichage']]
                
            fig.add_scatter(
                x=df_total['Label_X'],
                y=df_total['Total_Affichage'],
                mode='text',
                text=labels_total,
                textposition='top center',
                showlegend=False,
                hoverinfo='skip'
            )

            fig.update_layout(xaxis_title="Période", yaxis_title=unite, barcornerradius=10)
            st.plotly_chart(fig, use_container_width=True)

            # --- TABLEAU DE DONNÉES RÉCAPITULATIF ---
            with st.expander("📄 Voir le détail des données", expanded=True):
                df_table = df_resampled.copy()
                # On utilise les labels propres pour l'index du tableau
                df_table.set_index('Label_X', inplace=True)
                df_table.index.name = "Période"
                
                cols_display = cols_plot + ['Total_Affichage']
                
                # Formatage pour l'affichage
                if not mode_kwh:
                    for col in cols_display:
                        df_table[col] = df_table[col].map(lambda x: f"{x:.2f} €")
                else:
                    for col in cols_display:
                        df_table[col] = df_table[col].map(lambda x: f"{x:.1f} kWh")
                
                st.dataframe(df_table[cols_display], use_container_width=True)

                # --- BOUTONS D'EXPORT ---
                st.divider()
                col_exp1, col_exp2 = st.columns(2)
                
                # Export CSV simple
                csv = df_table[cols_display].to_csv(sep=';').encode('utf-8-sig')
                col_exp1.download_button("📥 Télécharger CSV", data=csv, file_name="export_sicae.csv", mime="text/csv", use_container_width=True)
                
                # Export PDF complet
                if col_exp2.button("📄 Générer Rapport PDF", use_container_width=True):
                    with st.spinner("Génération du PDF en cours..."):
                        periode_label = f"du {st.session_state.start_date.strftime('%d/%m/%Y')} au {st.session_state.end_date.strftime('%d/%m/%Y')}"
                        pdf_data = generer_pdf(fig, df_table[cols_display], periode_label, unite)
                        st.download_button("📥 Télécharger le PDF", data=bytes(pdf_data), file_name="rapport_sicae.pdf", mime="application/pdf", use_container_width=True)

    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.info("👋 Importez vos CSV pour commencer.")
