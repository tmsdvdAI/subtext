import json

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ───────────────── CONFIG & CLIENT ─────────────────

load_dotenv()
client = OpenAI()

st.set_page_config(
    page_title="SUBTEXT",
    page_icon="🕵️",
    layout="centered",
)

# ───────────────── FONCTIONS UTILES ─────────────────

def score_style(score: int):
    """Retourne (emoji, niveau texte) en fonction du score."""
    if score <= 33:
        return "🟢", "Faible"
    elif score <= 66:
        return "🟠", "Moyen"
    else:
        return "🔴", "Élevé"


def render_score(label: str, value: int):
    icon, level = score_style(value)
    st.markdown(
        f"""
        <div style="text-align:center; padding: 0.5rem 0;">
            <div style="font-size:0.9rem; margin-bottom:0.25rem;">{label}</div>
            <div style="font-size:1.4rem; font-weight:600;">{icon} {value}/100</div>
            <div style="font-size:0.85rem; opacity:0.9;">Niveau : {level}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ───────────────── UI ─────────────────

st.title("SUBTEXT — voir ce que les mots cachent")

st.write(
    "Colle un texte, SUBTEXT va analyser le bruit, la manipulation et l'hostilité, "
    "puis te donner les intentions et actions possibles."
)

user_text = st.text_area(
    "Colle ton texte à analyser :",
    height=200,
    placeholder="Ex : Bonjour, on aurait besoin de ton accord rapide sur ce point, c’est assez urgent...",
)

if st.button("Scanner"):
    if not user_text.strip():
        st.warning("⚠️ Merci de coller un texte avant de scanner.")
    else:
        with st.spinner("Analyse en cours..."):
            try:
                # ───────── PROMPT SYSTEME ─────────
                system_prompt = """
Tu es DECODER-Engine, un système d'analyse rhétorique.
Ta mission : analyser un texte pour révéler ce qu'il cache.

Consignes strictes :
- Réponds UNIQUEMENT avec un JSON valide, sans aucun texte autour.
- Respect total de la structure JSON ci-dessous.
- Pas de commentaire, pas d'explication, pas de morale.
- Aucune mention de l'utilisateur ou de toi-même.
- Tu n'enregistres jamais le texte fourni.

Définitions rapides :
- noise : Bullshit, flou, remplissage, non-information.
- manipulation : pression, culpabilisation, langue de bois, agenda caché.
- hostility : ton agressif, mépris, condescendance.

Format JSON exact à utiliser :
{
  "scores": {
    "noise": 0,
    "manipulation": 0,
    "hostility": 0
  },
  "tone": "",
  "intention": "",
  "summary": [],
  "actions": [],
  "confidence": 0
}

Contraintes de style :
- tone : un seul mot (ex : neutre, amical, menaçant, condescendant, pressant).
- intention : une phrase courte, factuelle.
- summary : 2 à 3 puces maximum, utiles et factuelles.
- actions : 2 à 3 actions concrètes ou "Aucune action nécessaire".
- confidence : entier de 0 à 100.

Ton style : froid, analytique, concis, anti-bullshit.
"""

                # ───────── APPEL OPENAI ─────────
                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f'Analyse ce texte :\n\n"{user_text}"'
                        },
                    ],
                )

                raw = response.choices[0].message.content
                data = json.loads(raw)

                # ───────── AFFICHAGE ─────────
                with st.expander("Voir le JSON brut"):
                    st.json(data)

                st.subheader("Résultats")

                scores = data["scores"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    render_score("Bruit (Bullshit)", scores["noise"])
                with col2:
                    render_score("Manipulation", scores["manipulation"])
                with col3:
                    render_score("Hostilité", scores["hostility"])

                st.write("---")
                st.write(f"**Ton détecté** : {data['tone']}")
                st.write(f"**Intention principale** : {data['intention']}")

                st.write("**Résumé utile :**")
                for item in data["summary"]:
                    st.write(f"• {item}")

                st.write("**Actions proposées :**")
                for action in data["actions"]:
                    st.write(f"✓ {action}")

                st.caption(f"Confiance du modèle : {data['confidence']} / 100")

            except json.JSONDecodeError:
                st.error("Impossible de lire la réponse comme JSON. Voici la réponse brute :")
                st.code(raw, language="json")
            except Exception as e:
                st.error(f"Erreur : {e}")
