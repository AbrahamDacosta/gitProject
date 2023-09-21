import streamlit as st
import pandas as pd
import base64
import io
import time
import traceback

# Définir le style CSS personnalisé
custom_css = """
<style>
body {
    color: #333333;
    background-color: #ffffff;
    font-family: 'sans-serif';
}

.stButton>button {
    background-color: #009688;
    color: #ffffff;
}

.stTextInput>div>div>input {
    background-color: #ffffff;
    color: #333333;
}

.sidebar .sidebar-content {
    background-color: #00ff00;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Compteur global pour générer des clés uniques
compteur = 0

def get_unique_key(prefix):
    global compteur
    key = f"{prefix}_{compteur}"
    compteur += 1
    return key


def import_and_match_transactions_payin():
    st.header("Importation et Matching des Transactions de Paiement")

    # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))

    # Charger le fichier des transactions succès dans notre Back Office
    fichier_back_office = st.file_uploader("Sélectionnez le fichier des transactions succès dans notre Back Office", type=['xlsx', '.csv'], key=get_unique_key("fichier_back_office"))

    if fichier_operateur is not None and fichier_back_office is not None:
        try:
            # Charger les données des fichiers Excel
            df_operateur = pd.read_excel(fichier_operateur, engine='openpyxl')
            df_back_office = pd.read_excel(fichier_back_office, engine='openpyxl')

            # Filtrer dans le fichier opérateur les transactions "Successfully Processed Transaction" uniquement
            df_operateur = df_operateur[df_operateur['ResponseMessage'] == 'Successfully Processed Transaction']

            # Supprimer les virgules et convertir la colonne 'TransactionId' en entiers
            df_operateur['TransactionId'] = df_operateur['TransactionId'].str.replace(',', '').astype(int)
            df_operateur.dropna(subset=['TransactionId'], inplace=True)
            df_operateur['TransactionId'] = df_operateur['TransactionId'].astype(int)

            # Filtrer dans le fichier Back Office les transactions avec l'état "SUCCES" uniquement
            df_back_office = df_back_office[df_back_office['ETAT TRANSACTION'] == 'SUCCES']

            # Effectuer le matching entre les colonnes 'MSISDN' du premier DataFrame et 'TELEPHONE' du deuxième DataFrame
            matched_df = pd.merge(df_operateur, df_back_office, left_on='MSISDN', right_on='TELEPHONE', how='outer', indicator=True)

            # Filtrer les transactions correspondantes
            internes_df = matched_df[matched_df['_merge'] == 'both']

            # Filtrer les transactions non correspondantes (écarts)
            ecarts_df = matched_df[matched_df['_merge'] == 'left_only']

            if ecarts_df.empty:
                # Aucun écart, afficher les transactions internes
                st.subheader("Aucun écart trouvé, voici les transactions internes :")
                st.write(internes_df)
            else:
                # Télécharger le fichier des écarts
                st.subheader("Télécharger le fichier des écarts")
                excel_data_ecarts = io.BytesIO()
                with pd.ExcelWriter(excel_data_ecarts, engine='xlsxwriter') as writer:
                    ecarts_df.to_excel(writer, index=False)
                excel_data_ecarts.seek(0)
                b64_ecarts = base64.b64encode(excel_data_ecarts.read()).decode()
                href_ecarts = f'<a href="data:application/octet-stream;base64,{b64_ecarts}" download="ecarts_test_mtn.xlsx">Télécharger le fichier des écarts</a>'
                st.markdown(href_ecarts, unsafe_allow_html=True)

                # Télécharger le fichier du résultat du matching (quel que soit le résultat)
                st.subheader("Télécharger le fichier des transactions internes")
                excel_data_internes = io.BytesIO()
                with pd.ExcelWriter(excel_data_internes, engine='xlsxwriter') as writer:
                    internes_df.to_excel(writer, index=False)
                excel_data_internes.seek(0)
                b64_internes = base64.b64encode(excel_data_internes.read()).decode()
                href_internes = f'<a href="data:application/octet-stream;base64,{b64_internes}" download="transactions_internes.xlsx">Télécharger le fichier des transactions internes</a>'
                st.markdown(href_internes, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())
            

# ... (le reste du code reste inchangé)

# Fonction pour réaliser le TCD interne
# Fonction pour vérifier si la valeur est un nombre
def is_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

# Fonction pour fractionner la colonne 'Amount'
def fractionner_amount(amount):
    try:
        amount_str = str(amount)
        if is_number(amount_str):
            return amount_str.split('.')[-1]
        else:
            return ''
    except:
        return ''

# Fonction pour réaliser le TCD interne
def tcd_interne(df):
    try:
        # Pour extraire uniquement la date de la colonne StartDateTime
        df['StartDateTime'] = pd.to_datetime(df['StartDateTime']).dt.date

        # Appliquer la fonction de fractionnement à la colonne 'Amount'
        df['Amount'] = df['Amount'].apply(fractionner_amount)

        # Convertir la colonne 'ID PAIEMENT' en nombre entier
        df['ID PAIEMENT'] = df['ID PAIEMENT'].astype(int)
    except KeyError:
        pass

    # Créer le TCD interne
    tcd_interne = pd.pivot_table(df, index=['StartDateTime'], values=['Amount'], aggfunc={'Amount': ['count', 'sum']}, fill_value=0)

    # Renommer les colonnes du TCD
    tcd_interne.columns = ['Nombre de Montant', 'Somme de Montant']

    # Calculer la colonne 'Somme des Frais' en soustrayant 'Nombre de Montant' de 'Somme de Montant'
    #tcd_interne['Somme des Frais'] = tcd_interne['Somme de Montant'] - tcd_interne['Nombre de Montant']

    # Appliquer une couleur gradient au TCD
    tcd_interne = tcd_interne.style.background_gradient(cmap='YlGnBu')

    return tcd_interne



    
    
# Créer une fonction pour importer les fichiers des écarts et des transactions en échec
def import_ecarts_and_en_echec_payin():
    # Charger le fichier des écarts
    fichier_ecarts = st.file_uploader("Sélectionnez le fichier des écarts", type=['xlsx', '.csv'], key=get_unique_key("fichier_ecarts"))
    
    # Charger le fichier des transactions en échec
    fichier_en_echec = st.file_uploader("Sélectionnez le fichier des transactions en échec", type=['xlsx', '.csv'], key=get_unique_key("fichier_en_echec"))
    
    if fichier_ecarts is not None and fichier_en_echec is not None:
        try:
            # Charger les données des fichiers Excel
            df_ecarts = pd.read_excel(fichier_ecarts)
            df_en_echec = pd.read_excel(fichier_en_echec)
            
            # Vérifier si la colonne 'External Transaction Id' est présente dans le fichier des écarts
            if 'External Transaction Id' not in df_ecarts.columns:
                # Si la colonne n'existe pas, créer une nouvelle colonne 'External Transaction Id'
                # en concaténant les colonnes 'StartDateTime' et 'MONTANT' dans le fichier des écarts
                df_ecarts['External Transaction Id'] = df_ecarts['StartDateTime'].astype(str) + df_ecarts['MONTANT'].astype(str)
            
            # Vérifier si la colonne 'External Transaction Id' est présente dans le fichier des transactions en échec
            if 'External Transaction Id' not in df_en_echec.columns:
                # Si la colonne n'existe pas, créer une nouvelle colonne 'External Transaction Id'
                # en concaténant les colonnes 'CREATION', 'MONTANT', et 'TELEPHONE' dans le fichier des transactions en échec
                df_en_echec['External Transaction Id'] = df_en_echec['CREATION'].astype(str) + df_en_echec['MONTANT'].astype(str) + df_en_echec['TELEPHONE'].astype(str)

            # Effectuer le Matching des colonnes
            matched_df = pd.merge(df_ecarts, df_en_echec, left_on='External Transaction Id', right_on='CUSTOM 6', how='inner')
            
            # Enregistrer les écarts dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                matched_df.to_excel(writer, index=False)
            excel_data.seek(0)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts.xlsx">Télécharger le fichier des écarts</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

            # Afficher les résultats
            st.subheader("Résultats")
            st.write(matched_df)

        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")


def recherchev():
    st.header("Étape 3: Exécuter la RECHERCHEV")
    
    # Charger le fichier des écarts
    st.subheader("Fichier des écarts")
    fichier_ecarts = st.file_uploader("Sélectionnez le fichier des écarts", type=['xlsx', '.csv'], key=get_unique_key("fichier_ecarts"))
    
    # Charger le fichier des transactions en échec
    st.subheader("Fichier des transactions en échec")
    fichier_en_echec = st.file_uploader("Sélectionnez le fichier des transactions en échec", type=['xlsx', '.csv'], key=get_unique_key("fichier_en_echec"))
    
    # Charger le fichier des transactions en succès chez l'opérateur
    st.subheader("Fichier des transactions en succès chez l'opérateur")
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions en succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    if fichier_ecarts is not None and fichier_en_echec is not None and fichier_operateur is not None:
        try:
            # Charger les données des fichiers Excel
            df_ecarts = pd.read_excel(fichier_ecarts)
            df_en_echec = pd.read_excel(fichier_en_echec)
            df_operateur = pd.read_excel(fichier_operateur)
            
            # Effectuer le matching entre la colonne "Référence" du tableau des écarts et la colonne "CUSTOM 6" des transactions en échec
            matched_df = pd.merge(df_ecarts, df_en_echec, left_on='External Transaction Id', right_on='External Transaction Id', how='left')
            
            # Utiliser la fonction RECHERCHEV pour trouver les éléments "ID TRANSACTION" et "SITE ID" dans les transactions en échec de CinetPay
            matched_df['ID TRANSACTION'] = matched_df['External Transaction Id'].apply(lambda x: df_en_echec.loc[df_en_echec['ID TRANSACTION'] == x, 'ID TRANSACTION'].values[0] if not pd.isnull(x) and not df_en_echec.loc[df_en_echec['ID TRANSACTION'] == x].empty else '')
            matched_df['SITE_ID'] = matched_df['External Transaction Id'].apply(lambda x: df_en_echec.loc[df_en_echec['ID TRANSACTION'] == x, 'SITE ID'].values[0] if not pd.isnull(x) and not df_en_echec.loc[df_en_echec['ID TRANSACTION'] == x].empty else '')
            
            # Effectuer le matching entre la colonne "Référence" du tableau des écarts et la colonne "External Transaction Id" du fichier de l'opérateur en succès
            matched_df = pd.merge(matched_df, df_operateur[['External Transaction Id', 'Date', 'HEURE']], left_on='External Transaction Id', right_on='External Transaction Id', how='left')
            
            # Enregistrer les écarts mis à jour dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                matched_df.to_excel(writer, index=False)
            excel_data.seek(0)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts_mis_a_jour.xlsx">Télécharger le fichier des écarts mis à jour</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

            # Afficher les résultats
            st.subheader("Résultats")
            st.write(matched_df)

        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")


# Créer une fonction pour réaliser le TCD des transactions en succès chez l'opérateur
def tcd_transactions_success_payin():
    # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    if fichier_operateur is not None:
        try:
            # Charger les données des transactions en succès de l'opérateur dans un DataFrame
            df_transactions_success = pd.read_excel(fichier_operateur)

            # Convertir la colonne 'Date' en format de date si nécessaire
            df_transactions_success['Date'] = pd.to_datetime(df_transactions_success['Date'])

            # Créer le TCD en utilisant la méthode pivot_table()
            tcd = pd.pivot_table(df_transactions_success, index=['Date'], values=['Montant'], aggfunc={'Montant': ['count', 'sum']}, fill_value=0)

            # Renommer les colonnes du TCD
            tcd.columns = ['Nombre de Montant', 'Somme de Montant']

            # Calculer la colonne 'Somme des Frais' en soustrayant 'Nombre de Montant' de 'Somme de Montant'
            tcd['Somme des Frais'] = tcd['Somme de Montant'] - tcd['Nombre de Montant']

            # Afficher les résultats
            st.subheader("Résultats")
            st.write(tcd)
        except Exception as e:
            st.error(f"Erreur lors du traitement du fichier : {str(e)}")
            
         
            
# Fonction pour créer l'External Transaction Id pour le fichier opérateur
#def create_external_transaction_id_operateur(row):
 #   if row['Opérateur'] in ['Orange GN', 'Orange CI', 'Orange BF', 'Orange ML', 'Orange SN']:
  #      return f"{row['Destinataire']}_{row['Créé']}_{row['Montant']}_{row['Heure']}"
   # else:
    #    return f"{row['Destinataire']}_{row['Créé']}_{row['Montant']}"

#def create_external_transaction_id_cinetpay(row):
 #   if row['Opérateur'] not in ['Orange GN', 'Orange CI', 'Orange BF', 'Orange ML', 'Orange SN']:
  #      return f"{row['Numéro']}_{row['Crée le']}_{row['Montant']}"
   # else:
    #    return f"{row['Numéro']}_{row['Crée le']}_{row['Montant']}"

#def create_external_transaction_id(df_row, columns_mapping):
 #   id_parts = [df_row[column] for column in columns_mapping]
  #  return ''.join(str(part) for part in id_parts)

# Fonction pour choisir automatiquement les colonnes pour le numéro de compte et le montant
#def choose_columns_for_operator_file(df):
 #   numero_columns = ["Destinataire", "N° de Compte2"]
  #  montant_columns = ["Montant", "Crédit", "Débit"]
    
   # numero_column = next((col for col in numero_columns if col in df.columns), None)
    #montant_column = next((col for col in montant_columns if col in df.columns), None)
    
   # return numero_column, montant_column
    










# Fonction pour créer une colonne "External Transaction Id" en fonction des colonnes spécifiques du fichier opérateur
#def create_external_transaction_id_operateur(row):
    # Si la colonne "Opérateur" existe, utilisez-la pour créer l'ID
   # if 'Opérateur' in row.index:
    #    operateur = str(row['Opérateur'])
    #else:
        # Sinon, utilisez la fonction d'identification de l'opérateur à partir du numéro de téléphone
     #   operateur = str(identify_operator_from_phone_number(row['N° de Compte2']))  # Remplacez 'N° de Compte2' par le nom de la colonne appropriée

    #montant = str(row['Montant'])  # Remplacez 'Montant' par le nom de la colonne appropriée
    #date = str(row['Créé'])  # Remplacez 'Créé' par le nom de la colonne appropriée
    #heure = str(row['Heure'])  # Remplacez 'Heure' par le nom de la colonne appropriée
    
    #return operateur + montant + date + heure

# Appliquer la fonction pour créer la colonne "External Transaction Id" dans le fichier opérateur



def import_and_match_transactions_orange_magma_payin():
       # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    # Charger le fichier des transactions succès dans notre Back Office
    fichier_back_office = st.file_uploader("Sélectionnez le fichier des transactions succès dans notre Back Office", type=['xlsx', '.csv'], key=get_unique_key("fichier_back_office"))
    
    if fichier_operateur is not None and fichier_back_office is not None:
        try:
            # Charger les données des fichiers Excel
            df_operateur = pd.read_excel(fichier_operateur)
            df_back_office = pd.read_excel(fichier_back_office)
            
            
            # Filtrer la colonne "Traitant" pour ne garder que les transactions en "Orange CI (API MAGMA)"
            df_back_office = df_back_office[df_back_office['Traitant'] == 'Orange CI (API MAGMA)']
            
            # Effectuer le matching entre la colonne "Référence" du premier DataFrame et la colonne "ID PAIEMENT" du deuxième DataFrame
            matched_df = pd.merge(df_operateur, df_back_office, left_on='TransactionID', right_on='slug', how='left', indicator=True)
            
            # Filtrer les transactions non correspondantes
            non_matched_df = matched_df[matched_df['_merge'] == 'left_only']
            
            # Télécharger le fichier des écarts
            st.subheader("Télécharger le fichier des écarts")
            st.write(non_matched_df)
           # Enregistrer les écarts dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                non_matched_df.to_excel(writer, index=False)
            excel_data.seek(0)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts_orange_magma.xlsx">Télécharger le fichier des écarts</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

            
        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())
            
            
            



# Créer une fonction pour réaliser le TCD des transactions en succès chez l'opérateur
import streamlit as st
import pandas as pd
import io
import base64
import traceback

import streamlit as st
import pandas as pd
import io
import base64
import traceback

def tcd_transactions_success_magma_payin():
    # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    if fichier_operateur is not None:
        try:
            # Charger les données des transactions en succès de l'opérateur dans un DataFrame
            df_transactions_success = pd.read_excel(fichier_operateur)

            # Convertir la colonne 'Date' en format de date si nécessaire
            df_transactions_success['Date'] = pd.to_datetime(df_transactions_success['Created At'])
            
            # Extraire la date courte (jour-mois-année)
            df_transactions_success['Date_Courte'] = df_transactions_success['Date'].dt.strftime('%d-%m-%Y')

            # Calculer le count par date
            count_by_date = df_transactions_success.groupby('Date_Courte')['Amount'].count()

            # Calculer la somme par date
            sum_by_date = df_transactions_success.groupby('Date_Courte')['Amount'].sum()

            # Calculer la colonne 'Somme des Frais' en soustrayant le count du sum
            sum_frais_by_date = sum_by_date - count_by_date

            # Fusionner les résultats dans un DataFrame
            tcd = pd.DataFrame({'Nombre de Montant': count_by_date, 'Somme de Montant': sum_by_date, 'Somme des Frais': sum_frais_by_date})

            # Enregistrer le TCD dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                tcd.to_excel(writer, index=True)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.getvalue()).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="tcd_transactions_success.xlsx">Télécharger le TCD des transactions succès</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

            # Afficher le TCD
            st.subheader("TCD des transactions succès chez l'opérateur")
            st.write(tcd)

        except Exception as e:
            st.error(f"Erreur lors du traitement du fichier : {str(e)}")               
            st.error(traceback.format_exc())

# Votre fonction get_unique_key() ici (non fournie dans le code donné)
def get_unique_key(key_name):
    # Implémentez votre fonction pour générer une clé unique en fonction du nom donné
    pass


# Votre fonction get_unique_key() ici (non fournie dans le code donné)
def get_unique_key(key_name):
    # Implémentez votre fonction pour générer une clé unique en fonction du nom donné
    pass






            
#----------------------------------------------------------------------------------------------------------------------------------------
# Fonction pour créer l'External Transaction Id pour le fichier opérateur
def create_external_transaction_id_operateur(row):
    if  row['Operator']  in ['Orange_GN', 'Orange_CI', 'Orange_BF', 'Orange_ML', 'Orange_SN']:
        return f"{row['Receiver']}_{row['Created At']}_{row['Amount']}_{row['Heure']}"
    else:
        return f"{row['Receiver']}_{row['Created At']}_{row['Amount']}"

def create_external_transaction_id_cinetpay(row):
    if row['Opérateur'] not in ['Orange GN', 'Orange CI', 'Orange BF', 'Orange ML', 'Orange SN']:
        return f"{row['Numéro']}_{row['Date']}_{row['Montant']}"
    else:
        return f"{row['Numéro']}_{row['Crée le']}_{row['Montant']}"
    
def create_external_transaction_id_échec(row):
    
        return f"{row['TELEPHONE']}_{row['CREATION']}_{row['HEURE']}_{row['MONTANT']}"    

def import_and_match_transactions_orange_payin():
    # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    # Charger le fichier des transactions succès dans notre Back Office
    fichier_back_office = st.file_uploader("Sélectionnez le fichier des transactions succès dans notre Back Office", type=['xlsx', '.csv'], key=get_unique_key("fichier_back_office"))
    
    # Charger le fichier des transactions succès chez l'opérateur
    fichier_échec = st.file_uploader("Sélectionnez le fichier des transactions en échec chez cinetpay", type=['xlsx', '.csv'], key=get_unique_key("fichier_échec"))
    
    if fichier_operateur is not None and fichier_back_office is not None:
        try:
            # Charger les données des fichiers Excel
            df_operateur = pd.read_excel(fichier_operateur)
            df_back_office = pd.read_excel(fichier_back_office)
            fichier_échec= pd.read_excel(fichier_échec)
            # Créer une colonne "External Transaction Id" dans le fichier opérateur
            df_operateur['External Transaction Id'] = df_operateur.apply(create_external_transaction_id_operateur, axis=1)
            
            # Créer une colonne "External Transaction Id" dans le fichier des transactions à succès chez CinetPay
            df_back_office['External Transaction Id'] = df_back_office.apply(create_external_transaction_id_cinetpay, axis=1)
            
            # Créer une colonne "External Transaction Id" dans le fichier des transactions en échec
            fichier_échec['External Transaction Id'] = fichier_échec.apply(create_external_transaction_id_échec, axis=1)


            # Enregistrer les informations du fichier opérateur avec la nouvelle colonne "External Transaction Id" dans un nouveau fichier
            new_operator_file = df_operateur.copy()
            excel_data_operator = io.BytesIO()
            with pd.ExcelWriter(excel_data_operator, engine='xlsxwriter') as writer:
                new_operator_file.to_excel(writer, index=False)
            excel_data_operator.seek(0)
            
            # Enregistrer les informations du fichier des transactions à succès chez CinetPay avec la nouvelle colonne "External Transaction Id" dans un nouveau fichier
            new_cinetpay_file = df_back_office.copy()
            excel_data_cinetpay = io.BytesIO()
            with pd.ExcelWriter(excel_data_cinetpay, engine='xlsxwriter') as writer:
                new_cinetpay_file.to_excel(writer, index=False)
            excel_data_cinetpay.seek(0)
            
            # Enregistrer les informations du fichier des transactions en échec chez CinetPay avec la nouvelle colonne "External Transaction Id" dans un nouveau fichier
            new_échec_file = fichier_échec.copy()
            excel_data_échec = io.BytesIO()
            with pd.ExcelWriter(excel_data_échec, engine='xlsxwriter') as writer:
                new_échec_file.to_excel(writer, index=False)
            excel_data_échec.seek(0)
            
            # Télécharger les nouveaux fichiers
            st.subheader("Télécharger le fichier des transactions succès chez l'opérateur avec la colonne 'External Transaction Id'")
            st.download_button("Télécharger", data=excel_data_operator.getvalue(), file_name='new_operator_file.xlsx')
            
            st.subheader("Télécharger le fichier des transactions succès chez CinetPay avec la colonne 'External Transaction Id'")
            st.download_button("Télécharger", data=excel_data_cinetpay.getvalue(), file_name='new_cinetpay_file.xlsx')
            
            st.subheader("Télécharger le fichier des transactions en échec chez CinetPay avec la colonne 'External Transaction Id'")
            st.download_button("Télécharger", data=excel_data_échec.getvalue(), file_name='new_échec_file.xlsx')
            
        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())
         
            
                        
# Créer une fonction pour importer les fichiers et réaliser le matching des transactions succès
def NBSI_transactions_orange_payin():
    # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    # Charger le fichier des transactions succès dans notre Back Office
    fichier_back_office = st.file_uploader("Sélectionnez le fichier des transactions succès dans notre Back Office", type=['xlsx', '.csv'], key=get_unique_key("fichier_back_office"))
    
    if fichier_operateur is not None and fichier_back_office is not None:
        try:
            # Charger les données des fichiers Excel
            df_operateur = pd.read_excel(fichier_operateur)
            df_back_office = pd.read_excel(fichier_back_office)
            
            # Effectuer le matching entre la colonne "Référence" du premier DataFrame et la colonne "ID PAIEMENT" du deuxième DataFrame
            matched_df = pd.merge(df_operateur, df_back_office, left_on='TransactionID', right_on='slug', how='left', indicator=True)
            
            # Filtrer les transactions non correspondantes
            non_matched_df = matched_df[matched_df['_merge'] == 'left_only']
            
            
             # Enregistrer les informations du fichier opérateur avec la nouvelle colonne "External Transaction Id" dans un nouveau fichier
            écart_file = non_matched_df.copy()
            excel_data_écarts = io.BytesIO()
            with pd.ExcelWriter(excel_data_écarts, engine='xlsxwriter') as writer:
                 écart_file.to_excel(writer, index=False)
            excel_data_écarts.seek(0)
            
            # Télécharger le fichier des écarts
            st.subheader("Télécharger le fichier des écarts")
            st.write(non_matched_df)
            st.download_button("Télécharger", data=excel_data_écarts.read(), file_name='ecarts_test_mtn.xlsx')
        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")            
            

# Fonction pour réaliser le TCD interne des écarts
def tcd_interne_1(df):
    # Faites ici le TCD interne en fonction de votre besoin
    # Par exemple, vous pouvez utiliser la fonction pivot_table de pandas
    # Pour des exemples d'utilisation de la fonction pivot_table, consultez la documentation de pandas :
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.pivot_table.html
    tcd_result = df.pivot_table(index=['StartDateTime', 'Amount'],aggfunc={'Amount': ['count', 'sum']}, fill_value=0)
    # Renommer les colonnes du TCD
    tcd_result.columns = ['Étiquettes de lignes','Nombre de Montant', 'Somme de Montant']
    
    # Calculer la colonne 'Somme des Frais' en soustrayant 'Nombre de Montant' de 'Somme de Montant'
    tcd_result['Somme des Frais'] = tcd_result['Somme de Montant'] - tcd_result['Nombre de Montant']
    
    # Appliquer une couleur gradient au TCD
    tcd_colored = tcd_result.style.background_gradient(cmap='YlGnBu')
    return tcd_result


def import_ecarts_and_en_echec_orange_payin():
    # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
     # Charger le fichier des transactions écarts
    fichier_écart = st.file_uploader("Sélectionnez le fichier des écarts succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_écart"))

    # Charger le fichier des transactions succès dans notre Back Office
    fichier_en_échec = st.file_uploader("Sélectionnez le fichier des transactions en échec dans notre Back Office", type=['xlsx', '.csv'], key=get_unique_key("fichier_en_échec"))

    if fichier_operateur is not None and fichier_en_échec is not None:
        try:
            # Charger les données des fichiers Excel
            fichier_operateur = pd.read_excel(fichier_operateur)
            fichier_en_échec = pd.read_excel(fichier_en_échec)
            fichier_écart=pd.read_excel(fichier_écart)

            # Vérifier s'il y a des écarts (différence de lignes entre les deux fichiers)
            is_ecart = len(fichier_écart) < len(fichier_operateur)

            if is_ecart:
                # Créer une colonne External Transaction Id dans le fichier des transactions en échec chez l'opérateur
              # Créer une colonne External Transaction Id dans le fichier des transactions en échec chez l'opérateur
                fichier_écart['External Transaction Id'] = fichier_écart['Receiver'].astype(str) + fichier_écart['Created At'].astype(str) + fichier_écart['Amount'].astype(str)

                # Créer une colonne External Transaction Id dans le fichier des transactions succès chez notre Back Office
                fichier_en_échec['External Transaction Id'] = fichier_en_échec['TELEPHONE'].astype(str) + fichier_en_échec['DATE PAIEMENT'].astype(str) + fichier_en_échec['MONTANT'].astype(str)

                # Faire le matching des colonnes External Transaction Id
                #matched_df = pd.merge(fichier_écart, fichier_en_échec[['External Transaction Id', 'ID TRANSACTION', 'SITE_ID']], on='External Transaction Id', how='left')
                # Créer des listes pour stocker les valeurs de SITE ID et ID TRANSACTION
                site_ids = []
                id_transactions = []

                # Parcourir les transactions du fichier des écarts
                for index, row in fichier_écart.iterrows():
                    reference = row['External Transaction Id']
                    
                    # Rechercher la correspondance dans le fichier des transactions en échec
                    match = fichier_en_échec[fichier_en_échec['External Transaction Id'] == reference]
                    
                    if not match.empty:
                        site_id = match['SITE_ID'].values[0]
                        id_transaction = match['ID TRANSACTION'].values[0]
                    else:
                        site_id = ''
                        id_transaction = ''
                        
                    
                    # Ajouter les valeurs dans les listes
                    site_ids.append(site_id)
                    id_transactions.append(id_transaction)

                # Ajouter les listes de valeurs au DataFrame des écarts
                fichier_écart['SITE_ID'] = site_ids
                fichier_écart['ID TRANSACTION'] = id_transactions


                # Faire la RECHERCHEV pour compléter les informations manquantes dans les écarts
                # ...

                # Enregistrer les écarts dans un fichier Excel
                excel_data_ecarts = io.BytesIO()
                with pd.ExcelWriter(excel_data_ecarts, engine='xlsxwriter') as writer:
                    fichier_écart.to_excel(writer, index=False)
                excel_data_ecarts.seek(0)

                # Générer le lien de téléchargement
                b64 = base64.b64encode(excel_data_ecarts.read()).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts.xlsx">Télécharger le fichier des écarts</a>'

                # Afficher le lien de téléchargement
                st.markdown(href, unsafe_allow_html=True)

                # Afficher les résultats
                st.subheader("Résultats")
                st.write(fichier_écart)

            else:
                # Réaliser le TCD interne car il n'y a pas d'écarts
                tcd_interne_result = tcd_interne_1(fichier_écart)

                # Enregistrer le TCD interne dans un fichier Excel
                excel_data_tcd = io.BytesIO()
                with pd.ExcelWriter(excel_data_tcd, engine='xlsxwriter') as writer:
                    tcd_interne_result.to_excel(writer)
                excel_data_tcd.seek(0)

                # Télécharger le fichier du TCD interne
                st.subheader("Télécharger le fichier du TCD interne")
                st.download_button("Télécharger", data=excel_data_tcd.getvalue(), file_name='tcd_interne.xlsx')

        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())

#def identifier_colonne_numero(dataframe):
    # Recherche dans les noms de colonnes les termes associés au numéro (ajuster la liste si besoin)
 #   mots_cles_numero = ['Numéro', 'Numero', 'N°', 'NumeroTel', 'Telephone', 'Phone']
  #  for nom_colonne in dataframe.columns:
   #     for mot_cle in mots_cles_numero:
    #        if mot_cle.lower() in nom_colonne.lower():
     #           return nom_colonne
    #raise ValueError("Impossible de trouver la colonne 'Numéro' dans le fichier opérateur")

#def identifier_colonne_identifiant(dataframe):
    # Recherche dans les noms de colonnes les termes associés à l'identifiant (ajuster la liste si besoin)
 #   mots_cles_identifiant = ['CUSTOM 6', 'Identifiant', 'ID', 'Transaction ID']
  #  for nom_colonne in dataframe.columns:
   #     for mot_cle in mots_cles_identifiant:
    #        if mot_cle.lower() in nom_colonne.lower():
     #           return nom_colonne
    #raise ValueError("Impossible de trouver la colonne d'identifiant dans le fichier des transactions à succès chez CinetPay")
# Le reste du code reste inchangé

# Fonction create_external_transaction_id_operateur reste inchangée
# Fonction create_external_transaction_id_cinetpay reste inchangée
"""
ICI IL S'AGIT DE CREER LA LOGIQUE POUR ORANGE MONEY PAYIN POUR TOUS LES PAYS
"""
                        
def import_and_match_transactions_orange_money_payin():
       # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    # Charger le fichier des transactions succès dans notre Back Office
    fichier_back_office = st.file_uploader("Sélectionnez le fichier des transactions succès dans notre Back Office", type=['xlsx', '.csv'], key=get_unique_key("fichier_back_office"))
    
    if fichier_operateur is not None and fichier_back_office is not None:
        try:
            # Charger les données des fichiers Excel
            df_operateur = pd.read_excel(fichier_operateur)
            df_back_office = pd.read_excel(fichier_back_office)
            
            # Effectuer le matching entre la colonne "Référence" du premier DataFrame et la colonne "ID PAIEMENT" du deuxième DataFrame
            matched_df = pd.merge(df_operateur, df_back_office, left_on='Référence', right_on='ID PAIEMENT', how='left', indicator=True)
            
            # Filtrer les transactions non correspondantes
            non_matched_df = matched_df[matched_df['_merge'] == 'left_only']
            
            # Télécharger le fichier des écarts
            st.subheader("Télécharger le fichier des écarts")
            st.write(non_matched_df)
           # Enregistrer les écarts dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                non_matched_df.to_excel(writer, index=False)
            excel_data.seek(0)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts_orange.xlsx">Télécharger le fichier des écarts</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

            
        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())
            
            

# Créer une fonction pour importer les fichiers des écarts et des transactions en échec
def import_ecarts_and_en_echec_orange_money_payin():
    st.header("Étape 3: NBSI DES ECART")
    
    # Charger le fichier des écarts
    st.subheader("Fichier des écarts")
    fichier_ecarts = st.file_uploader("Sélectionnez le fichier des écarts", type=['xlsx', '.csv'], key=get_unique_key("fichier_ecarts"))
    
    # Charger le fichier des transactions en échec
    st.subheader("Fichier des transactions en échec")
    fichier_en_echec = st.file_uploader("Sélectionnez le fichier des transactions en échec", type=['xlsx', '.csv'], key=get_unique_key("fichier_en_echec"))
    
    # Charger le fichier des transactions en succès chez l'opérateur
    #st.subheader("Fichier des transactions en succès chez l'opérateur")
    #fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions en succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    if fichier_ecarts is not None and fichier_en_echec is not None :
        try:
            # Charger les données des fichiers Excel
            df_ecarts = pd.read_excel(fichier_ecarts)
            df_en_echec = pd.read_excel(fichier_en_echec)
            #df_operateur = pd.read_excel(fichier_operateur)
            
            # Effectuer le matching entre la colonne "Référence" du tableau des écarts et la colonne "CUSTOM 6" des transactions en échec
            matched_df = pd.merge(df_ecarts, df_en_echec, left_on='Référence', right_on='CUSTOM 6', how='left')
            
            # Utiliser la fonction RECHERCHEV pour trouver les éléments "ID TRANSACTION" et "SITE ID" dans les transactions en échec de CinetPay
            matched_df['ID TRANSACTION'] = matched_df['Référence'].apply(lambda x: df_en_echec.loc[df_en_echec['ID TRANSACTION'] == x, 'ID TRANSACTION'].values[0] if not pd.isnull(x) and not df_en_echec.loc[df_en_echec['ID TRANSACTION'] == x].empty else '')
            matched_df['SITE_ID'] = matched_df['Référence'].apply(lambda x: df_en_echec.loc[df_en_echec['ID TRANSACTION'] == x, 'SITE_ID'].values[0] if not pd.isnull(x) and not df_en_echec.loc[df_en_echec['ID TRANSACTION'] == x].empty else '')
            
            # Effectuer le matching entre la colonne "Référence" du tableau des écarts et la colonne "External Transaction Id" du fichier de l'opérateur en succès
            #matched_df = pd.merge(matched_df, df_operateur, left_on='Référence', right_on='CUSTOM 6', how='left')
            
            # Enregistrer les écarts mis à jour dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                matched_df.to_excel(writer, index=False)
            excel_data.seek(0)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts_mis_a_jour.xlsx">Télécharger le fichier des écarts mis à jour</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

            # Afficher les résultats
            st.subheader("Résultats")
            st.write(matched_df)

        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())

          
def recherchev_orange_money_payin():
    st.header("Étape 3: Exécuter la RECHERCHEV")
    
    # Charger le fichier des écarts
    st.subheader("Fichier des écarts")
    fichier_ecarts = st.file_uploader("Sélectionnez le fichier des écarts", type=['xlsx', '.csv'], key=get_unique_key("fichier_ecarts"))
    
    # Charger le fichier des transactions en échec
    st.subheader("Fichier des transactions en échec")
    fichier_en_echec = st.file_uploader("Sélectionnez le fichier des transactions en échec", type=['xlsx', '.csv'], key=get_unique_key("fichier_en_echec"))
    
    # Charger le fichier des transactions en succès chez l'opérateur
    st.subheader("Fichier des transactions en succès chez l'opérateur")
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions en succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    if fichier_ecarts is not None and fichier_en_echec is not None and fichier_operateur is not None:
        try:
            # Charger les données des fichiers Excel
            df_ecarts = pd.read_excel(fichier_ecarts)
            df_en_echec = pd.read_excel(fichier_en_echec)
            df_operateur = pd.read_excel(fichier_operateur)
            
            # Créer une colonne "External Transaction Id" pour le fichier des écarts en concaténant les colonnes N° de Compte2, Crédit, Date et Heure
            df_ecarts['External Transaction Id'] = df_ecarts['N° de Compte2'].astype(str) + df_ecarts['Crédit'].astype(str) + df_ecarts['Date'].astype(str) + df_ecarts['Heure'].astype(str)
            
            # Créer une colonne "External Transaction Id" pour le fichier du back office en échec en concaténant les colonnes TELEPHONE, MONTANT, CREATION
            df_en_echec['Cinetpay Transaction Id'] = df_en_echec['TÉLÉPHONE'].astype(str) + df_en_echec['MONTANT'].astype(str) + df_en_echec['CREATION'].astype(str)+df_en_echec['heure'].astype(str)
            st.write(df_en_echec)
            # Effectuer le matching entre la colonne "Référence" du tableau des écarts et la colonne "External Transaction Id" du fichier de l'opérateur en succès
           # matched_df = pd.merge(df_ecarts, df_operateur[['External Transaction Id', 'ID TRANSACTION', 'SITE ID']], left_on='Référence', right_on='External Transaction Id', how='left')
                    
            # Convertir la colonne 'Référence' du fichier des écarts en type de données compatible
            df_ecarts['External Transaction Id'] = df_ecarts['External Transaction Id'].astype(str)
            
            # Fusionner les DataFrames des écarts et des transactions en échec
            merged_df = pd.merge(df_ecarts, df_en_echec, left_on='External Transaction Id', right_on='Cinetpay Transaction Id', how='left')
            st.write(merged_df)
            # Sélectionner les colonnes nécessaires
            selected_columns = ['ID TRANSACTION', 'SITE_ID', 'CPM_RESULT', 'Référence', 'Date', 'heure']
            result_table = merged_df[selected_columns].copy()

            # Renommer les colonnes
            result_table.columns = ['ID transaction', 'Site ID', 'Résultat Paiement', 'Opérateur Transaction ID', 'Date Paiement', 'Heure Paiement']
            
             #Ajout du datafrale dans le fichier de rapport
            #maj_df.to_excel(excel_file, sheet_name="template - CINETPAY", index = None)
            
            # Enregistrer les écarts mis à jour dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                result_table.to_excel(writer, index=False)
            excel_data.seek(0)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts_mis_a_jour.xlsx">Télécharger le fichier des écarts mis à jour</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

            # Afficher les résultats
            st.subheader("Résultats")
            st.write(result_table)

        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())


# Créer une fonction pour réaliser le TCD des transactions en succès chez l'opérateur
def tcd_transactions_success_orange_money_payin():
    # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    if fichier_operateur is not None:
        try:
            # Charger les données des transactions en succès de l'opérateur dans un DataFrame
            df_transactions_success = pd.read_excel(fichier_operateur)

            # Convertir la colonne 'Date' en format de date si nécessaire
            df_transactions_success['Date'] = pd.to_datetime(df_transactions_success['Date'])
            #convertir la colonne date en date courte
            df_transactions_success['Date_courte']=df_transactions_success['Date'].dt.strftime('%d-%m-%Y')
            #formater le montant
           # df_transactions_success['Crédit']= df_transactions_success['Crédit'].apply(lambda x: "{:.2f}".format(x).rstrip('0').rstrip('.'))
            #Calculer le count par date
            count_by_date=df_transactions_success.groupby('Date_courte')['Crédit'].count()
            #calculer la somme par date
            sum_by_date=df_transactions_success.groupby('Date_courte')['Crédit'].sum()
            #On fusionne le résultat dans un dataframe
            tcd = pd.DataFrame({'Nombre de Montant': count_by_date, 'Somme de Montant': sum_by_date})

            # Enregistrer le TCD dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                tcd.to_excel(writer, index=True)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.getvalue()).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="tcd_orange_transactions_success.xlsx">Télécharger le TCD des transactions succès</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

            # Afficher le TCD
            st.subheader("TCD des transactions succès chez l'opérateur")
            st.write(tcd)

           
        except Exception as e:
            st.error(f"Erreur lors du traitement du fichier : {str(e)}")   
            st.error(traceback.format_exc())
            
"""
ICI IL S'AGIT DE CREER LA LOGIQUE POUR TOGO MONEY PAYIN POUR TOUS LES PAYS

