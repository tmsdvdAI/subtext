import os
import json
from typing import Dict, Any, Optional, List, Tuple
import html as html_lib

import streamlit as st
from openai import OpenAI
import requests

# BeautifulSoup facultatif pour extraire le texte HTML
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# ───────────────── CONFIG GLOBALE ─────────────────

st.set_page_config(
    page_title="SUBTEXT — Scanner d'intention",
    page_icon="👁️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

client = OpenAI()

# Modèle LLM principal (flagship)
OPENAI_MAIN_MODEL = "gpt-5.1"

# ───────────────── STYLES GLOBAUX (Dark / Mobile-first) ─────────────────

st.markdown(
    """
    <style>
    /* Forcer le dark mode partout */
    html, body, .stApp {
        background-color: #020617 !important;
        color: #F9FAFB !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #020617 !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0, 0, 0, 0) !important;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1.5rem;
        max-width: 700px;
    }
    h1, h2, h3, h4 {
        font-weight: 600;
        letter-spacing: 0.02em;
        color: #F9FAFB;
    }
    .hero-card {
        border-radius: 18px;
        padding: 1.2rem 1.3rem;
        background: linear-gradient(135deg, #020617, #111827);
        border: 1px solid #1F2937;
    }
    .sub-card {
        border-radius: 14px;
        padding: 0.9rem 1rem;
        background: #111827;
        border: 1px solid #1F2937;
    }
    .tag-pill {
        display: inline-block;
        padding: 0.25rem 0.55rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 500;
        margin-right: 0.35rem;
        margin-bottom: 0.25rem;
        background: #1F2937;
        color: #E5E7EB;
    }
    .tag-pill.danger { background: #7F1D1D; color: #FEE2E2; }
    .tag-pill.warn   { background: #92400E; color: #FEF3C7; }
    .tag-pill.info   { background: #1E3A8A; color: #DBEAFE; }
    .tag-pill.safe   { background: #065F46; color: #D1FAE5; }

    .share-card {
        border-radius: 18px;
        padding: 1rem 1.2rem;
        background: radial-gradient(circle at top left, #1F2937, #020617);
        border: 1px solid #1F2937;
    }
    .share-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #9CA3AF;
        margin-bottom: 0.3rem;
    }
    .share-main {
        font-size: 1.0rem;
        font-weight: 600;
        margin-bottom: 0.3rem;
        color: #F9FAFB;
    }
    .share-sub {
        font-size: 0.85rem;
        color: #D1D5DB;
    }
    .small-label {
        font-size: 0.8rem;
        color: #9CA3AF;
    }
    textarea {
        font-size: 0.9rem !important;
        background-color: #020617 !important;
        color: #F9FAFB !important;
    }
    input {
        background-color: #020617 !important;
        color: #F9FAFB !important;
    }

    /* Tabs (sections) plus visibles, scrollables sur mobile */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        scrollbar-width: thin;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        padding: 0.25rem 0.6rem;
        border-radius: 999px 999px 0 0;
        color: #E5E7EB;
        font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 2px solid #F97373;
        color: #F97373 !important;
        font-weight: 600;
    }

    /* Bloc de réponse + bouton copier (pas de scroll horizontal) */
    .reply-block {
        margin-top: 0.6rem;
    }
    .reply-text {
        width: 100%;
        min-height: 90px;
        background-color: #020617;
        color: #F9FAFB;
        border-radius: 12px;
        border: 1px solid #374151;
        padding: 0.75rem;
        resize: vertical;
        white-space: pre-wrap;
        overflow-wrap: break-word;
    }
    .copy-btn {
        margin-top: 0.5rem;
        border-radius: 999px;
        border: 1px solid #4B5563;
        background: #111827;
        color: #E5E7EB;
        padding: 0.35rem 0.9rem;
        font-size: 0.85rem;
        cursor: pointer;
    }
    .copy-btn:hover {
        border-color: #F97373;
        color: #F97373;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ───────────────── DEMO TEXTES ─────────────────

DEMO_EMAIL_MANAGER = (
    "Bonjour,\n\n"
    "Pour la troisième fois je dois te rappeler cette tâche pourtant simple. "
    "Je ne vais pas repasser derrière toi indéfiniment : à un moment il va falloir "
    "te mettre au niveau du reste de l'équipe.\n\n"
    "Bien à toi."
)

DEMO_SMS_RUPTURE = (
    "écoute, je t'avais prévenu. Si tu faisais un effort on n'en serait pas là. "
    "Je ne peux pas continuer à être le seul à essayer dans cette relation. "
    "Tu t'étonnes que je sois froid, mais tu récoltes juste ce que tu as semé."
)

DEMO_TWEET_POLITIQUE = (
    "Si vous n'avez rien à vous reprocher, vous ne devriez pas avoir peur "
    "de cette nouvelle loi. Ceux qui s'indignent le plus sont toujours ceux "
    "qui ont quelque chose à cacher. #SécuritéAvantTout"
)

# ───────────────── HELPERS URL ─────────────────


def fetch_url_text(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Essaie de récupérer le texte principal d'une URL.
    Retourne (texte, erreur).
    Si erreur != None → on affiche un wording clair invitant à copier-coller.
    """
    url = url.strip()
    if not url:
        return None, "Merci de saisir une URL valide."

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SUBTEXT/0.1)"},
            timeout=10,
        )
    except Exception:
        return (
            None,
            "Impossible de récupérer cette page automatiquement. "
            "Certains sites protègent leur contenu ou nécessitent du JavaScript. "
            "Copie-colle le texte directement dans l'onglet « Texte ».",
        )

    if resp.status_code != 200 or "text/html" not in resp.headers.get("Content-Type", ""):
        return (
            None,
            "Je n'arrive pas à extraire le texte de cette URL (protection, JavaScript, Cloudflare...). "
            "Copie-colle le contenu dans l'onglet « Texte » pour l'analyser.",
        )

    html = resp.text

    # Protection Cloudflare / JS / pages vides
    if "cf-browser-verification" in html.lower() or "cf-challenge" in html.lower():
        return (
            None,
            "Cette page semble protégée (Cloudflare / JavaScript). "
            "Je ne peux pas extraire automatiquement le contenu. "
            "Copie-colle le texte dans l'onglet « Texte ». ",
        )

    if BeautifulSoup is None:
        # Fallback très simple si bs4 pas installée
        return (
            None,
            "Je peux accéder à la page, mais je ne dispose pas de l'outil pour extraire proprement le texte. "
            "Installe `beautifulsoup4` ou copie-colle directement le texte.",
        )

    soup = BeautifulSoup(html, "html.parser")

    # Naïf : on concatène les paragraphes
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = "\n\n".join(p for p in paragraphs if p)

    if not text.strip():
        return (
            None,
            "Je n'ai pas réussi à trouver du texte exploitable sur cette page. "
            "Copie-colle le contenu à analyser dans l'onglet « Texte ». ",
        )

    return text, None

