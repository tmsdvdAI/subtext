import json
import re
from typing import Optional, Tuple, List

import requests
from bs4 import BeautifulSoup
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import urllib.parse


# ───────────────── CONFIG & CLIENT ─────────────────

load_dotenv()
client = OpenAI()

st.set_page_config(
    page_title="SUBTEXT",
    page_icon="🕵️",
    layout="centered",
)

# ───────────────── GLOBAL THEME (DARK) ─────────────────

st.markdown(
    """
    <style>
    /* --- GLOBAL DARK THEME --- */
    .stApp {
        background-color: #020617 !important;
        color: #e5e7eb !important;
    }

    /* Body text par défaut plus clair */
    p, span, li, label {
        color: #e5e7eb !important;
    }

    /* Titres */
    h1, h2, h3, h4, h5, h6 {
        color: #f9fafb !important;
    }

    /* Textarea + inputs */
    textarea,
    input,
    .stTextInput > div > div > input {
        background-color: #020617 !important;
        color: #f9fafb !important;
        border: 1px solid rgba(148, 163, 184, 0.65) !important;
        border-radius: 10px !important;
    }

    /* Placeholder lisible sur fond sombre */
    textarea::placeholder,
    .stTextInput input::placeholder {
        color: #9ca3af !important;
        opacity: 0.85 !important;
    }

    /* Radios & labels */
    .stRadio label {
        color: #f9fafb !important;
        font-size: 0.9rem !important;
    }

    /* Buttons */
    .stButton button {
        background: #0f172a !important;
        color: #f9fafb !important;
        border-radius: 999px !important;
        padding: 0.45rem 1.2rem !important;
        border: 1px solid rgba(148, 163, 184, 0.8) !important;
        font-size: 0.9rem !important;
    }
    .stButton button:hover {
        background: #1e293b !important;
        border-color: rgba(248, 250, 252, 0.9) !important;
    }

    /* Tabs */
    .stTabs [role="tablist"] {
        border-bottom: 1px solid rgba(148, 163, 184, 0.55) !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    .stTabs [role="tab"] {
        color: #e5e7eb !important;
        background: transparent !important;
        font-size: 0.9rem !important;
        padding-bottom: 0.4rem !important;
    }
    .stTabs [aria-selected="true"] {
        color: #fecaca !important;
        border-bottom: 2px solid #fb7185 !important;
    }

    /* Supprimer le fade/glow à droite/gauche sur mobile & desktop */
    .stTabs [role="tablist"]::after,
    .stTabs [role="tablist"]::before {
        box-shadow: none !important;
        background: transparent !important;
    }

    /* Divider lines */
    hr {
        border-color: rgba(148, 163, 184, 0.25) !important;
    }

    /* Éviter les "bulles" / séparateurs fantômes dans les tabs */
    .stTabs hr {
        margin-top: 0.2rem !important;
        margin-bottom: 0.4rem !important;
        border: 1px solid rgba(15, 23, 42, 0.0) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ───────────────── HELPERS ─────────────────


def score_style(score: int) -> Tuple[str, str]:
    """Retourne (emoji, label niveau) en fonction du score."""
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


def fetch_url_content(url: str, follow_forum: bool = False, max_pages: int = 3) -> str:
    """
    Récupère le texte principal d'une page web.
    Si follow_forum=True et que l'URL contient 'page=', tente d'incrémenter le paramètre.
    C'est volontairement simple : on ne gère pas les sites complexes, login, JS, etc.
    """
    texts: List[str] = []

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SubtextBot/0.1; +https://example.com/bot)"
    }

    def get_single(url_single: str) -> Optional[str]:
        try:
            resp = requests.get(url_single, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        body = soup.body
        if not body:
            return None
        text = body.get_text(separator="\n", strip=True)
        return text

    base_text = get_single(url)
    if base_text:
        texts.append(base_text)

    if follow_forum and "page=" in url:
        match = re.search(r"(page=)(\d+)", url)
        if match:
            prefix, num_str = match.groups()
            start_page = int(num_str)
            for p in range(start_page + 1, start_page + max_pages):
                new_url = re.sub(r"(page=)\d+", f"{prefix}{p}", url)
                extra_text = get_single(new_url)
                if extra_text:
                    texts.append(extra_text)

    return "\n\n".join(texts)


def is_conversational_type(detected_type: str) -> bool:
    """Retourne True si le type ressemble à un message / conversation."""
    if not detected_type:
        return False

    t = detected_type.lower()

    # Cas "propres" (valeurs prévues dans le JSON)
    conversational_types = {
        "email",
        "dm",
        "sms",
        "chat",
        "forum_post",
        "comment",
        "social_post",
        "message",
    }
    if t in conversational_types:
        return True

    # Cas plus "sales" : labels combinés ou custom du modèle
    keywords = [
        "mail",
        "e-mail",
        "dm",
        "sms",
        "message",
        "messagerie",
        "chat",
        "whatsapp",
        "imessage",
        "signal",
        "telegram",
        "forum",
        "commentaire",
        "post",
    ]

    return any(k in t for k in keywords)


def count_words(text: str) -> int:
    return len(re.findall(r"\w+", text))



# ───────────────── PROMPT MOTEUR ─────────────────

SYSTEM_PROMPT = """
Tu es SUBTEXT-SYSTÉMIQUE-OSINT, un moteur d’auto-défense intellectuelle.

Ta mission : analyser un texte pour révéler :
1) son effet cognitif sur le lecteur
2) sa structure de pouvoir (qui exerce quoi sur qui)
3) la véracité APPROXIMATIVE des affirmations vérifiables (à partir de tes connaissances internes, pas du web)
4) les risques informationnels globaux
5) pour un article ou discours public : une estimation de crédibilité et de biais politique
6) pour un message de forum / réseau social : une estimation du biais politique PROBABLE de l'auteur