"""         




def import_and_match_transactions_togo_money_payin():
    # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))

    # Charger le fichier des transactions succès dans notre Back Office
    fichier_back_office = st.file_uploader("Sélectionnez le fichier des transactions succès dans notre Back Office", type=['xlsx', '.csv'], key=get_unique_key("fichier_back_office"))

    if fichier_operateur is not None and fichier_back_office is not None:
        try:
            # Charger les données des fichiers Excel ou CSV
            if fichier_operateur.name.endswith('.xlsx'):
                df_operateur = pd.read_excel(fichier_operateur, engine='openpyxl')
            else:
                df_operateur = pd.read_csv(fichier_operateur)

            if fichier_back_office.name.endswith('.xlsx'):
                df_back_office = pd.read_excel(fichier_back_office, engine='openpyxl')
            else:
                df_back_office = pd.read_csv(fichier_back_office)

            # Convertir la colonne "Transaction Id" en nombre entier en remplaçant les valeurs non valides par NaN
            #df_operateur['Transaction Id'] = pd.to_numeric(df_operateur['Transaction Id'], errors='coerce')

            # Filtrer les lignes contenant NaN dans la colonne "Transaction Id"
            #df_operateur = df_operateur.dropna(subset=['Transaction Id'])
            
            # Convertir la colonne "Transaction Id" en nombre entier
            #df_back_office['Transaction Id'] = df_back_office['Transaction Id'].astype(int)


            # Filtrer la colonne "Type" pour ne garder que les transactions de type "sell"
            df_operateur = df_operateur[df_operateur['Type'] == 'sell']

            # Filtrer la colonne "State" pour ne garder que les transactions en "Completed"
            df_operateur = df_operateur[df_operateur['State'] == 'Completed']

            # Fractionner la colonne "Amount" pour enlever les zéros après le point
            df_operateur['Amount'] = df_operateur['Amount'].apply(lambda x: '{:.3f}'.format(float(x)))

            # Filtrer la colonne "ETAT TRANSACTION" pour ne garder que les transactions en "SUCCES"
            df_back_office = df_back_office[df_back_office['ETAT TRANSACTION'] == 'SUCCES']

            # Convertir la colonne "Transaction Id" en nombre entier
            #df_back_office['ID PAIEMENT'] = df_back_office['ID PAIEMENT'].astype(int)

            # Faire le matching entre la colonne 'Transaction Id' du premier DataFrame et la colonne 'ID PAIEMENT' du deuxième DataFrame
            #merged_df = pd.merge(df_operateur, df_back_office, left_on='Transaction Id', right_on='ID PAIEMENT', how='left', indicator=True)
            merged_df=df_operateur[(df_operateur["Transaction Id"].isin(df_back_office["ID PAIEMENT"]) == False)] 
            
            # Filtrer les transactions non correspondantes (en écart)
            #non_matched_df = merged_df[merged_df['_merge'] == 'left_only']

            # Télécharger le fichier des écarts
            st.subheader("Télécharger le fichier des écarts")
            st.write(merged_df)

            # Enregistrer les écarts dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                merged_df.to_excel(writer, index=False)
            excel_data.seek(0)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts_TMONEY.xlsx">Télécharger le fichier des écarts</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())
            
            

# Créer une fonction pour importer les fichiers des écarts et des transactions en échec
def import_ecarts_and_en_echec_togo_money_payin():
      # Charger le fichier de l'opérateur
    #fichier_operateur = st.file_uploader("Sélectionnez le fichier de l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    # Charger le fichier des écarts
    fichier_ecarts = st.file_uploader("Sélectionnez le fichier des écarts", type=['xlsx', '.csv'], key=get_unique_key("fichier_ecarts"))
    
    # Charger le fichier des transactions en échec
    fichier_en_echec = st.file_uploader("Sélectionnez le fichier des transactions en échec", type=['xlsx', '.csv'], key=get_unique_key("fichier_en_echec"))
    
    if fichier_ecarts is not None and fichier_en_echec is not None:
        try:
            # Charger les données des fichiers Excel into Pandas DataFrames
            #df_operateur = pd.read_excel(fichier_operateur)
            df_en_echec = pd.read_excel(fichier_en_echec)
            df_en_écart = pd.read_excel(fichier_ecarts)

            # Vérifier s'il y a des écarts (différence de lignes entre les deux fichiers)
            #is_ecart = len(df_en_écart) < len(df_operateur)

            #if is_ecart:
            df_en_écart['Initiator'] = df_en_écart['Initiator'].astype(str)
            df_en_écart['Date'] = df_en_écart['Date'].astype(str)
            #df_en_écart['HEURE'] = df_en_écart['HEURE'].astype(str)
                #df_en_écart['Amount.1'] = df_en_écart['Amount.1'].astype(str)

                # Créer une nouvelle DataFrame pour les écarts
            new_df_ecarts = pd.DataFrame(df_en_écart)
                
                # Modifier les colonnes spécifiques pour créer la colonne "External Transaction Id"
            new_df_ecarts['External Transaction Id'] = new_df_ecarts['Initiator'] + new_df_ecarts['Date']
                
            df_en_echec['TÉLÉPHONE'] = df_en_echec['TÉLÉPHONE'].astype(str)
            df_en_echec['CREATION'] = df_en_echec['CREATION'].astype(str)
                #df_en_echec['MONTANT'] = df_en_echec['MONTANT'].astype(str)
               

                # Créer une colonne External Transaction Id dans le fichier des transactions succès chez notre Back Office
                #df_en_echec['External Transaction Id'] = df_en_echec['TELEPHONE'].str.cat([
                #    df_en_echec['DATE PAIEMENT'], df_en_echec['MONTANT']
               # ], sep='')
            df_en_echec['External Transaction Id'] = df_en_echec['TÉLÉPHONE'].astype(str) + df_en_echec['CREATION'].astype(str) 
                

                # Faire le matching des colonnes External Transaction Id
            matched_df = pd.merge(new_df_ecarts, df_en_echec[['External Transaction Id', 'ID TRANSACTION', 'SITE_ID']], on='External Transaction Id', how='left')

                # Faire la RECHERCHEV pour compléter les informations manquantes dans les écarts
                # ...

                # Enregistrer les écarts dans un fichier Excel
            excel_data_ecarts = io.BytesIO()
            with pd.ExcelWriter(excel_data_ecarts, engine='xlsxwriter') as writer:
                matched_df.to_excel(writer, index=False)
            excel_data_ecarts.seek(0)

                # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data_ecarts.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts.xlsx">Télécharger le fichier des écarts</a>'

                # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

                # Afficher les résultats
            st.subheader("Résultats")
            st.write(matched_df)

           # else:
                # Réaliser le TCD interne car il n'y a pas d'écarts
               # tcd_interne_result = tcd_interne_1(df_en_echec)

                # Enregistrer le TCD interne dans un fichier Excel
                #excel_data_tcd = io.BytesIO()
                #with pd.ExcelWriter(excel_data_tcd, engine='xlsxwriter') as writer:
                    #tcd_interne_result.to_excel(writer)
               # excel_data_tcd.seek(0)

                # Télécharger le fichier du TCD interne
                #st.subheader("Télécharger le fichier du TCD interne")
               # st.download_button("Télécharger", data=excel_data_tcd.getvalue(), file_name='tcd_interne.xlsx')

        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())

          

def recherchev_togo_money_payin():
    st.header("Étape 3: Exécuter la RECHERCHEV")
    
    # Charger le fichier des écarts
    st.subheader("Fichier des écarts")
    fichier_ecarts = st.file_uploader("Sélectionnez le fichier des écarts", type=['xlsx', '.csv'], key=get_unique_key("fichier_ecarts"))
    
    # Charger le fichier des transactions en échec
    st.subheader("Fichier des transactions en échec")
    fichier_en_echec = st.file_uploader("Sélectionnez le fichier des transactions en échec", type=['xlsx', '.csv'], key=get_unique_key("fichier_en_echec"))
    
    # Charger le fichier des transactions en succès chez l'opérateur
    #st.subheader("Fichier des transactions en succès chez l'opérateur")
    #fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions en succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    if fichier_ecarts is not None and fichier_en_echec is not None :
        try:
            # Charger les données des fichiers Excel
            df_ecarts = pd.read_excel(fichier_ecarts)
            df_en_echec = pd.read_excel(fichier_en_echec)
           # df_operateur = pd.read_excel(fichier_operateur)
            
            # Créer une colonne "External Transaction Id" pour le fichier des écarts en concaténant les colonnes N° de Compte2, Crédit, Date et Heure
            df_ecarts['External Transaction Id'] = df_ecarts['Initiator'].astype(str) + df_ecarts['Amount'].astype(str) + df_ecarts['Date'].astype(str) + df_ecarts['heure'].astype(str)
            
            # Créer une colonne "External Transaction Id" pour le fichier du back office en échec en concaténant les colonnes TELEPHONE, MONTANT, CREATION
            df_en_echec['Cinetpay Transaction Id'] = df_en_echec['TÉLÉPHONE'].astype(str) + df_en_echec['MONTANT'].astype(str) + df_en_echec['CREATION'].astype(str) + df_en_echec['heure'].astype(str)
            st.write(df_en_echec)
            # Effectuer le matching entre la colonne "Référence" du tableau des écarts et la colonne "External Transaction Id" du fichier de l'opérateur en succès
            #matched_df = pd.merge(df_ecarts, df_en_echec[['External Transaction Id', 'ID TRANSACTION', 'SITE ID']], left_on='External Transaction Id', right_on='Cinetpay Transaction Id', how='left')
                    
            # Convertir la colonne 'Référence' du fichier des écarts en type de données compatible
            df_ecarts['External Transaction Id'] = df_ecarts['External Transaction Id'].astype(str)
            
            # Fusionner les DataFrames des écarts et des transactions en échec
            merged_df = pd.merge(df_ecarts, df_en_echec, left_on='External Transaction Id', right_on='Cinetpay Transaction Id', how='left')
            st.write(merged_df)
            
            # Substituer les valeurs 'NA' par 'ACCEPTED' dans la colonne 'CPM_RESULT'
            merged_df['CPM_RESULT'] = merged_df['CPM_RESULT'].replace('NA', 'ACCEPTED')
            # Sélectionner les colonnes nécessaires
            selected_columns = ['ID TRANSACTION', 'SITE_ID', 'CPM_RESULT', 'Transaction Id', 'Date']
            result_table = merged_df[selected_columns].copy()

            # Renommer les colonnes
            result_table.columns = ['ID transaction', 'Site ID', 'Résultat Paiement', 'Opérateur Transaction ID', 'Date Paiement']
            
             #Ajout du datafrale dans le fichier de rapport
            #maj_df.to_excel(excel_file, sheet_name="template - CINETPAY", index = None)
            
            # Enregistrer les écarts mis à jour dans un fichier Excel
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                result_table.to_excel(writer, index=False)
            excel_data.seek(0)

            # Générer le lien de téléchargement
            b64 = base64.b64encode(excel_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="ecarts_mis_a_jour.xlsx">Télécharger le fichier des écarts mis à jour</a>'

            # Afficher le lien de téléchargement
            st.markdown(href, unsafe_allow_html=True)

            # Afficher les résultats
            st.subheader("Résultats")
            st.write(result_table)

        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())


# Créer une fonction pour réaliser le TCD des transactions en succès chez l'opérateur
def tcd_transactions_success_togo_money_payin():
    # Charger le fichier des transactions succès chez l'opérateur
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions succès chez l'opérateur", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))
    
    if fichier_operateur is not None:
        try:
            # Charger les données des transactions en succès de l'opérateur dans un DataFrame
            df_transactions_success = pd.read_excel(fichier_operateur)

            # Convertir la colonne 'Date' en format de date si nécessaire
            df_transactions_success['Date'] = pd.to_datetime(df_transactions_success['Date'])

            # Créer le TCD en utilisant la méthode pivot_table()
            tcd = pd.pivot_table(df_transactions_success, index=['Date'], values=['Crédit'], aggfunc={'Crédit': ['count', 'sum']}, fill_value=0)

            # Renommer les colonnes du TCD
            tcd.columns = ['Nombre de Montant', 'Somme de Montant']

            # Calculer la colonne 'Somme des Frais' en soustrayant 'Nombre de Montant' de 'Somme de Montant'
            tcd['Somme des Frais'] = tcd['Somme de Montant'] - tcd['Nombre de Montant']

            # Afficher les résultats
            st.subheader("Résultats")
            st.write(tcd)
        except Exception as e:
            st.error(f"Erreur lors du traitement du fichier : {str(e)}")  
            

def import_orange_pendings_bo_payout():
    # Charger le fichier des pendings
    fichier_pending = st.file_uploader("Sélectionnez le fichier des pendings", type=['xlsx', '.csv'], key=get_unique_key("fichier_pending"))

    # Charger le fichier des transactions en échec
    fichier_operateur = st.file_uploader("Sélectionnez le fichier des transactions en échec", type=['xlsx', '.csv'], key=get_unique_key("fichier_operateur"))

    if fichier_pending is not None and fichier_operateur is not None:
        try:
            # Charger les données des fichiers Excel into Pandas DataFrames
            df_pending = pd.read_excel(fichier_pending)
            df_operateur = pd.read_excel(fichier_operateur)

            # Vérifier si les colonnes existent dans les DataFrames
            required_columns_pending = ['mobile_recepteur', 'created_at', 'montant_transfert']
            required_columns_operateur = ['N° de Compte2', 'Date', 'Débit']

            if all(column in df_pending.columns for column in required_columns_pending) and all(column in df_operateur.columns for column in required_columns_operateur):
                # Créer une nouvelle colonne "External Transaction Id" dans le DataFrame df_pending
                df_pending['mobile_recepteur'] = df_pending['mobile_recepteur'].str[-3:]  # Récupérer les 3 derniers caractères
                df_pending['created_at'] = df_pending['created_at']
                df_pending['montant_transfert'] = df_pending['montant_transfert']
                df_pending['External Transaction Id'] = df_pending['mobile_recepteur'] + df_pending['created_at'] + df_pending['montant_transfert']

                # Créer une nouvelle colonne "External Transaction Id" dans le DataFrame df_operateur
                df_operateur['N° de Compte2'] = df_operateur['N° de Compte2']
                df_operateur['Date'] = df_operateur['Date']
                df_operateur['Débit'] = df_operateur['Débit']
                df_operateur['External Transaction Id'] = df_operateur['N° de Compte2'] + df_operateur['Date'] + df_operateur['Débit']

                # Faire le matching des colonnes "External Transaction Id" entre les deux DataFrames
                matched_df = pd.merge(df_pending, df_operateur[['External Transaction Id', 'ID TRANSACTION', 'SITE_ID']], on='External Transaction Id', how='left')

                # Filtrer les transactions correspondantes
                transactions_correspondantes = matched_df.dropna(subset=['ID TRANSACTION'])

                # Filtrer les transactions en échec (non correspondantes)
                transactions_en_echec = matched_df[matched_df['ID TRANSACTION'].isnull()]

                # Enregistrer les transactions en échec dans un fichier Excel
                excel_data_en_echec = io.BytesIO()
                with pd.ExcelWriter(excel_data_en_echec, engine='xlsxwriter') as writer:
                    transactions_en_echec.to_excel(writer, index=False)
                excel_data_en_echec.seek(0)

                # Générer le lien de téléchargement pour le fichier des transactions en échec
                b64_en_echec = base64.b64encode(excel_data_en_echec.read()).decode()
                href_en_echec = f'<a href="data:application/octet-stream;base64,{b64_en_echec}" download="transactions_en_echec.xlsx">Télécharger le fichier des transactions en échec</a>'

                # Afficher le lien de téléchargement
                st.markdown(href_en_echec, unsafe_allow_html=True)

                # Afficher les résultats
                st.subheader("Transactions Correspondantes")
                st.write(transactions_correspondantes)
            else:
                st.warning("Les colonnes 'mobile_recepteur', 'created_at' et 'montant_transfert' doivent exister dans le DataFrame des pendings.")
                st.warning("Les colonnes 'N° de Compte2', 'Date' et 'Débit' doivent exister dans le DataFrame des transactions en échec.")
        except Exception as e:
            st.error(f"Erreur lors du traitement des fichiers : {str(e)}")
            st.error(traceback.format_exc())


 
            
            

# Créer la page MTN PAYIN
def mtn_payin_page():
    st.title("MTN PAYIN")
    st.header("Page MTN PAYIN")
    st.subheader("Importation des fichiers et matching des transactions succès")
    
    # Dictionnaire associant chaque option à une fonction
    options = {
        'NBSI_OP': import_and_match_transactions_payin,
        'NBSI_ECART': import_ecarts_and_en_echec_payin,
        'RECHERCHEV': recherchev,
        'TCD': tcd_transactions_success_payin
    }
    
    # Affichage de la liste déroulante
    selected_option = st.selectbox('Sélectionnez une option', list(options.keys()), key=get_unique_key("selectbox"))
    
    # Appel de la fonction correspondante à l'option sélectionnée
    option_function = options[selected_option]
    option_function()



# Créer la page ORANGE PAYIN
def orange_payin_magma_page():
    st.title("ORANGE PAYIN MAGMA")
    st.header("Page ORANGE PAYIN")
    st.subheader("Importation des fichiers et matching des transactions succès")
    
    # Dictionnaire associant chaque option à une fonction
    options = {
        'Option 1': import_and_match_transactions_orange_magma_payin,
        'Option 2': tcd_transactions_success_magma_payin
    }
    
    # Affichage de la liste déroulante
    selected_option = st.selectbox('Sélectionnez une option', list(options.keys()), key=get_unique_key("selectbox"))
    
    # Appel de la fonction correspondante à l'option sélectionnée
    option_function = options[selected_option]
    option_function()
    
# Créer la page ORANGE PAYIN
def orange_money_payin_page():
    st.title("ORANGE MONEY PAYIN ")
    st.header("Page ORANGE MONEY PAYIN")
    st.subheader("Importation des fichiers et matching des transactions succès")
    
    # Dictionnaire associant chaque option à une fonction
    options = {
        'Option 1': import_and_match_transactions_orange_money_payin,
        'Option 2': import_ecarts_and_en_echec_orange_money_payin,
        'Option 3': recherchev_orange_money_payin,
        'Option 4': tcd_transactions_success_orange_money_payin
    }
    
    # Affichage de la liste déroulante
    selected_option = st.selectbox('Sélectionnez une option', list(options.keys()), key=get_unique_key("selectbox"))
    
    # Appel de la fonction correspondante à l'option sélectionnée
    option_function = options[selected_option]
    option_function()    
    
    
# Créer la page TMONEY PAYIN
def TOGO_money_payin_page():
    st.title("TOGO MONEY PAYIN ")
    st.header("Page TMONEY PAYIN")
    st.subheader("Importation des fichiers et matching des transactions succès")
    
    # Dictionnaire associant chaque option à une fonction
    options = {
        'Option 1': import_and_match_transactions_togo_money_payin,
        'Option 2': import_ecarts_and_en_echec_togo_money_payin,
        'Option 3': recherchev_togo_money_payin,
        'Option 4': tcd_transactions_success_togo_money_payin
    }
    
    # Affichage de la liste déroulante
    selected_option = st.selectbox('Sélectionnez une option', list(options.keys()), key=get_unique_key("selectbox"))
    
    # Appel de la fonction correspondante à l'option sélectionnée
    option_function = options[selected_option]
    option_function()   
    
    

# Créer la page TMONEY PAYIN
def Orange_pending_payout_page():
    st.title("Orange pending ")
    st.header("Orange pending payout")
    st.subheader("Importation des fichiers et matching des transactions succès")
    
    # Dictionnaire associant chaque option à une fonction
    options = {
        'Option 1': import_orange_pendings_bo_payout,
        'Option 2': import_ecarts_and_en_echec_togo_money_payin,
        'Option 3': recherchev_togo_money_payin,
        'Option 4': tcd_transactions_success_togo_money_payin
    }
    
    # Affichage de la liste déroulante
    selected_option = st.selectbox('Sélectionnez une option', list(options.keys()), key=get_unique_key("selectbox"))
    
    # Appel de la fonction correspondante à l'option sélectionnée
    option_function = options[selected_option]
    option_function()     


# Créer la plateforme multi-page
pages = {
    "MTN PAYIN": mtn_payin_page,
    #"MTN PAYOUT": mtn_payint_page,
    "ORANGE MAGMA PAYIN": orange_payin_magma_page,
    #"ORANGE PAYOUT": orange_payin_page
    "ORANGE MONEY PAYIN": orange_money_payin_page,
    #"ORANGE PAYIN": orange_payout_page
     "TOGO MONEY PAYIN": TOGO_money_payin_page,
    #"TOGO PAYIN": TOGO_payout_page
    "ORANGE PENDING PAYOUT": Orange_pending_payout_page,
}

# Afficher la page sélectionnée
selected_page = st.sidebar.selectbox("Sélectionnez une page", list(pages.keys()))
pages[selected_page]()