# ───────────────── LLM : ANALYSE ─────────────────


def analyze_text_with_llm(text: str) -> Optional[Dict[str, Any]]:
    if not text.strip():
        return None

    system_prompt = """
Tu es SUBTEXT-ENGINE, moteur d'analyse de communication, de rhétorique et d'impact cognitif, en français.

🎯 Ta mission :
Produire une ANALYSE STRUCTURÉE, JSON UNIQUEMENT, qui aide l'utilisateur à :
1) Comprendre l'effet psychologique du texte (micro : lecteur individuel).
2) Comprendre la logique de pouvoir, les intérêts et la mise en scène (méso / macro).
3) Détecter hostilité, manipulation, pression sociale.
4) Repérer les passages problématiques (citations + explication).
5) Pour les articles / discours : proposer un début de FACT-CHECK avec verdict + sources quand tu as une base solide.
6) Proposer des actions recommandées (réagir / ne pas réagir / enquêter / partager ou non).

⚠️ Tu restes sobre, nuancé, pédagogique. Pas de catastrophisme.

──────────────── SCHEMA JSON ATTENDU ────────────────

{
  "content_type": "interaction" | "article" | "discours" | "forum" | "réseau_social" | "autre",

  "global_score": 0-100,
  "global_label": "Toxique" | "Tendu" | "Ambigu" | "Neutre" | "Positif",

  "main_effect": "1 phrase très concrète (max 22 mots) expliquant ce que ce texte fait ressentir à un lecteur moyen",
  "secondary_effects": [
    "autre effet possible (ex: culpabilité, honte, colère, confusion, mobilisation, résignation)",
    "..."
  ],

  "tags": [
    "passif-agressif",
    "culpabilisation",
    "intimidation",
    "chantage affectif",
    "sarcasme",
    "ton sec",
    "mobilisation politique",
    "bouc émissaire",
    "propagande",
    "neutre",
    "bienveillant"
  ],

  "hostility": { "score": 0-100, "label": "très faible"|"faible"|"moyenne"|"élevée"|"très élevée" },
  "manipulation": { "score": 0-100, "label": "très faible"|"faible"|"moyenne"|"élevée"|"très élevée" },
  "pressure": { "score": 0-100, "label": "très faible"|"faible"|"moyenne"|"élevée"|"très élevée" },

  "profile": {
    "relation_type": "ex: manager → employé, partenaire amoureux, inconnu sur réseau social, élu → citoyens, média → grand public",
    "channel": "mail / sms / réunion / tweet / article / discours / forum / autre",
    "power_asymmetry": "faible / moyenne / forte, avec 1 phrase d'explication courte",
    "target_audience": "public visé principal, en quelques mots"
  },

  "systemic_view": {
    "scale": "micro"|"méso"|"macro"|"micro→macro",
    "power_dynamics": "2–4 phrases, vulgarisées, expliquant qui a l'avantage, qui subit, et comment le message entretient ce rapport de force",
    "narrative_frame": "2–3 phrases simples expliquant comment le texte cadre le problème (ex: sécurité vs liberté, mérite individuel, crise permanente, responsabilité personnelle vs collective, etc.)",
    "macro_implications": [
      "jusqu'à 3 phrases (ou puces) décrivant les effets possibles à moyen / long terme sur la confiance, la coopération, la polarisation, la capacité des gens à discuter sereinement"
    ]
  },

  "highlights": [
    {
      "quote": "extrait exact du texte original",
      "tag": "type de problème (ex: intimidation, mépris, chantage affectif, bouc émissaire, simplification abusive)",
      "explanation": "effet probable sur le lecteur en langage simple (1–3 phrases)"
    }
  ],

  "fact_checks": [
    {
      "claim": "affirmation factuelle précise du texte",
      "verdict": "vrai" | "faux" | "partiellement vrai" | "incertain",
      "explanation": "explication courte et nuancée du verdict",
      "sources": [
        "https://... (source institutionnelle ou média reconnu si tu en as une en mémoire)",
        "https://..."
      ]
    }
  ],

  "recommended_actions": [
    {
      "label": "Ne pas répondre à chaud",
      "detail": "explication courte adaptée au contexte du texte",
      "priority": 1
    }
  ]
}

──────────────── RÈGLES D'INTERPRÉTATION ────────────────

1) content_type
- interaction : mails, DM, SMS, messages privés, échanges personnels.
- article : presse, blog, analyse.
- discours : meeting politique, prise de parole officielle, allocution.
- forum : JVC, Reddit, etc.
- réseau_social : tweet, post Insta, etc. (hors forum).
- autre : si tu hésites.

2) Scores :
- 0–20  : très faible / neutre
- 21–40 : faible / légèrement tendu
- 41–60 : moyen / ambigu / potentiellement problématique
- 61–80 : élevé / clairement problématique
- 81–100: très élevé / fortement toxique ou manipulateur

3) Fact-check :
- Tu utilises tes connaissances internes.
- Tu ne remplis "fact_checks" que si tu as une base raisonnable.
- Si tu n'es pas sûr : verdict = "incertain" et "sources": [].

4) Systemic view :
- Tu expliques les choses pour un public non spécialiste, avec un vocabulaire simple.
- Tu relies le micro au macro : quels récits, quels rapports de force, quelle vision du monde ?
- Tu restes sobre, analytique, pas militant.

Format de sortie :
- UNIQUEMENT un JSON valide conforme au schéma.
- PAS de texte avant/après, pas de markdown.
"""

    user_prompt = f"Texte à analyser (en français) :\n\n{text}"

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MAIN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = completion.choices[0].message.content
        data = json.loads(content)
        return data
    except Exception as e:
        st.error(f"Erreur lors de l'appel à l'IA (analyse) : {e}")
        return None