Tu t’adaptes automatiquement au type de contenu :
- Mail / DM / SMS → interaction individuelle, dynamique de dépendance
- Forum / réseaux → dynamique de groupe, statut, toxicité
- Publicité → persuasion, marketing, raccourcis cognitifs
- Article / post d’information → fiabilité globale, intérêt public
- Discours politique → slogans, cadrage idéologique, polarisation
- Sinon → "other"

Tu dois produire UN JSON STRICT avec le format suivant :

{
  "meta": {
    "detected_type": "",
    "type_confidence": 0,
    "intention": ""
  },
  "summary": {
    "neutral": ""
  },
  "scores": {
    "noise": 0,
    "manipulation": 0,
    "hostility": 0,
    "emotional_intensity": 0,
    "informational_value": 0,
    "justifications": {
      "noise": "",
      "manipulation": "",
      "hostility": "",
      "emotional_intensity": "",
      "informational_value": ""
    }
  },
  "techniques": [
    {
      "label": "",
      "excerpt": ""
    }
  ],
  "claims": [
    {
      "quote": "",
      "verdict": "",
      "confidence": 0,
      "sources": []
    }
  ],
  "actions": {
    "suggested": [],
    "none_needed": false
  },
  "systemic_analysis": {
    "power_relation": "",
    "mechanism": "",
    "hidden_interests": ""
  },
  "diagram": {
    "mermaid": ""
  },
  "credibility": {
    "score": 0,
    "justification": ""
  },
  "politics": {
    "article_bias": "",
    "article_bias_score": 0,
    "author_bias": "",
    "author_bias_score": 0
  },
  "cognitive_risk": {
    "score": 0,
    "factors": []
  },
  "confidence": 0
}

