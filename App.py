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

    /* === EXPANDER : bloc d'exemples === */
    .streamlit-expanderHeader {
        background: #020617 !important;
        color: #e5e7eb !important;
        border-radius: 12px !important;
        border: 1px solid rgba(75, 85, 99, 0.95) !important;
        font-size: 0.9rem !important;
        padding: 0.4rem 0.9rem !important;
    }
    .streamlit-expanderContent {
        background: #020617 !important;
        padding-top: 0.4rem !important;
        padding-bottom: 0.4rem !important;
    }

    /* 🔧 FIX iOS : forcer le dark sur l’expander ouvert */
    [data-testid="stExpander"] > details,
    [data-testid="stExpander"] > details > summary {
        background-color: #020617 !important;
        color: #e5e7eb !important;
    }
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {
        color: #e5e7eb !important;
    }
    [data-testid="stExpander"] div[role="region"] {
        background-color: #020617 !important;
        color: #e5e7eb !important;
    }

    /* Petit chip de statut sous les boutons (analyse en cours / terminée) */
    .subtext-status-chip {
        margin-top: 0.45rem;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.18rem 0.7rem;
        border-radius: 999px;
        font-size: 0.8rem;
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid rgba(75, 85, 99, 0.9);
        color: #e5e7eb;
    }

    /* --- SELECTBOX : lisibilité en dark mode (desktop + mobile) --- */

    /* Label */
    .stSelectbox label {
        color: #e5e7eb !important;
    }

    /* Boîte fermée (select) */
    .stSelectbox > div > div,
    div[data-baseweb="select"] > div {
        background-color: #020617 !important;
        color: #f9fafb !important;
        border-radius: 10px !important;
        border: 1px solid rgba(148, 163, 184, 0.8) !important;
    }

    /* Texte interne */
    .stSelectbox div[data-baseweb="select"] span,
    div[data-baseweb="select"] span {
        color: #e5e7eb !important;
    }

    /* Liste déroulante (popover) */
    .stSelectbox div[role="listbox"],
    div[role="listbox"] {
        background-color: #020617 !important;
        color: #e5e7eb !important;
        border-radius: 10px !important;
        border: 1px solid rgba(148, 163, 184, 0.9) !important;
    }

    /* Options */
    .stSelectbox div[role="option"],
    div[role="option"] {
        background-color: #020617 !important;
        color: #e5e7eb !important;
    }

    /* Option survolée / sélectionnée */
    .stSelectbox div[role="option"][aria-selected="true"],
    .stSelectbox div[role="option"]:hover,
    div[role="option"][aria-selected="true"],
    div[role="option"]:hover {
        background-color: #0f172a !important;
        color: #f9fafb !important;
    }

     /* 🩹 Patch iOS Safari : forcer le popover du select en dark */
    @supports (-webkit-touch-callout: none) {
        /* Conteneur du menu déroulant */
        div[data-baseweb="popover"] {
            background-color: #020617 !important;
            color: #e5e7eb !important;
        }

        /* Zone listbox à l'intérieur */
        div[data-baseweb="popover"] [role="listbox"] {
            background-color: #020617 !important;
            color: #e5e7eb !important;
            border-radius: 10px !important;
            border: 1px solid rgba(148, 163, 184, 0.9) !important;
        }

        /* Options du menu */
        div[data-baseweb="popover"] [role="option"] {
            background-color: #020617 !important;
            color: #e5e7eb !important;
        }

        /* Option survolée / sélectionnée */
        div[data-baseweb="popover"] [role="option"][aria-selected="true"],
        div[data-baseweb="popover"] [role="option"]:hover {
            background-color: #0f172a !important;
            color: #f9fafb !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ───────────────── HELPERS ─────────────────

DEBUG_SCRAPER = True  # passe à False si tu veux enlever les messages de debug


def score_style(score: int) -> Tuple[str, str]:
    """Retourne (emoji, label niveau) en fonction du score pour les gros compteurs."""
    if score <= 33:
        return "🟢", "Faible"
    elif score <= 66:
        return "🟠", "Moyen"
    else:
        return "🔴", "Élevé"


def render_score(label: str, value: int):
    """Affiche un gros compteur (pour l’onglet Scores & actions)."""
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


def score_pill_level(score: int) -> str:
    """Retourne la classe CSS (good/warn/bad) pour les mini-pills de score."""
    if score >= 70:
        return "bad"   # rouge
    elif score >= 40:
        return "warn"  # orange
    else:
        return "good"  # vert


def fetch_url_content(url: str, follow_forum: bool = False, max_pages: int = 3) -> str:
    """
    Récupère du texte brut depuis une page web.

    - Essaie de parser même si le statut HTTP n'est pas 200 (403, 404 avec body, etc.).
    - Ne contourne PAS Cloudflare, paywalls, ni le JS dynamique.
    - Si le texte extrait est trop court (page technique, loader, "Just a moment...", "MSN"...),
      on considère que ce n'est pas exploitable et on renvoie une chaîne vide.
    """
    texts: List[str] = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }

    def extract_text(html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")

        # 1️⃣ On enlève le bruit évident
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # 2️⃣ Heuristique article si présent
        article_tag = soup.find("article")
        if article_tag:
            paragraphs = [p.get_text(" ", strip=True) for p in article_tag.find_all("p")]
            text = "\n\n".join([p for p in paragraphs if p])
            if text.strip():
                return text

        # 3️⃣ Plus gros bloc de texte dans main/body
        main = soup.find("main") or soup.body or soup
        candidates = main.find_all(["div", "section", "p"], recursive=True)

        best_text = ""
        best_len = 0
        for c in candidates:
            t = c.get_text(" ", strip=True)
            if not t or len(t) < 500:  # évite les micro-blocs
                continue
            if len(t) > best_len:
                best_len = len(t)
                best_text = t

        if best_text.strip():
            return best_text

        # 4️⃣ Fallback : tout le body
        body = soup.body or soup
        raw = body.get_text("\n", strip=True)
        if raw.strip():
            return raw

        # 5️⃣ Dernier recours : <title> + meta description / og:description
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        desc = ""
        desc_meta = soup.find("meta", attrs={"name": "description"})
        if not desc_meta:
            desc_meta = soup.find("meta", attrs={"property": "og:description"})
        if desc_meta and desc_meta.get("content"):
            desc = desc_meta["content"].strip()

        combo = (title + "\n\n" + desc).strip()
        return combo if combo else None

    def looks_like_anti_bot_page(text: str) -> bool:
        """Détecte les pages type Cloudflare / 'Just a moment...'."""
        lower = text.lower()
        patterns = [
            "just a moment",
            "cloudflare",
            "attention requise",
            "checking your browser before accessing",
            "vérification que vous n'êtes pas un robot",
        ]
        return any(p in lower for p in patterns)

    def get_page(url_single: str) -> Optional[str]:
        try:
            resp = requests.get(url_single, headers=headers, timeout=12)
        except Exception as e:
            if DEBUG_SCRAPER:
                st.warning(f"🌐 Erreur réseau en récupérant {url_single} : {e}")
            return None

        if DEBUG_SCRAPER:
            st.caption(f"🌐 Statut HTTP {resp.status_code} pour {url_single}")

        if not resp.text:
            if DEBUG_SCRAPER:
                st.caption("⚠️ Réponse sans body exploitable.")
            return None

        # 🔒 Détection Cloudflare / anti-bot
        if looks_like_anti_bot_page(resp.text):
            if DEBUG_SCRAPER:
                st.warning(
                    "⚠️ Cette page semble protégée (Cloudflare / anti-bot). "
                    "SUBTEXT ne peut pas y accéder directement.\n\n"
                    "👉 Ouvre la page dans ton navigateur puis **copie-colle le texte** "
                    "dans l’onglet « Texte »."
                )
            return None

        # 4xx / 5xx : on tente quand même d'extraire du texte, mais on prévient
        if resp.status_code >= 400:
            if DEBUG_SCRAPER:
                st.warning(
                    "⚠️ Le site a répondu avec un statut d'erreur "
                    f"({resp.status_code}). Il peut bloquer les robots/scrapers. "
                    "SUBTEXT essaie quand même d'extraire du texte si possible, "
                    "mais il est possible que tu doives copier-coller le contenu."
                )

        text = extract_text(resp.text)
        if not text:
            if DEBUG_SCRAPER:
                st.caption("⚠️ Aucun texte exploitable n'a pu être extrait.")
            return None

        # 🧹 Filtre : si le texte est beaucoup trop court, on considère que ce n'est pas exploitable
        # (cas typiques : 'MSN', 'Just a moment...', bandeau cookies, etc.)
        word_count = len(re.findall(r"\w+", text))
        if word_count < 30:
            if DEBUG_SCRAPER:
                preview_short = text[:80].replace("\n", " ")
                st.caption(
                    f"⚠️ Texte extrait très court ({word_count} mots) : "
                    f"« {preview_short} » …\n"
                    "Probable page technique (loader, consentement cookies, anti-bot...)."
                )
            return None

        if DEBUG_SCRAPER:
            preview = text[:400].replace("\n", " ")
            st.caption(
                f"🧾 Aperçu texte extrait ({len(text)} caractères / ~{word_count} mots) : "
                f"{preview} …"
            )

        return text

    # Page principale
    base_text = get_page(url)
    if base_text:
        texts.append(base_text)

    # Pages suivantes type forum ?page=1 → page=2,3...
    if follow_forum and "page=" in url and base_text:
        match = re.search(r"(page=)(\d+)", url)
        if match:
            prefix, num_str = match.groups()
            start_page = int(num_str)
            for p in range(start_page + 1, start_page + max_pages):
                new_url = re.sub(r"(page=)\d+", f"{prefix}{p}", url)
                extra_text = get_page(new_url)
                if extra_text:
                    texts.append(extra_text)

    full_text = "\n\n".join(texts).strip()
    return full_text if full_text else ""


def is_conversational_type(detected_type: str) -> bool:
    """Retourne True si le type ressemble à un message / conversation."""
    if not detected_type:
        return False

    t = detected_type.lower()

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

Tu dois produire UN objet json STRICT avec le format suivant, et rien d’autre que cet objet json :

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

Contraintes :

- detected_type ∈ ["email","dm","sms","forum_post","social_post","article","blog","news","advertisement","political_speech","other"]
- type_confidence : entier 0–100
- intention : courte phrase sur ce que l'auteur semble vouloir (informer, persuader, vendre, intimider, mobiliser, etc.)
- summary.neutral : une phrase factuelle, sans intention ni jugement
- scores.* : entiers 0–100 (0 = absent / très faible, 100 = très fort)
- scores.justifications.* : une phrase courte expliquant chaque score
- techniques : 0 à 5 éléments max, label + citation exacte du texte
- claims : 0 à 5 éléments max
  - verdict ∈ ["vrai","faux","incertain","invérifiable"]
  - confidence : 0–100
  - sources : liste d'URLs ou de noms de sources si tu en connais, sinon []
- actions.suggested : 0 à 3 actions concrètes pour le lecteur
- actions.none_needed : true si vraiment aucune action n'est nécessaire
- systemic_analysis : 2–3 phrases max au total, réparties dans ces trois champs, adaptation au type de texte
- diagram.mermaid :
  - soit chaîne vide ""
  - soit un diagramme Mermaid valide de type:
    graph LR
    ActeurA -->|Ressource/pression| ActeurB
- credibility.score : entier 0–100
  - 0 = très peu crédible / hautement douteux
  - 100 = très crédible / très fiable
- credibility.justification : 1–2 phrases max expliquant le score
- politics.article_bias : chaîne courte (ex : "centre-gauche", "droite", "populiste", "pro-gouvernement", "anti-gouvernement", "neutre", etc.)
- politics.article_bias_score : 0–100 (force du biais politique du TEXTE, si applicable)
- politics.author_bias : chaîne courte (orientation politique probable de l'auteur, si c'est un message de forum/réseau)
- politics.author_bias_score : 0–100 (niveau de confiance dans cette estimation)
- cognitive_risk.score : entier 0–100
- cognitive_risk.factors : 1 à 3 raisons principales
- confidence : entier 0–100 sur l'analyse globale

Règles spécifiques :

- Si le texte est un article, blog, news ou discours politique :
  - Tu dois renseigner credibility.* et politics.article_bias/article_bias_score.
- Si le texte est un forum_post, social_post, commentaire :
  - Tu peux estimer politics.author_bias/author_bias_score si des indices explicites sont présents.
  - Si ce n'est pas clair, laisse "author_bias" vide et score = 0.
- Pour les mails/DM/SMS très courts :
  - credibility peut rester générique, politics peut rester vide.
  - Tu privilégies les scores cognitifs + actions.

Style :
- Froid, clinique, sans morale.
- Tu n’inventes pas de faits. Si tu n’es pas sûr : verdict = "incertain" ou "invérifiable".
- Tu ne fais PAS de politique partisane.
- Tu n'ajoutes AUCUN texte hors du json.
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

if "analysis_status" not in st.session_state:
    st.session_state["analysis_status"] = ""

if "is_loading" not in st.session_state:
    st.session_state["is_loading"] = False


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
    st.session_state["analysis_status"] = ""
    st.session_state["is_loading"] = False


# ───────────────── UI PRINCIPALE ─────────────────

st.title("SUBTEXT — voir ce que les mots font à ta tête 🕵️")

st.write(
    "Colle un texte **ou** une URL. SUBTEXT analyse le bruit, la manipulation, "
    "l’hostilité, les leviers rhétoriques, le biais politique et le risque cognitif global."
)

mode_label = st.radio(
    "Source du contenu :",
    ["Texte", "URL (article / post public)"],
    horizontal=True,
)

input_mode = "Texte" if mode_label.startswith("Texte") else "URL"

raw_text = ""
url = ""
follow_forum = False

if input_mode == "Texte":
    # ───────── EXEMPLES RAPIDES (dans un expander au-dessus) ─────────
    example_preset: Optional[str] = None

    with st.expander("Besoin d’un exemple ? Clique pour en charger un :"):
        example_col1, example_col2, example_col3 = st.columns(3)

        with example_col1:
            if st.button("💢 Message agressif", key="ex_agressif"):
                example_preset = (
                    "T'arrêtes pas de raconter n'importe quoi, t’es complètement ridicule. "
                    "Personne ne te respecte ici, tu ferais mieux de quitter Twitter."
                )

        with example_col2:
            if st.button("🕴️ Manipulation (mail)", key="ex_mail"):
                example_preset = (
                    "Bonjour, j’espère que tu vas bien. Il faudrait vraiment que tu m’aides "
                    "sur ce dossier aujourd’hui, sinon on risque tous de paraître incompétents. "
                    "Tu ne veux pas que ça arrive, n’est-ce pas ?"
                )

        with example_col3:
            if st.button("🎭 Propagande politique", key="ex_politique"):
                example_preset = (
                    "Notre pays est détruit par les mêmes élites depuis 30 ans. "
                    "Il est temps de reprendre le contrôle, d’abolir leurs privilèges "
                    "et de les faire payer pour leurs crimes."
                )

    if example_preset is not None:
        st.session_state["input_text"] = example_preset
        st.session_state["analysis_data"] = None
        st.session_state["reply_text"] = ""
        st.session_state["word_count"] = 0

    raw_text = st.text_area(
        "Colle ton texte ici :",
        height=220,
        placeholder="Ex : mail, message, post, discours...",
        key="input_text",
    )

else:
    st.info(
        "🔗 Colle ici l’URL d’un article, d’un post public ou d’un topic de forum.\n\n"
        "SUBTEXT va récupérer le texte principal de la page (pas les commentaires cachés, pas les éléments interactifs)."
    )

    url = st.text_input(
        "URL à analyser :",
        placeholder="Ex : https://…",
    )

    follow_forum = st.checkbox(
        "Inclure aussi les pages suivantes si c’est un topic de forum (page=2,3,4…)",
        value=False,
        help="Ne marche que si l’URL contient un paramètre du type page=1, page=2, etc.",
    )

col_analyze, col_clear = st.columns([3, 1])

with col_analyze:
    analyze_button = st.button("Analyser ce texte")

with col_clear:
    st.button("Effacer", on_click=reset_all)

# Petit statut visible sous les boutons (mobile friendly)
status_msg = st.session_state.get("analysis_status", "")
if status_msg:
    st.markdown(
        f"<div class='subtext-status-chip'>🧠 {status_msg}</div>",
        unsafe_allow_html=True,
    )

if input_mode == "URL":
    st.caption(
        "ℹ️ Si l’analyse échoue, copie-colle simplement le texte de l’article dans la zone de texte."
    )


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
            st.error(
                "Impossible de récupérer du texte depuis cette URL.\n\n"
                "💡 Causes possibles :\n"
                "- le site bloque les robots/scrapers (ex : erreur 403, Cloudflare, protection anti-bot),\n"
                "- le contenu est chargé dynamiquement en JavaScript (SUBTEXT n’exécute pas le JS),\n"
                "- la page est protégée par un paywall ou nécessite une connexion.\n\n"
                "👉 Dans ces cas-là, ouvre la page dans ton navigateur puis **copie-colle le texte** "
                "dans l’onglet « Texte » de SUBTEXT."
            )
            st.stop()

        source_text = content

    # Compte de mots + blocage si trop court
    word_count = count_words(source_text)
    st.session_state["word_count"] = word_count

    if word_count < 15:
        st.warning(
            "📏 Le texte est trop court pour une analyse pertinente.\n\n"
            "SUBTEXT a besoin d’un minimum de contexte (environ 2 à 3 phrases complètes).\n"
            "👉 Ajoute un peu de contenu ou colle le message dans son contexte."
        )
        st.session_state["analysis_status"] = ""
        st.session_state["is_loading"] = False
        st.stop()

    st.session_state["analysis_status"] = "Analyse en cours…"
    st.session_state["is_loading"] = True

    with st.spinner("Analyse en cours…"):
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
            st.error("Impossible de lire la réponse du modèle comme JSON. Voici la réponse brute :")
            st.code(raw, language="json")
            st.session_state["analysis_status"] = ""
            st.session_state["is_loading"] = False
            st.stop()
        except Exception as e:
            st.error(f"Erreur lors de l’appel au modèle : {e}")
            st.session_state["analysis_status"] = ""
            st.session_state["is_loading"] = False
            st.stop()

    st.session_state["analysis_data"] = data
    st.session_state["source_text"] = source_text
    st.session_state["analysis_status"] = (
        "Analyse terminée ✅ Fais défiler pour voir le verdict."
    )
    st.session_state["is_loading"] = False


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

        # ───────── Mini-résumé visuel des scores ─────────
        mini_noise = int(scores.get("noise", 0) or 0)
        mini_manip = int(scores.get("manipulation", 0) or 0)
        mini_host = int(scores.get("hostility", 0) or 0)
        mini_emo = int(scores.get("emotional_intensity", 0) or 0)

        mini_noise_class = score_pill_level(mini_noise)
        mini_manip_class = score_pill_level(mini_manip)
        mini_host_class = score_pill_level(mini_host)
        mini_emo_class = score_pill_level(mini_emo)

        st.markdown(
            f"""
            <div style="
                margin-top: 0.55rem;
                margin-bottom: 0.35rem;
                display: flex;
                flex-wrap: wrap;
                gap: 0.4rem;
            ">
                <span class="subtext-score-pill {mini_manip_class}">
                    🎯 Manipulation&nbsp; {mini_manip}/100
                </span>
                <span class="subtext-score-pill {mini_host_class}">
                    💢 Hostilité&nbsp; {mini_host}/100
                </span>
                <span class="subtext-score-pill {mini_noise_class}">
                    📡 Bruit&nbsp; {mini_noise}/100
                </span>
                <span class="subtext-score-pill {mini_emo_class}">
                    💓 Intensité émotive&nbsp; {mini_emo}/100
                </span>
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
            # --- Options de réponse (objectif, ton, emojis) ---
            reply_goal = st.selectbox(
                "Objectif de ta réponse :",
                [
                    "Répondre simplement",
                    "Poser un cadre / des limites",
                    "Apaiser / rassurer",
                    "Exprimer un désaccord calmement",
                    "Refuser poliment",
                ],
                index=0,
            )

            reply_tone = st.selectbox(
                "Ton souhaité :",
                [
                    "Neutre",
                    "Chaleureux / amical",
                    "Professionnel",
                    "Direct mais poli",
                ],
                index=0,
            )

            use_emojis = st.checkbox(
                "Autoriser les emojis si c’est naturel",
                value=True,
            )

            gen_col, reset_col = st.columns([1, 1])

            # Bouton pour générer la réponse
            with gen_col:
                gen_reply = st.button("Générer une réponse", key="reply_after_analysis")

            # Bouton reset complet (input + analyse + réponse)
            with reset_col:
                st.button(
                    "🔁 Reset complet",
                    key="reset_after",
                    on_click=reset_all,
                )

            # Génération de la réponse si demandé
            if gen_reply:
                with st.spinner("Rédaction de la réponse..."):
                    try:
                        reply_system_prompt = f"""
Tu écris une réponse courte au texte donné.

Règles générales :
- Même langue que le texte d'origine.
- Ton : {reply_tone}.
- Objectif principal : {reply_goal}.
- Toujours respectueux, assertif, jamais agressif.
- Va droit au but, sans phrases inutiles.
- Ta réponse doit rester plus courte que le texte d'origine, idéalement 50–80% de son nombre de mots (~{int(word_count * 0.8)} mots max).
- Ne reformule pas le texte d'origine, réponds réellement à son contenu.
- Emojis autorisés : {"oui, mais avec parcimonie" if use_emojis else "non, n'en mets aucun"}.
"""

                        reply_user_content = (
                            "Texte d'origine :\n"
                            "----------------\n"
                            f"{source_text}\n\n"
                            "Contexte d'analyse (résumé neutre) :\n"
                            f"{neutral_summary}\n\n"
                            "Intention apparente détectée par SUBTEXT :\n"
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

            # Zone de texte éditable avec la réponse
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