def generate_replies_with_llm(
    original_text: str,
    analysis: Dict[str, Any],
    tone_pref: str,
    emoji_allowed: bool,
) -> Dict[str, str]:
    """
    Second appel LLM : génère uniquement les réponses proposées,
    une fois l'analyse déjà faite et affichée.
    Répond TOUJOURS au nom de la personne qui a REÇU le message.
    """
    system_prompt = """
Tu es SUBTEXT-REPLY, spécialisé dans les réponses calmes et assertives.

Point de vue :
- Tu écris AU NOM DE LA PERSONNE QUI REÇOIT le message, pas de la personne qui l'a envoyé.
- Ex : si le texte est un mail de manager, tu écris du point de vue de l'employé qui répond.

Mission :
- À partir du TEXTE ORIGINAL + d'un RÉSUMÉ D'ANALYSE fourni,
- Générer 2 réponses possibles :
  1) "calm" : posée, factuelle, sans attaque, recentrée sur les faits / besoins.
  2) "assertive" : posée mais ferme, pose des limites claires, sans insulte ni mépris.

Tons possibles (tu adapteras en fonction de la consigne) :
- "calme" : vocabulaire simple, phrases courtes, pas d'attaque.
- "professionnel" : formulation polie, structurée, neutre.
- "empathique" : reconnaissance du ressenti, douceur.
- "direct mais respectueux" : va au point important, mais sans agressivité.
- "humour léger" : 1 ou 2 petites touches d'humour, jamais humiliant.

Emojis :
- Si l'utilisateur autorise les emojis :
  - Tu peux en mettre 1–2 maximum, cohérents avec le ton.
- Sinon :
  - Aucun emoji, jamais.

Contraintes :
- 1–4 phrases max par réponse.
- Pas de psychanalyse, pas de jugement global ("tu es toxique").
- Pas de répétition inutile du contenu initial.
- Tu n'expliques pas ta réponse, tu ne renvoies que le JSON ci-dessous.

Format JSON STRICT :

{
  "calm": "réponse courte, posée",
  "assertive": "réponse courte, posée mais ferme"
}
"""

    summary_for_reply = {
        "global_score": analysis.get("global_score"),
        "global_label": analysis.get("global_label"),
        "main_effect": analysis.get("main_effect"),
        "tags": analysis.get("tags", []),
        "hostility": analysis.get("hostility", {}),
        "manipulation": analysis.get("manipulation", {}),
        "pressure": analysis.get("pressure", {}),
        "profile": analysis.get("profile", {}),
    }

    user_prompt = f"""
Texte original reçu :

{original_text}

Résumé d'analyse (ne PAS renvoyer) :
{json.dumps(summary_for_reply, ensure_ascii=False)}

Préférences utilisateur :
- Ton souhaité : {tone_pref}
- Emojis autorisés : {"oui" if emoji_allowed else "non"}

Génère UNIQUEMENT un JSON avec deux champs :
- "calm"
- "assertive"
"""

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MAIN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        content = completion.choices[0].message.content
        data = json.loads(content)
        return {
            "calm": (data.get("calm") or "").strip(),
            "assertive": (data.get("assertive") or "").strip(),
        }
    except Exception as e:
        st.error(f"Erreur lors de la génération de réponse : {e}")
        return {"calm": "", "assertive": ""}