(… le reste de tes contraintes / règles est inchangé …)
"""

# ───────────────── STATE ─────────────────

if "analysis_data" not in st.session_state:
    st.session_state["analysis_data"] = None

if "source_text" not in st.session_state:
    st.session_state["source_text"] = ""

if "word_count" not in st.session_state:
    st.session_state["word_count"] = 0

if "reply_text" not in st.session_state:
    st.session_state["reply_text"] = ""


def reset_all():
    """Réinitialise tous les états utiles (appelé AVANT rendu via on_click)."""
    if "analysis_data" in st.session_state:
        st.session_state["analysis_data"] = None
    if "source_text" in st.session_state:
        st.session_state["source_text"] = ""
    if "word_count" in st.session_state:
        st.session_state["word_count"] = 0
    if "reply_text" in st.session_state:
        st.session_state["reply_text"] = ""
    if "input_text" in st.session_state:
        st.session_state["input_text"] = ""


# ───────────────── UI PRINCIPALE ─────────────────

st.title("SUBTEXT — voir ce que les mots font à ta tête 🕵️")

st.write(
    "Colle un texte **ou** une URL. SUBTEXT analyse le bruit, la manipulation, "
    "l’hostilité, les leviers rhétoriques, le biais politique et le risque cognitif global."
)

mode_label = st.radio(
    "Source du contenu :",
    ["Texte (disponible)", "URL (bientôt)"],
    horizontal=True,
)

input_mode = "Texte" if mode_label.startswith("Texte") else "URL"

raw_text = ""
url = ""
follow_forum = False

if input_mode == "Texte":
    raw_text = st.text_area(
        "Colle ton texte ici :",
        height=220,
        placeholder="Ex : mail, message, post, discours...",
        key="input_text",
    )
else:
    st.info(
        "🔗 Analyse par URL arrive bientôt.\n\n"
        "Pour l’instant, colle simplement le texte de l’article ou du post à la main. "
        "Cela garantit une analyse plus fiable et évite les bugs de parsing."
    )
    st.stop()

col_analyze, col_clear = st.columns([3, 1])

with col_analyze:
    analyze_button = st.button("Analyser ce texte")

with col_clear:
    st.button("Effacer", on_click=reset_all)


# ───────────────── ANALYSE ─────────────────

if analyze_button:
    if input_mode == "Texte":
        if not raw_text.strip():
            st.warning("⚠️ Merci de coller un texte avant d’analyser.")
            st.stop()
        source_text = raw_text.strip()
    else:
        if not url.strip():
            st.warning("⚠️ Merci de fournir une URL avant d’analyser.")
            st.stop()
        with st.spinner("Récupération de la page..."):
            content = fetch_url_content(url.strip(), follow_forum=follow_forum)
        if not content:
            st.error("Impossible de récupérer du texte depuis cette URL.")
            st.stop()
        source_text = content

    word_count = count_words(source_text)

    with st.spinner("Analyse en cours..."):
        try:
            response = client.chat.completions.create(
                model="gpt-5.1",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": source_text},
                ],
            )

            raw = response.choices[0].message.content
            data = json.loads(raw)

        except json.JSONDecodeError:
            st.error("Impossible de lire la réponse comme JSON. Voici la réponse brute :")
            st.code(raw, language="json")
            st.stop()
        except Exception as e:
            st.error(f"Erreur : {e}")
            st.stop()

    st.session_state["analysis_data"] = data
    st.session_state["source_text"] = source_text
    st.session_state["word_count"] = word_count


# ───────────────── AFFICHAGE SI ANALYSE DISPO ─────────────────

data = st.session_state.get("analysis_data")
source_text = st.session_state.get("source_text", "")
word_count = st.session_state.get("word_count", 0)

if data:
    # CSS pour les cards SUBTEXT
    st.markdown(
        """
        <style>
        .subtext-verdict-card {
            border-radius: 18px;
            padding: 1.4rem 1.8rem;
            background: radial-gradient(circle at top left, #0f172a, #020617 55%);
            border: 1px solid rgba(148, 163, 184, 0.45);
            box-shadow: 0 20px 45px rgba(0,0,0,0.7);
            color: #e5e7eb;
            margin-bottom: 0.75rem;
        }
        .subtext-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.2rem 0.6rem;
            font-size: 0.75rem;
            border-radius: 999px;
            background: rgba(15, 118, 110, 0.18);
            color: #5eead4;
            border: 1px solid rgba(45, 212, 191, 0.55);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .subtext-intention {
            font-size: 0.9rem;
            color: #d1d5db;
            margin-top: 0.35rem;
        }
        .subtext-summary {
            font-size: 1.05rem;
            font-weight: 600;
            margin-top: 0.85rem;
            margin-bottom: 0.75rem;
            color: #f9fafb;
        }
        .subtext-score-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .subtext-score-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #9ca3af;
        }
        .subtext-score-pill {
            font-size: 0.88rem;
            font-weight: 600;
            padding: 0.25rem 0.7rem;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
        }
        .subtext-score-pill.good {
            background: rgba(22, 163, 74, 0.16);
            color: #4ade80;
            border: 1px solid rgba(74, 222, 128, 0.55);
        }
        .subtext-score-pill.warn {
            background: rgba(234, 179, 8, 0.16);
            color: #facc15;
            border: 1px solid rgba(250, 204, 21, 0.55);
        }
        .subtext-score-pill.bad {
            background: rgba(239, 68, 68, 0.16);
            color: #fca5a5;
            border: 1px solid rgba(248, 113, 113, 0.55);
        }
        .subtext-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            font-size: 0.78rem;
            background: rgba(15,23,42,0.85);
            border: 1px solid rgba(75,85,99,0.9);
            color: #9ca3af;
        }
        .subtext-card {
            border-radius: 14px;
            padding: 1rem 1.1rem;
            background: #020617;
            border: 1px solid rgba(51, 65, 85, 0.95);
            box-shadow: 0 14px 34px rgba(0,0,0,0.7);
        }
        .subtext-card h4 {
            margin: 0 0 0.45rem 0;
            font-size: 0.95rem;
            color: #e5e7eb;
        }
        .subtext-card p {
            margin: 0;
            font-size: 0.9rem;
            color: #e5e7eb;
        }
        .subtext-tab-container > div {
            padding-top: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    meta = data.get("meta", {})
    summary = data.get("summary", {})
    scores = data.get("scores", {})
    techniques = data.get("techniques", [])
    claims = data.get("claims", [])
    actions = data.get("actions", {})
    systemic = data.get("systemic_analysis", {})
    diagram = data.get("diagram", {})
    credibility = data.get("credibility", {})
    politics = data.get("politics", {})
    cog_risk = data.get("cognitive_risk", {})
    overall_conf = data.get("confidence", 0)

    detected_type = meta.get("detected_type", "other") or "other"
    type_conf = int(meta.get("type_confidence", 0) or 0)
    intention = meta.get("intention", "").strip() or "Non précisé"
    neutral_summary = summary.get("neutral", "")

    risk_score = int(cog_risk.get("score", 0) or 0)

    if risk_score >= 70:
        risk_class = "bad"
    elif risk_score >= 40:
        risk_class = "warn"
    else:
        risk_class = "good"

    st.markdown("### 🔎 Verdict d’analyse")

    top_left, top_right = st.columns([3, 2])

    # ───────── Carte verdict ─────────
    with top_left:
        st.markdown(
            f"""
            <div class="subtext-verdict-card">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:0.75rem; flex-wrap:wrap;">
                    <div class="subtext-badge">
                        {detected_type} · {type_conf}/100
                    </div>
                    <div class="subtext-chip">
                        {word_count} mots analysés
                    </div>
                </div>
                <div class="subtext-intention">
                    Intention apparente : <strong>{intention}</strong>
                </div>
                <div class="subtext-summary">
                    {neutral_summary}
                </div>
                <div class="subtext-score-row">
                    <div>
                        <div class="subtext-score-label">Risque cognitif global</div>
                        <div style="font-size:0.8rem; color:#9ca3af; margin-top:0.2rem;">
                            Confiance de l’analyse : {overall_conf}/100
                        </div>
                    </div>
                    <div>
                        <span class="subtext-score-pill {risk_class}">
                            {risk_score}/100
                        </span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Crédibilité / biais politique
        if detected_type in ["article", "blog", "news", "political_speech"]:
            cred_score = int(credibility.get("score", 0) or 0)
            cred_justif = credibility.get("justification", "")
            art_bias = politics.get("article_bias", "")
            art_bias_score = int(politics.get("article_bias_score", 0) or 0)

            with st.container():
                st.markdown('<div class="subtext-card">', unsafe_allow_html=True)
                st.markdown("**Crédibilité & biais politique**")
                st.markdown(f"- Crédibilité perçue : **{cred_score}/100**")
                if cred_justif:
                    st.markdown(
                        f"<span style='font-size:0.85rem;color:#9ca3af;'>{cred_justif}</span>",
                        unsafe_allow_html=True,
                    )
                if art_bias:
                    st.markdown(
                        f"- Bord politique du texte : **{art_bias}** ({art_bias_score}/100)"
                    )
                st.markdown("</div>", unsafe_allow_html=True)

        if detected_type in ["forum_post", "social_post", "comment"]:
            auth_bias = politics.get("author_bias", "")
            auth_bias_score = int(politics.get("author_bias_score", 0) or 0)
            if auth_bias:
                st.markdown(
                    f"<div class='subtext-card' style='margin-top:0.6rem;'><strong>Orientation probable de l'auteur :</strong> {auth_bias} ({auth_bias_score}/100)</div>",
                    unsafe_allow_html=True,
                )

    # ───────── Bloc réponse à droite ─────────
    with top_right:
        st.markdown('<div class="subtext-card">', unsafe_allow_html=True)
        st.markdown("#### 💬 Réponse suggérée")

        if is_conversational_type(detected_type):
            gen_col, reset_col = st.columns([1, 1])

            with gen_col:
                gen_reply = st.button("Générer une réponse", key="reply_after_analysis")

            with reset_col:
                st.button(
                    "🔁 Reset complet",
                    key="reset_after",
                    on_click=reset_all,
                )

            if gen_reply:
                with st.spinner("Rédaction de la réponse..."):
                    try:
                        reply_system_prompt = f"""
Tu écris une réponse courte au texte donné.
Règles :
- Même langue que le texte d'origine.
- Ton adapté au type détecté (email professionnel, message amical, forum, etc.).
- Toujours respectueux, assertif, jamais agressif.
- Va droit au but, sans phrases inutiles.
- Ta réponse doit rester plus courte que le texte d'origine, idéalement 50–80% de son nombre de mots (~{int(word_count * 0.8)} mots max).
- Ne reformule pas le texte d'origine, réponds réellement.
"""

                        reply_user_content = (
                            "Texte d'origine :\n"
                            "----------------\n"
                            f"{source_text}\n\n"
                            "Contexte d'analyse (résumé neutre) :\n"
                            f"{neutral_summary}\n\n"
                            "Intention apparente :\n"
                            f"{intention}\n"
                        )

                        reply_resp = client.chat.completions.create(
                            model="gpt-5.1",
                            messages=[
                                {"role": "system", "content": reply_system_prompt},
                                {"role": "user", "content": reply_user_content},
                            ],
                        )

                        st.session_state["reply_text"] = (
                            reply_resp.choices[0].message.content.strip()
                        )

                    except Exception as e:
                        st.error(f"Erreur lors de la génération de la réponse : {e}")

            reply_text = st.session_state.get("reply_text", "")
            if reply_text:
                st.text_area(
                    "Texte à copier / ajuster",
                    value=reply_text,
                    height=180,
                    label_visibility="collapsed",
                )
                st.caption("✂️ Tu peux éditer puis copier-coller manuellement.")
            else:
                st.caption(
                    "Clique sur « Générer une réponse » pour proposer une formulation."
                )
        else:
            st.caption(
                "Ce contenu n’a pas été détecté comme message conversationnel. "
                "Génération de réponse désactivée."
            )

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ───────── TABS PRINCIPAUX ─────────
    tab_scores, tab_rhet, tab_fact, tab_system, tab_json = st.tabs(
        ["📊 Scores & actions", "🎭 Rhétorique", "🧪 Fact-check", "🕸 Système", "🛠 Debug JSON"]
    )

    noise = int(scores.get("noise", 0) or 0)
    manip = int(scores.get("manipulation", 0) or 0)
    host = int(scores.get("hostility", 0) or 0)
    emo = int(scores.get("emotional_intensity", 0) or 0)
    info_val = int(scores.get("informational_value", 0) or 0)

    # TAB SCORES & ACTIONS
    with tab_scores:
        st.markdown('<div class="subtext-tab-container">', unsafe_allow_html=True)
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown('<div class="subtext-card">', unsafe_allow_html=True)
            st.markdown("#### Profil cognitif")
            row1_col1, row1_col2 = st.columns(2)
            row2_col1, row2_col2 = st.columns(2)

            with row1_col1:
                render_score("Manipulation", manip)
            with row1_col2:
                render_score("Intensité émotionnelle", emo)
            with row2_col1:
                render_score("Bruit", noise)
            with row2_col2:
                render_score("Valeur informationnelle", info_val)

            with st.expander("Voir les justifications des scores"):
                just = scores.get("justifications", {})
                st.markdown(f"**Bruit :** {just.get('noise', '')}")
                st.markdown(f"**Manipulation :** {just.get('manipulation', '')}")
                st.markdown(f"**Hostilité :** {just.get('hostility', '')}")
                st.markdown(
                    f"**Intensité émotionnelle :** {just.get('emotional_intensity', '')}"
                )
                st.markdown(
                    f"**Valeur informationnelle :** {just.get('informational_value', '')}"
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown('<div class="subtext-card">', unsafe_allow_html=True)
            st.markdown("#### Actions recommandées")
            sugg = actions.get("suggested", []) or []
            none_needed = actions.get("none_needed", False)

            if none_needed and not sugg:
                st.write("✅ Aucune action particulière n’est nécessaire.")
            else:
                if sugg:
                    for a in sugg:
                        st.markdown(f"• {a}")
                if none_needed:
                    st.caption(
                        "Le modèle estime qu’aucune action critique supplémentaire n’est indispensable."
                    )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # TAB RHÉTORIQUE
    with tab_rhet:
        st.markdown('<div class="subtext-tab-container">', unsafe_allow_html=True)
        st.markdown('<div class="subtext-card">', unsafe_allow_html=True)
        st.markdown("#### 🎭 Techniques rhétoriques détectées")
        if not techniques:
            st.write("Aucune technique marquante détectée.")
        else:
            for t in techniques:
                label = t.get("label", "")
                excerpt = t.get("excerpt", "")
                st.markdown(f"- **{label}** — « {excerpt} »")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # TAB FACT-CHECK
    with tab_fact:
        st.markdown('<div class="subtext-tab-container">', unsafe_allow_html=True)
        st.markdown('<div class="subtext-card">', unsafe_allow_html=True)
        st.markdown("#### 🧪 Claims factuels & pseudo fact-check (connaissances internes)")
        if not claims:
            st.write("Aucun claim factuel explicite identifié.")
        else:
            for c in claims:
                quote = c.get("quote", "")
                verdict = c.get("verdict", "")
                conf = c.get("confidence", 0)
                sources = c.get("sources", [])
                st.markdown(f"**« {quote} »**")
                st.markdown(f"- Verdict : `{verdict}` (confiance {conf}/100)")
                if sources:
                    st.markdown("- Sources possibles :")
                    for s in sources:
                        st.markdown(f"  - {s}")
                st.write("")

        if claims:
            st.write("---")
            st.markdown("### 🔍 Vérifier ces affirmations sur Internet")

            factcheck_prompt = f"""
Tu es un assistant spécialisé en vérification factuelle avec accès à la recherche web (browsing).

Ta tâche est de vérifier les affirmations factuelles contenues dans le texte ci-dessous en utilisant des sources fiables disponibles en ligne.

INSTRUCTIONS :
1. Identifie les principales affirmations factuelles.
2. Pour chaque affirmation, fais une recherche web rapide.
3. Pour chaque affirmation, retourne :
   - Claim : l’affirmation reformulée de façon courte
   - Verdict : vrai / faux / partiellement vrai / incertain
   - Sources : 2 à 3 URL de sources fiables
   - Confiance : un score de 0 à 100

FORMAT DE SORTIE :

### Fact-check web sourcé

| Claim | Verdict | Sources | Confiance |
|------|---------|---------|-----------|

### Texte à vérifier :

{source_text}
"""

            query = urllib.parse.quote(factcheck_prompt)
            chatgpt_url = f"https://chat.openai.com/?q={query}"

            st.markdown(
                f"[🧪 Ouvrir dans ChatGPT pour vérifier sur Internet]({chatgpt_url})",
                unsafe_allow_html=True,
            )
            st.caption(
                "Clique pour ouvrir ChatGPT avec le texte déjà préparé pour un fact-check web sourcé."
            )

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # TAB SYSTÈME
    with tab_system:
        st.markdown('<div class="subtext-tab-container">', unsafe_allow_html=True)
        st.markdown('<div class="subtext-card">', unsafe_allow_html=True)
        st.markdown("#### 🕸 Analyse systémique")

        pr = systemic.get("power_relation", "")
        mech = systemic.get("mechanism", "")
        hidden = systemic.get("hidden_interests", "")

        if not any([pr, mech, hidden]):
            st.write("Pas d’analyse systémique fournie pour ce texte.")
        else:
            if pr:
                st.markdown(f"**Relation de pouvoir :** {pr}")
            if mech:
                st.markdown(f"**Mécanisme :** {mech}")
            if hidden:
                st.markdown(f"**Intérêts potentiels cachés :** {hidden}")

            mermaid = (diagram or {}).get("mermaid", "").strip()
            if mermaid:
                with st.expander("Voir le code du diagramme (Mermaid)"):
                    st.code(mermaid, language="mermaid")
                st.caption(
                    "Dans une prochaine version, ce schéma sera affiché graphiquement."
                )

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # TAB DEBUG JSON
    with tab_json:
        st.markdown('<div class="subtext-tab-container">', unsafe_allow_html=True)
        st.markdown('<div class="subtext-card">', unsafe_allow_html=True)
        st.markdown("#### 🛠 JSON brut (debug)")
        st.json(data)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