# ───────────────── HELPERS UI ─────────────────


def render_tag(text: str, level: str = "info") -> str:
    level_class = level if level in {"danger", "warn", "info", "safe"} else "info"
    return f"<span class='tag-pill {level_class}'>{text}</span>"


def get_score_color(score: int) -> str:
    try:
        s = int(score)
    except Exception:
        return "white"
    if s >= 75:
        return "#F87171"  # rouge
    if s >= 50:
        return "#FBBF24"  # ambre
    if s >= 25:
        return "#34D399"  # vert clair
    return "#6EE7B7"      # vert


def reset_app():
    """Callback Reset : nettoie la session proprement."""
    keys_to_clear = ["input_text", "input_url", "analysis", "replies"]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]


def render_reply_block(title: str, text: str):
    """Bloc réponse + bouton copier (sans scroll horizontal)."""
    if not text:
        return
    escaped = html_lib.escape(text)
    js_text = json.dumps(text)  # string JS sécurisé
    st.markdown(
        f"""
        <div class="reply-block sub-card">
          <div style="font-size:0.9rem;margin-bottom:0.4rem;">{title}</div>
          <textarea class="reply-text" readonly>{escaped}</textarea>
          <button class="copy-btn" onclick='navigator.clipboard.writeText({js_text})'>
            📋 Copier la réponse
          </button>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ───────────────── INITIALISATION SESSION ─────────────────

if "analysis" not in st.session_state:
    st.session_state["analysis"] = None

if "replies" not in st.session_state:
    st.session_state["replies"] = {"calm": "", "assertive": ""}

if "tone_pref" not in st.session_state:
    st.session_state["tone_pref"] = "calme"

if "emoji_allowed" not in st.session_state:
    st.session_state["emoji_allowed"] = True

if "input_text" not in st.session_state:
    st.session_state["input_text"] = ""

if "input_url" not in st.session_state:
    st.session_state["input_url"] = ""

if "input_mode" not in st.session_state:
    st.session_state["input_mode"] = "Texte"

# ───────────────── HEADER ─────────────────

st.markdown("<h1 style='text-align:center;'>👁️ SUBTEXT</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#9CA3AF;font-size:0.9rem;'>"
    "Scanner d'intention, de non-dits & de récits — micro → macro."
    "</p>",
    unsafe_allow_html=True,
)

st.markdown("---")

# ───────────────── DEMO BAR ─────────────────

st.markdown("**Essayer en un clic**")
col_demo1, col_demo2, col_demo3 = st.columns(3)

with col_demo1:
    if st.button("📧 Mail manager", use_container_width=True):
        st.session_state["input_text"] = DEMO_EMAIL_MANAGER
        st.session_state["analysis"] = None
        st.session_state["replies"] = {"calm": "", "assertive": ""}

with col_demo2:
    if st.button("💔 SMS rupture", use_container_width=True):
        st.session_state["input_text"] = DEMO_SMS_RUPTURE
        st.session_state["analysis"] = None
        st.session_state["replies"] = {"calm": "", "assertive": ""}

with col_demo3:
    if st.button("🏛️ Tweet politique", use_container_width=True):
        st.session_state["input_text"] = DEMO_TWEET_POLITIQUE
        st.session_state["analysis"] = None
        st.session_state["replies"] = {"calm": "", "assertive": ""}

st.markdown("")

# ───────────────── INPUT MODE (Texte / URL) ─────────────────

input_mode = st.radio(
    "Mode d'entrée",
    ["Texte", "URL"],
    horizontal=True,
    key="input_mode",
)

if input_mode == "Texte":
    st.markdown("**Colle ici le texte, tweet, DM, article ou discours :**")
    st.text_area(
        label="",
        key="input_text",
        height=180,
        placeholder="Colle le message, l'article, le discours ou le post ici…",
    )
    input_text = st.session_state["input_text"]
else:
    st.markdown("**Colle ici l'URL de l'article / discours à analyser :**")
    st.text_input(
        label="",
        key="input_url",
        placeholder="https://...",
    )
    input_text = ""  # sera rempli après fetch

col_scan, col_reset = st.columns([3, 1])

with col_scan:
    scan_clicked = st.button("🔍 SCANNER LE SOUS-TEXTE", use_container_width=True)

with col_reset:
    st.button("🧹 Reset", use_container_width=True, on_click=reset_app)

if scan_clicked:
    # Gestion URL → texte
    if input_mode == "URL":
        url = st.session_state.get("input_url", "").strip()
        if not url:
            st.warning("Merci de saisir une URL à analyser.")
        else:
            with st.spinner("Récupération du contenu de la page…"):
                fetched_text, err = fetch_url_text(url)
            if err:
                st.warning(err)
                st.stop()
            else:
                input_text = fetched_text
    else:
        input_text = st.session_state.get("input_text", "")

    if not input_text.strip():
        st.warning("Colle d'abord un texte à analyser (ou choisis une URL).")
    else:
        with st.spinner("Analyse en cours…"):
            analysis = analyze_text_with_llm(input_text)
        st.session_state["analysis"] = analysis
        st.session_state["replies"] = {"calm": "", "assertive": ""}  # reset réponses
        if analysis:
            st.toast("Analyse terminée ✅", icon="✅")

st.markdown("---")

analysis = st.session_state["analysis"]

# ───────────────── AUCUN RÉSULTAT ─────────────────

if not analysis:
    st.markdown(
        "<p style='color:#9CA3AF;font-size:0.9rem;'>"
        "Tu verras ici le tableau de bord cognitif après l'analyse. "
        "Commence avec un des exemples ci-dessus, colle un texte, ou fournis une URL."
        "</p>",
        unsafe_allow_html=True,
    )
    st.stop()

# ───────────────── HERO VERDICT ─────────────────

content_type = (analysis.get("content_type") or "autre").lower()

global_score = int(analysis.get("global_score", 0))
global_label = analysis.get("global_label", "Ambigu")
main_effect = (analysis.get("main_effect") or "").strip()
secondary_effects: List[str] = analysis.get("secondary_effects", []) or []
tags = analysis.get("tags", []) or []

hostility = analysis.get("hostility", {}) or {}
manipulation = analysis.get("manipulation", {}) or {}
pressure = analysis.get("pressure", {}) or {}

profile = analysis.get("profile", {}) or {}
systemic = analysis.get("systemic_view", {}) or {}

st.markdown("<div class='hero-card'>", unsafe_allow_html=True)

st.markdown("<div class='small-label'>Verdict global</div>", unsafe_allow_html=True)
score_color = get_score_color(global_score)

st.markdown(
    f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:0.2rem;margin-bottom:0.4rem;">
        <div style="min-width:110px;">
            <div style="font-size:0.9rem;color:#9CA3AF;">Niveau de pression cognitive</div>
            <div style="font-size:2.1rem;font-weight:700;color:{score_color};">
                {global_score}%
            </div>
            <div style="font-size:0.9rem;color:#E5E7EB;">{global_label}</div>
            <div style="font-size:0.8rem;color:#9CA3AF;margin-top:0.2rem;">
                Type détecté : {content_type or "—"}
            </div>
        </div>
        <div style="flex:1;margin-left:1rem;">
            <div style="height:10px;border-radius:999px;background:#1F2937;overflow:hidden;">
                <div style="width:{global_score}%;height:100%;background:{score_color};"></div>
            </div>
            <div style="margin-top:0.4rem;font-size:0.9rem;color:#D1D5DB;">
                {main_effect or "Ce texte génère un effet difficile à formuler, mais potentiellement chargé."}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if secondary_effects:
    st.markdown("<div class='small-label' style='margin-top:0.4rem;'>Autres effets possibles</div>", unsafe_allow_html=True)
    for eff in secondary_effects[:4]:
        st.markdown(f"- {eff}")

if tags:
    st.markdown("<div class='small-label' style='margin-top:0.4rem;'>Signaux détectés</div>", unsafe_allow_html=True)
    tag_html = ""
    for t in tags:
        lvl = "info"
        low = t.lower()
        if any(k in low for k in ["insulte", "mépris", "agressif", "hostile", "bouc émissaire"]):
            lvl = "danger"
        elif any(k in low for k in ["culpabilisation", "pression", "chantage"]):
            lvl = "warn"
        elif any(k in low for k in ["neutre", "apaisant", "bienveillant"]):
            lvl = "safe"
        tag_html += render_tag(t, lvl)
    st.markdown(tag_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # fin hero-card

st.markdown("")

# ───────────────── NAVIGATION PRINCIPALE (Tabs) ─────────────────

tab_labels = ["🧩 Diagnostic", "🌐 Systémique", "🧪 Fact-check", "🎯 Actions", "🛡️ Réponse"]
tabs = st.tabs(tab_labels)

# ───── SECTION DIAGNOSTIC ─────

with tabs[0]:
    st.markdown("#### Profils & indicateurs")

    # Profil relationnel
    st.markdown("<div class='sub-card' style='margin-bottom:0.8rem;'>", unsafe_allow_html=True)
    st.markdown("**Profil du message**", unsafe_allow_html=True)
    rel_type = profile.get("relation_type", "—")
    channel = profile.get("channel", "—")
    power_asym = profile.get("power_asymmetry", "—")
    target_audience = profile.get("target_audience", "—")

    st.markdown(f"- **Relation** : {rel_type}")
    st.markdown(f"- **Canal** : {channel}")
    st.markdown(f"- **Asymétrie de pouvoir** : {power_asym}")
    st.markdown(f"- **Audience visée** : {target_audience}")
    st.markdown("</div>", unsafe_allow_html=True)

    # Barres hostilité / manipulation / pression
    with st.container():
        c1, c2, c3 = st.columns(3)

        with c1:
            h_score = int(hostility.get("score", 0) or 0)
            h_label = hostility.get("label", "—")
            st.markdown("**Hostilité**")
            st.progress(h_score / 100)
            st.caption(f"{h_score}% · {h_label}")

        with c2:
            m_score = int(manipulation.get("score", 0) or 0)
            m_label = manipulation.get("label", "—")
            st.markdown("**Manipulation**")
            st.progress(m_score / 100)
            st.caption(f"{m_score}% · {m_label}")

        with c3:
            p_score = int(pressure.get("score", 0) or 0)
            p_label = pressure.get("label", "—")
            st.markdown("**Pression sociale**")
            st.progress(p_score / 100)
            st.caption(f"{p_score}% · {p_label}")

    st.markdown("")

    # Autopsie repliée
    highlights = analysis.get("highlights", []) or []

    with st.expander("🔎 Autopsie du texte (passages problématiques)"):
        if not highlights:
            st.caption("Aucun passage spécifique n'a été mis en avant.")
        else:
            for h in highlights:
                quote = (h.get("quote") or "").strip()
                tag = (h.get("tag") or "").strip()
                explanation = (h.get("explanation") or "").strip()

                st.markdown("<div class='sub-card' style='margin-bottom:0.6rem;'>", unsafe_allow_html=True)
                if tag:
                    st.markdown(render_tag(tag, "info"), unsafe_allow_html=True)
                if quote:
                    st.markdown(f"> {quote}")
                if explanation:
                    st.markdown(
                        f"<p style='font-size:0.9rem;color:#E5E7EB;margin-top:0.3rem;'>{explanation}</p>",
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

# ───── SECTION SYSTÉMIQUE ─────

with tabs[1]:
    st.markdown("#### Mise en perspective systémique")

    st.markdown("<div class='sub-card' style='margin-bottom:0.8rem;'>", unsafe_allow_html=True)
    scale = systemic.get("scale", "—")
    power_dyn = systemic.get("power_dynamics", "—")
    narrative_frame = systemic.get("narrative_frame", "—")
    macro_implications = systemic.get("macro_implications", []) or []

    st.markdown(f"- **Échelle principale** : {scale}")
    st.markdown("")
    st.markdown("**Rapports de force & intérêts en jeu**")
    st.markdown(power_dyn)

    st.markdown("")
    st.markdown("**Comment le message cadre le problème**")
    st.markdown(narrative_frame)

    if macro_implications:
        st.markdown("")
        st.markdown("**Effets possibles à moyen / long terme**")
        for mi in macro_implications:
            st.markdown(f"- {mi}")
    st.markdown("</div>", unsafe_allow_html=True)

# ───── SECTION FACT-CHECK ─────

with tabs[2]:
    st.markdown("#### Analyse factuelle (quand applicable)")
    fact_checks = analysis.get("fact_checks", []) or []

    if content_type in ("article", "discours", "forum", "réseau_social") and fact_checks:
        for fc in fact_checks:
            claim = (fc.get("claim") or "").strip()
            verdict = (fc.get("verdict") or "").strip()
            explanation = (fc.get("explanation") or "").strip()
            sources = fc.get("sources", []) or []

            st.markdown("<div class='sub-card' style='margin-bottom:0.6rem;'>", unsafe_allow_html=True)
            if claim:
                st.markdown(f"**Affirmation :** {claim}")
            if verdict:
                st.markdown(f"**Verdict :** {verdict}")
            if explanation:
                st.markdown(f"**Pourquoi :** {explanation}")
            if sources:
                st.markdown("**Sources possibles :**")
                for src in sources:
                    st.markdown(f"- {src}")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.caption(
            "Aucune analyse factuelle spécifique n'a été générée, "
            "ou le texte ne s'y prêtait pas clairement."
        )

# ───── SECTION ACTIONS ─────

with tabs[3]:
    st.markdown("#### Actions recommandées")
    actions = analysis.get("recommended_actions", []) or []

    if not actions:
        st.caption("Aucune action particulière n'a été recommandée.")
    else:
        actions_sorted = sorted(
            actions,
            key=lambda a: a.get("priority", 3)
        )
        for act in actions_sorted:
            label = (act.get("label") or "").strip()
            detail = (act.get("detail") or "").strip()
            priority = act.get("priority", 3)

            st.markdown("<div class='sub-card' style='margin-bottom:0.6rem;'>", unsafe_allow_html=True)
            st.markdown(f"**[{priority}] {label}**")
            if detail:
                st.markdown(detail)
            st.markdown("</div>", unsafe_allow_html=True)

# ───── SECTION RÉPONSE ─────

with tabs[4]:
    if content_type != "interaction":
        st.caption(
            "Ce texte n'est pas identifié comme un message adressé directement "
            "(DM, mail, SMS...). Aucune réponse formulée n'est proposée."
        )
    else:
        st.markdown("#### Générer une réponse (après analyse)")

        col_tone, col_emoji = st.columns(2)
        with col_tone:
            st.session_state["tone_pref"] = st.selectbox(
                "Ton de la réponse",
                [
                    "calme",
                    "professionnel",
                    "empathique",
                    "direct mais respectueux",
                    "humour léger",
                ],
                index=0,
                key="tone_select",
            )
        with col_emoji:
            st.session_state["emoji_allowed"] = st.checkbox(
                "Inclure des emojis", value=True, key="emoji_checkbox"
            )

        tone_pref = st.session_state["tone_pref"]
        emoji_allowed = st.session_state["emoji_allowed"]

        # On utilise le texte effectivement analysé :
        if input_mode == "URL":
            original_for_reply = "(Texte issu d'un article ou discours, réponse directe rarement pertinente.)"
        else:
            original_for_reply = st.session_state.get("input_text", "")

        if st.button("🛡️ Générer une réponse suggérée", use_container_width=True):
            with st.spinner("Génération de la réponse…"):
                replies = generate_replies_with_llm(
                    original_text=original_for_reply,
                    analysis=analysis,
                    tone_pref=tone_pref,
                    emoji_allowed=emoji_allowed,
                )
            st.session_state["replies"] = replies
            st.toast("Réponse générée ✅ (utilise le bouton pour la copier)", icon="✅")

        replies = st.session_state["replies"]

        if replies.get("calm") or replies.get("assertive"):
            tabs_reply = st.tabs(["😌 Calme", "💬 Assertive"])

            with tabs_reply[0]:
                if replies.get("calm"):
                    render_reply_block("Réponse calme", replies["calm"])
                else:
                    st.caption("Aucune réponse calme disponible pour l'instant.")

            with tabs_reply[1]:
                if replies.get("assertive"):
                    render_reply_block("Réponse assertive", replies["assertive"])
                else:
                    st.caption("Aucune réponse assertive disponible pour l'instant.")
        else:
            st.caption(
                "Aucune réponse générée pour l'instant. "
                "Choisis le ton, puis clique sur « Générer une réponse suggérée »."
            )

# ───────────────── SHARE CARD ─────────────────

st.markdown("")
st.markdown("**📸 Résumé partageable (screenshot)**")
st.markdown(
    "<div class='share-card'>"
    "<div class='share-title'>Rapport SUBTEXT</div>",
    unsafe_allow_html=True,
)

share_tags = ", ".join(tags[:3]) if tags else "aucun signal critique"
share_main = f"Toxicité globale : {global_score}% — {global_label}"

st.markdown(f"<div class='share-main'>{share_main}</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='share-sub'>Effet principal : {main_effect or 'Inconfort diffus difficile à formuler.'}</div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='share-sub' style='margin-top:0.3rem;'>Signaux clés : {share_tags}</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='share-sub' style='margin-top:0.6rem;font-size:0.8rem;color:#6B7280;'>"
    "Capture cet encadré pour l'envoyer à un ami ou à un collègue."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")
st.markdown(
    "<p style='text-align:center;color:#6B7280;font-size:0.8rem;'>"
    "Made by Thomas — MVP SUBTEXT · UX + IA · Streamlit"
    "</p>",
    unsafe_allow_html=True,
)
