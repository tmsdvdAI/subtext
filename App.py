import json
import html as html_lib
from typing import Dict, Any, Optional, List

import streamlit as st
from openai import OpenAI

# ───────────────── CONFIG GLOBALE ─────────────────
# Conserve le titre et l'icône, mais permet un rendu plus large tout en
# restant centré pour une meilleure utilisation de l'espace sur grand
# écran. Le sidebar est masqué par défaut.
st.set_page_config(
    page_title="SUBTEXT — Détecteur de Bullshit",
    page_icon="👁️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Instanciation du client OpenAI. La clé API doit être fournie via les
# secrets Streamlit ou les variables d'environnement comme auparavant.
client = OpenAI()

# Nom du modèle principal utilisé pour l'analyse. Vous pouvez le
# modifier ici sans impacter le reste de l'application.
OPENAI_MAIN_MODEL = "gpt-5.1"

# ───────────────── STYLES GLOBAUX (Dark / Mobile-first) ─────────────────
# La feuille de style suivante définit l'ensemble des règles pour une
# interface sombre, moderne et adaptée aux mobiles. Les couleurs sont
# légèrement plus claires que dans la version initiale pour améliorer
# la lisibilité. Les composants (cartes, boutons, onglets) sont
# uniformisés et utilisent des variables d'accentuation cohérentes.
st.markdown(
    """
    <style>
    /* Couleurs de base et polices */
    html, body, .stApp {
        background-color: #0f172a !important;
        color: #f1f5f9 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Inter", "SF Pro Text", "Segoe UI", sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        background-color: transparent !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0, 0, 0, 0) !important;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1.5rem;
        max-width: 780px;
    }
    h1, h2, h3, h4 {
        font-weight: 700;
        letter-spacing: 0.02em;
        color: #f1f5f9;
    }
    /* Cartes principales */
    .hero-card {
        border-radius: 20px;
        padding: 1.2rem 1.4rem;
        background: linear-gradient(135deg, #0f172a, #172a45);
        border: 1px solid #1e293b;
    }
    .sub-card {
        border-radius: 16px;
        padding: 0.9rem 1.1rem;
        background: #172a45;
        border: 1px solid #1e293b;
    }
    .small-label {
        font-size: 0.78rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.12em;
    }
    /* Tags */
    .tag-pill {
        display: inline-block;
        padding: 0.28rem 0.55rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 500;
        margin-right: 0.35rem;
        margin-bottom: 0.25rem;
        background: #1e293b;
        color: #e5e7eb;
        white-space: nowrap;
    }
    .tag-pill.danger { background: #7f1d1d; color: #fee2e2; }
    .tag-pill.warn   { background: #92400e; color: #fef3c7; }
    .tag-pill.info   { background: #1e40af; color: #dbeafe; }
    .tag-pill.safe   { background: #065f46; color: #d1fae5; }
    /* Grille des métriques */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.55rem;
        margin-top: 0.6rem;
    }
    @media (max-width: 640px) {
        .metric-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    .metric-card {
        border-radius: 14px;
        padding: 0.7rem 0.8rem;
        background: #0f172a;
        border: 1px solid #1e293b;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-bottom: 0.15rem;
    }
    .metric-value {
        font-size: 1.35rem;
        font-weight: 700;
        line-height: 1.1;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #cbd5e1;
        margin-top: 0.1rem;
    }
    .metric-bar-bg {
        margin-top: 0.3rem;
        width: 100%;
        height: 5px;
        border-radius: 999px;
        background: #1e293b;
        overflow: hidden;
    }
    .metric-bar-fill {
        height: 100%;
        border-radius: 999px;
    }
    /* Champs d'entrée */
    textarea, input {
        font-size: 0.9rem !important;
        background-color: #0f172a !important;
        color: #f1f5f9 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    /* Boutons */
    .stButton > button {
        background-color: #172a45 !important;
        color: #f1f5f9 !important;
        border-radius: 999px !important;
        border: 1px solid #334155 !important;
        padding: 0.55rem 0.9rem !important;
        font-size: 0.9rem !important;
    }
    .stButton > button:hover {
        border-color: #f97373 !important;
        color: #f97373 !important;
    }
    /* Onglets */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.3rem;
        overflow-x: auto;
        scrollbar-width: none;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        display: none;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        padding: 0.25rem 0.6rem;
        border-radius: 999px 999px 0 0;
        color: #cbd5e1;
        font-size: 0.9rem;
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 2px solid #f97373;
        color: #f97373 !important;
        font-weight: 600;
    }
    /* Réponses et copie */
    .reply-block {
        margin-top: 0.6rem;
    }
    .reply-box {
        width: 100%;
        background-color: #0f172a;
        color: #f1f5f9;
        border-radius: 12px;
        border: 1px solid #334155;
        padding: 0.75rem;
        white-space: pre-wrap;
        overflow-wrap: break-word;
        font-size: 0.9rem;
    }
    .copy-btn {
        margin-top: 0.5rem;
        border-radius: 999px;
        border: 1px solid #475569;
        background: #172a45;
        color: #e2e8f0;
        padding: 0.35rem 0.9rem;
        font-size: 0.85rem;
        cursor: pointer;
    }
    .copy-btn:hover {
        border-color: #f97373;
        color: #f97373;
    }
    /* Segmented control customisation */
    .mode-toggle {
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    /* Rendre les segments Calme/Roast bien cliquables sur le texte */
    [data-testid="stSegmentedControl"] button {
        cursor: pointer;
    }
    [data-testid="stSegmentedControl"] button > div {
        pointer-events: auto;
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
    "Sérieux les golems qui croient encore au CDI en 2025... "
    "Continuez à enrichir votre patron pendant que je fais x10 en dropshipping depuis Bali. "
    "La sélection est naturelle les shills. 🤡"
)
DEMO_FORUM_TOXIC = (
    "Face à la crise, le gouvernement prend ses responsabilités. "
    "Il est temps de demander des efforts à ceux qui profitent du système au détriment des travailleurs honnêtes. "
    "Cette réforme est la seule voie possible pour sauver notre modèle social, n'en déplaise aux agitateurs professionnels."
)

# ───────────────── LLM : ANALYSE ET RÉPONSE ─────────────────
def analyze_text_with_llm(text: str) -> Optional[Dict[str, Any]]:
    """
    Appelle le modèle OpenAI pour analyser un texte et renvoie un JSON
    conforme au schéma attendu par tout le reste de l'app. Si le texte
    est vide, retourne None.
    """
    if not text.strip():
        return None
    system_prompt = """
Tu es SUBTEXT-ENGINE, moteur d'analyse de communication, de rhétorique, de manipulation et de dynamique systémique, en français.

🎯 OBJECTIF GÉNÉRAL
Aider un utilisateur non spécialiste à :
1) Comprendre l'effet psychologique du texte (micro : individu).
2) Comprendre la logique de pouvoir et les intérêts en jeu (méso / macro).
3) Voir comment ce texte s'inscrit dans des récits plus larges (idéologie, politique, culture, management...).
4) Savoir si sa réaction est compréhensible.
5) Décider comment réagir (ou ne pas réagir).

⚠️ STYLE
- Langage simple, concret, sans jargon universitaire.
- Tu restes sobre, nuancé, pédagogique. Pas de catastrophisme.
- Tu expliques, tu ne juges pas l'utilisateur.

──────────────── SCHEMA JSON ATTENDU ────────────────

TU DOIS RENVOYER STRICTEMENT UN OBJET json AVEC CE SCHÉMA :

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
    "idéologie de mérite individuel",
    "management autoritaire",
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
    "power_dynamics": "3–5 phrases, vulgarisées au maximum, expliquant très concrètement qui a l'avantage, qui subit, quels acteurs sont impliqués et comment le message renforce ce rapport de force dans CE CAS PRÉCIS.",
    "narrative_frame": "2–3 phrases simples expliquant comment le texte cadre le problème (ex: sécurité vs liberté, mérite individuel, crise permanente, responsabilité personnelle vs collective, etc.), avec des exemples concrets liés au texte.",
    "macro_implications": [
      "jusqu'à 3 phrases (ou puces) décrivant, en langage du quotidien, les effets possibles à moyen / long terme sur la confiance, la coopération, la polarisation, la capacité des gens à discuter sereinement."
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
  ],

  "plain_translation": "Traduction en langage courant : ce que la personne est en train de faire / dire au niveau relationnel, en 1–3 phrases simples.",
  "reaction_validation": "1–3 phrases expliquant si la réaction de la personne qui reçoit le message est compréhensible, logique, ou si le texte est plutôt neutre.",

  "viral_punchline": "Une phrase très courte (max 12 mots), ultra cash et moqueuse, manière khey qui démontre le message. Elle peut être humiliante pour le comportement décrit, mais sans propos haineux envers un groupe protégé et sans appel à la violence."
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
- Tu expliques pour un public non spécialiste, avec un vocabulaire simple.
- Tu relies le micro au macro : quels récits, quels rapports de force, quelle vision du monde ?
- Tu restes sobre, analytique, pas militant.

Format de sortie :
- UNIQUEMENT un objet json valide conforme au schéma.
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
    persona_mode: str,
) -> Dict[str, str]:
    """
    Génère deux réponses (calme et assertive) à partir du texte original et
    de l'analyse. Le style de réponse dépend à la fois des
    préférences de l'utilisateur et du mode sélectionné (Calme vs Roast).

    - En mode « Roast », la réponse utilise toujours un système prompt de type
      "Khey" et force un style sarcastique / moqueur inspiré de JVC.
    - En mode « Calme », le comportement reste similaire à l'application
      originale : le système choisit entre un prompt empathique ou sarcastique
      selon le ton demandé par l'utilisateur.

    L'argument `emoji_allowed` est conservé mais n'est pas utilisé pour
    l'instant.
    """
    if not analysis or not original_text:
        return {"calm": "", "assertive": ""}
    use_sarcastic = False
    if persona_mode.lower() == "trash":
        use_sarcastic = True
    else:
        lower_tone = tone_pref.lower() if tone_pref else ""
        if "sarcastique" in lower_tone or "moqueur" in lower_tone:
            use_sarcastic = True
    if use_sarcastic:
        system_prompt = """
Tu es un "Khey" légendaire du forum 18-25 de JeuxVideo.com.
Important (technique) : tu dois renvoyer un unique objet json valide. Le mot « json » est volontairement en minuscules.

Rôle :
- Tu écris AU NOM DE LA PERSONNE QUI REÇOIT le message.
- Tu balances des réponses courtes, humiliantes, ironiques et très cash.
- Objectif : ridiculiser l'auteur du message par le sarcasme, la honte sociale et le mépris, façon meme internet.

Contraintes :
- Pas de propos haineux visant un groupe protégé.
- Pas d'appel à la violence ni de menaces explicites.
- Vocabulaire : "malaise", "ratio", "cheh", "golem", "brisé", "pleure", "touriste", "NPC", etc.
- Style : agressif, moqueur, khey JVC, mais légal.

Format JSON STRICT :
{
  "calm": "réponse courte, style khey mais un peu 'soft'",
  "assertive": "réponse courte, style khey très cash"
}
"""
    else:
        system_prompt = """
Tu es SUBTEXT-REPLY, spécialisé dans les réponses calmes et assertives.
Important (technique) : tu dois renvoyer un unique objet json valide. Le mot « json » est volontairement en minuscules.

Point de vue :
- Tu écris AU NOM DE LA PERSONNE QUI REÇOIT le message.
Mission :
- À partir du TEXTE ORIGINAL + d'un RÉSUMÉ D'ANALYSE fourni,
- Générer 2 réponses possibles :
 1) "calm" : posée, factuelle, sans attaque.
 2) "assertive" : posée mais ferme, pose des limites claires, sans insulte ni mépris.

Contraintes :
- 1–4 phrases max par réponse (environ 300 caractères).
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
        "plain_translation": analysis.get("plain_translation", ""),
    }
    user_prompt = f"""
Texte original reçu :
{original_text}

Résumé d'analyse (ne PAS renvoyer) :
{json.dumps(summary_for_reply, ensure_ascii=False)}

Préférences utilisateur :
- Ton souhaité : {tone_pref}
- Emojis autorisés : {'oui' if emoji_allowed else 'non'}

Génère UNIQUEMENT un objet json avec deux champs : "calm" et "assertive".
"""
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "system",
                "content": (
                    f"RÈGLE PRIORITAIRE : le ton demandé par l'utilisateur est « {tone_pref} ». "
                    "Respecte ce ton dans la forme, le vocabulaire et le niveau de directivité."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]
        completion = client.chat.completions.create(
            model=OPENAI_MAIN_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.5 if not use_sarcastic else 0.95,
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
    """Retourne un fragment HTML pour afficher un tag stylisé."""
    level_class = level if level in {"danger", "warn", "info", "safe"} else "info"
    return f"<span class='tag-pill {level_class}'>{text}</span>"

def get_score_color(score: int) -> str:
    """Sélectionne une couleur en fonction du score fourni."""
    try:
        s = int(score)
    except Exception:
        return "#f1f5f9"
    if s >= 75:
        return "#f87171"  # rouge
    if s >= 50:
        return "#fbbf24"  # ambre
    if s >= 25:
        return "#34d399"  # vert clair
    return "#6ee7b7"      # vert

def reset_app() -> None:
    """Réinitialise l'état de l'application lors de l'appui sur le bouton reset."""
    keys_to_clear = ["input_text", "analysis", "replies", "tone_pref", "emoji_allowed"]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

def render_reply_block(title: str, text: str) -> None:
    """Affiche un bloc de réponse avec un bouton de copie."""
    if not text:
        return
    escaped = html_lib.escape(text)
    js_text = json.dumps(text)
    st.markdown(
        f"""
        <div class="reply-block sub-card">
          <div style="font-size:0.9rem;margin-bottom:0.4rem;">{title}</div>
          <div class="reply-box">{escaped}</div>
          <button class="copy-btn" onclick='navigator.clipboard.writeText({js_text})'>
            📋 Copier la réponse
          </button>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_metric_card(label: str, score: int, sublabel: str) -> str:
    """Construit le HTML pour une carte métrique."""
    color = get_score_color(score)
    width = max(0, min(100, score))
    return (
        f"<div class='metric-card'>"
        f"<div class='metric-label'>{label}</div>"
        f"<div class='metric-value' style='color:{color};'>{score}%</div>"
        f"<div class='metric-sub'>{sublabel}</div>"
        f"<div class='metric-bar-bg'>"
        f"<div class='metric-bar-fill' style='width:{width}%;background:{color};'></div>"
        f"</div>"
        f"</div>"
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
if "persona_mode" not in st.session_state:
    st.session_state["persona_mode"] = "Calme"

# ───────────────── EN-TÊTE + TOGGLE DE MODE ─────────────────
# L'en-tête présente le basculeur de mode et les titres. On utilise
# des colonnes pour aligner correctement sur desktop tout en gardant
# une bonne adaptation sur mobile (les éléments s'empilent). Un
# `st.caption` explicatif suit le toggle pour clarifier la différence
# entre les modes.
with st.container():
    col_toggle, col_title = st.columns([1.2, 3], gap="small")
    with col_toggle:
        # Toggle Calme / Roast. La clé assure la persistance du choix.
        persona_mode = st.segmented_control(
            label="",
            options=["Calme", "Roast"],
            default=st.session_state.get("persona_mode", "Calme"),
            key="persona_toggle",
            label_visibility="collapsed",
            width="content",
        )
        st.session_state["persona_mode"] = persona_mode
    with col_title:
        st.markdown(
            "<h1 style='margin-bottom:0.1rem;'>👁️ SUBTEXT</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='color:#94a3b8;font-weight:500;font-size:0.95rem;line-height:1.3;'>"
            "Analyse le sous-texte d’un message.<br>Comprends la pression et choisis ta réponse."
            "</p>",
            unsafe_allow_html=True,
        )
    # Légende expliquant les deux modes
    if persona_mode == "Calme":
        st.caption("Mode Calme : complet, sérieux et défensif. Toutes les analyses sont affichées.")
    else:
        st.caption("Mode Roast : léger et impertinent, quelques détails sont masqués pour plus de rapidité.")

st.markdown("---")

# ───────────────── DEMO BAR + INPUT ─────────────────
# Cette section regroupe les exemples et la zone de saisie. Les boutons
# d'exemple sont disposés sur deux colonnes pour une meilleure
# ergonomie sur mobile. La zone de texte permet à l'utilisateur de
# coller ou écrire son message, suivie des actions Scanner / Reset.
with st.container():
    st.caption("Teste avec un exemple :")
    col_demo_left, col_demo_right = st.columns(2, gap="small")
    with col_demo_left:
        if st.button("📧 Manager", use_container_width=True):
            st.session_state["input_text"] = DEMO_EMAIL_MANAGER
            st.session_state["analysis"] = None
            st.session_state["replies"] = {"calm": "", "assertive": ""}
        if st.button("💔 Rupture", use_container_width=True):
            st.session_state["input_text"] = DEMO_SMS_RUPTURE
            st.session_state["analysis"] = None
            st.session_state["replies"] = {"calm": "", "assertive": ""}
    with col_demo_right:
        if st.button("💬 Post Réseau", use_container_width=True):
            st.session_state["input_text"] = DEMO_TWEET_POLITIQUE
            st.session_state["analysis"] = None
            st.session_state["replies"] = {"calm": "", "assertive": ""}
        if st.button("📰 Article Pol.", use_container_width=True):
            st.session_state["input_text"] = DEMO_FORUM_TOXIC
            st.session_state["analysis"] = None
            st.session_state["replies"] = {"calm": "", "assertive": ""}

    st.markdown("**Ou colle ton texte ici :**")
    st.text_area(
        label="",
        key="input_text",
        height=180,
        placeholder="Colle le message, l'article, le discours, le tweet ou le post ici…",
    )
    st.caption("ℹ️ Vos messages ne sont ni stockés ni partagés. Ils servent uniquement le temps de l'analyse.")
    col_scan, col_reset = st.columns([3, 1], gap="small")
    with col_scan:
        scan_clicked = st.button("🔍 Scanner le sous-texte", use_container_width=True)
    with col_reset:
        st.button("🧹 Réinitialiser", use_container_width=True, on_click=reset_app)

    # Déclencher l'analyse si l'utilisateur clique sur le bouton
    if scan_clicked:
        input_text = st.session_state.get("input_text", "")
        if not input_text.strip():
            st.warning("Colle d'abord un texte à analyser.")
        else:
            # Message d'attente rassurant (~30s)
            with st.spinner("⏳ Analyse du message en cours… (~30 secondes max)\nJe décortique tout le sous-texte, je ne suis pas planté 😌"):
                analysis = analyze_text_with_llm(input_text)
            st.session_state["analysis"] = analysis
            st.session_state["replies"] = {"calm": "", "assertive": ""}
            if analysis:
                # Déterminer le ton par défaut en fonction du mode sélectionné
                default_tone = "sarcastique / moqueur (déconseillé)" if persona_mode == "Roast" else "calme"
                with st.spinner("🛡️ Préparation des suggestions de réponse…"):
                    try:
                        default_replies = generate_replies_with_llm(
                            original_text=input_text,
                            analysis=analysis,
                            tone_pref=default_tone,
                            emoji_allowed=True,
                            persona_mode=persona_mode,
                        )
                        st.session_state["replies"] = default_replies
                    except Exception:
                        pass
                st.toast("Analyse terminée ✅", icon="✅")

# ───────────────── AFFICHAGE DES RÉSULTATS ─────────────────
analysis = st.session_state.get("analysis")
if analysis:
    # Extraction des variables d'analyse
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
    plain_translation = (analysis.get("plain_translation") or "").strip()
    reaction_validation = (analysis.get("reaction_validation") or "").strip()
    viral_punchline = (analysis.get("viral_punchline") or "").strip()
    highlights = analysis.get("highlights", []) or []
    fact_checks = analysis.get("fact_checks", []) or []
    recommended_actions = analysis.get("recommended_actions", []) or []

    # Vue d'ensemble dans une carte héro
    st.markdown("<div class='hero-card'>", unsafe_allow_html=True)
    st.markdown("<div class='small-label'>Vue d'ensemble</div>", unsafe_allow_html=True)
    score_color = get_score_color(global_score)
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;margin-top:0.3rem;margin-bottom:0.6rem;gap:0.9rem;flex-wrap:wrap;">
            <div style="min-width:140px;flex:0 0 auto;">
                <div style="font-size:0.9rem;color:#94a3b8;">Indice de pression</div>
                <div style="font-size:2.3rem;font-weight:800;color:{score_color};margin-top:0.05rem;">
                    {global_score}%
                </div>
                <div style="font-size:0.95rem;color:#e2e8f0;font-weight:500;margin-top:0.05rem;">
                    {global_label}
                </div>
                <div style="font-size:0.8rem;color:#94a3b8;margin-top:0.25rem;">
                    Type de contenu : {content_type or '—'}
                </div>
            </div>
            <div style="flex:1;min-width:160px;">
                <div style="height:10px;border-radius:999px;background:#1e293b;overflow:hidden;">
                    <div style="width:{global_score}%;height:100%;background:{score_color};"></div>
                </div>
                <div style="margin-top:0.45rem;font-size:0.9rem;color:#cbd5e1;">
                    {main_effect or 'Effet émotionnel difficile à formuler, mais le message semble chargé.'}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Effets secondaires
    if secondary_effects:
        st.markdown("<div class='small-label' style='margin-top:0.6rem;'>Autres réactions possibles</div>", unsafe_allow_html=True)
        effects_html = ""
        for eff in secondary_effects:
            effects_html += render_tag(eff, "info")
        st.markdown(effects_html, unsafe_allow_html=True)
    # Tags
    if tags:
        st.markdown("<div class='small-label' style='margin-top:0.6rem;'>Signaux détectés</div>", unsafe_allow_html=True)
        tag_html = ""
        for t in tags:
            low = t.lower()
            lvl = "info"
            if any(k in low for k in ["insulte", "mépris", "agressif", "hostile", "bouc émissaire"]):
                lvl = "danger"
            elif any(k in low for k in ["culpabilisation", "pression", "chantage"]):
                lvl = "warn"
            elif any(k in low for k in ["neutre", "apaisant", "bienveillant"]):
                lvl = "safe"
            tag_html += render_tag(t, lvl)
        st.markdown(tag_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Traduction en langage clair
    if plain_translation:
        st.markdown("")
        st.markdown("<div class='sub-card'>", unsafe_allow_html=True)
        st.markdown("**🧠 En vrai, ce que la personne est en train de dire :**", unsafe_allow_html=True)
        st.markdown(plain_translation)
        st.markdown("</div>", unsafe_allow_html=True)

    # Construction des onglets
    tab_labels: List[str] = []
    fact_available = content_type in ("article", "discours", "forum", "réseau_social") and bool(fact_checks)
    response_available = content_type not in ("article", "discours")
    tab_labels.append("🧩 Diagnostic")
    tab_labels.append("🎯 Actions")
    if persona_mode == "Calme":
        tab_labels.append("🔍 Décryptage")
    tab_labels.append("🧪 Fact-check" if fact_available else "🧪 Fact-check (N/A)")
    tab_labels.append("🛡️ Réponse" if response_available else "🛡️ Réponse (N/A)")
    tabs = st.tabs(tab_labels)
    idx = 0

    # Diagnostic
    with tabs[idx]:
        st.markdown("#### Diagnostic rapide")
        st.markdown("<div class='sub-card' style='margin-bottom:0.9rem;'>", unsafe_allow_html=True)
        st.markdown("**👤 Qui parle à qui ?**", unsafe_allow_html=True)
        rel_type = profile.get("relation_type", "—")
        channel = profile.get("channel", "—")
        power_asym = profile.get("power_asymmetry", "—")
        target_audience = profile.get("target_audience", "—")
        col_p1, col_p2 = st.columns(2, gap="small")
        with col_p1:
            st.markdown(f"- **Relation :** {rel_type}")
            st.markdown(f"- **Canal :** {channel}")
        with col_p2:
            st.markdown(f"- **Rapport de force :** {power_asym}")
            st.markdown(f"- **Public visé :** {target_audience}")
        st.markdown("</div>", unsafe_allow_html=True)
        # Metrics
        h_score = int(hostility.get("score", 0) or 0)
        h_label = hostility.get("label", "—")
        m_score = int(manipulation.get("score", 0) or 0)
        m_label = manipulation.get("label", "—")
        p_score = int(pressure.get("score", 0) or 0)
        p_label = pressure.get("label", "—")
        st.markdown("<div class='small-label'>Niveau de tension du message</div>", unsafe_allow_html=True)
        st.markdown("<div class='metric-grid'>", unsafe_allow_html=True)
        st.markdown(render_metric_card("Hostilité", h_score, h_label), unsafe_allow_html=True)
        st.markdown(render_metric_card("Manipulation / pression", m_score, m_label), unsafe_allow_html=True)
        st.markdown(render_metric_card("Pression sociale", p_score, p_label), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("Plus le pourcentage est haut, plus le message est lourd/agressif sur cet axe.")
        if reaction_validation:
            st.markdown("<div class='sub-card' style='margin-top:0.9rem;'>", unsafe_allow_html=True)
            st.markdown("**🎭 Est-ce que ta réaction est normale ?**", unsafe_allow_html=True)
            st.markdown(reaction_validation)
            st.markdown("</div>", unsafe_allow_html=True)
        if highlights and persona_mode == "Calme":
            with st.expander("🔎 Passages précis repérés dans le texte", expanded=False):
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
                            f"<p style='font-size:0.9rem;color:#e2e8f0;margin-top:0.3rem;'>{explanation}</p>",
                            unsafe_allow_html=True,
                        )
                    st.markdown("</div>", unsafe_allow_html=True)
    idx += 1

    # Actions
    with tabs[idx]:
        st.markdown("#### Que faire concrètement ?")
        if not recommended_actions:
            st.caption("Aucune action recommandée par l'analyse.")
        else:
            actions_sorted = sorted(recommended_actions, key=lambda a: a.get("priority", 3))
            st.caption("🔴 Priorité 1 : immédiat · 🟠 2 : important · 🟡 3 : optionnel")
            for act in actions_sorted:
                label = (act.get("label") or "").strip()
                detail = (act.get("detail") or "").strip()
                priority = act.get("priority", 3)
                if priority == 1:
                    prio_icon = "🔴"
                elif priority == 2:
                    prio_icon = "🟠"
                else:
                    prio_icon = "🟡"
                if persona_mode == "Roast":
                    st.markdown(f"{prio_icon} **{label}**")
                else:
                    st.markdown("<div class='sub-card' style='margin-bottom:0.6rem;'>", unsafe_allow_html=True)
                    st.markdown(f"{prio_icon} **{label}**")
                    if detail:
                        st.markdown(f"- {detail}")
                    st.markdown("</div>", unsafe_allow_html=True)
    idx += 1

    # Décryptage (uniquement en mode Calme)
    if persona_mode == "Calme":
        with tabs[idx]:
            st.markdown("#### Décryptage de fond")
            with st.expander("Voir l'analyse détaillée du contexte et des rapports de force", expanded=False):
                st.markdown("<div class='sub-card' style='margin-bottom:0.8rem;'>", unsafe_allow_html=True)
                scale = systemic.get("scale", "—")
                power_dyn = systemic.get("power_dynamics", "—")
                narrative_frame = systemic.get("narrative_frame", "—")
                macro_implications = systemic.get("macro_implications", []) or []
                st.markdown("**📏 Échelle analysée**")
                st.markdown(f"- {scale}")
                st.markdown("")
                st.markdown("**🧠 1. Qui tient la position de force ici ?**")
                st.markdown(f"➡️ {power_dyn}")
                st.markdown("")
                st.markdown("**🧱 2. Quelle histoire le message raconte sur le monde ?**")
                st.markdown(f"➡️ {narrative_frame}")
                st.markdown("")
                if macro_implications:
                    st.markdown("**🌍 3. Si ce type de message se répète partout…**")
                    for mi in macro_implications:
                        st.markdown(f"- {mi}")
                st.markdown("</div>", unsafe_allow_html=True)
        idx += 1

    # Fact-check
    with tabs[idx]:
        st.markdown("#### Analyse factuelle (si applicable)")
        if fact_available:
            for fc in fact_checks:
                claim = (fc.get("claim") or "").strip()
                verdict = (fc.get("verdict") or "").strip()
                explanation = (fc.get("explanation") or "").strip()
                sources = fc.get("sources", []) or []
                st.markdown("<div class='sub-card' style='margin-bottom:0.6rem;'>", unsafe_allow_html=True)
                if claim:
                    st.markdown(f"**Affirmation :** {claim}")
                if verdict:
                    v_low = verdict.lower()
                    level = "info"
                    if "faux" in v_low:
                        level = "danger"
                    elif "partiellement" in v_low:
                        level = "warn"
                    elif "vrai" in v_low:
                        level = "safe"
                    verdict_badge = f"<span class='tag-pill {level}'>{verdict}</span>"
                    st.markdown(f"**Verdict :** {verdict_badge}", unsafe_allow_html=True)
                if explanation:
                    st.markdown(f"**Pourquoi :** {explanation}")
                if sources:
                    st.markdown("**Sources possibles :**")
                    for src in sources:
                        st.markdown(f"- {src}")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("Cette section n'est pas disponible pour ce type de contenu.")
    idx += 1

    # Réponse
    with tabs[idx]:
        if not response_available:
            st.caption("SUBTEXT ne propose pas de réponse rédigée pour ce type de contenu (informel).")
        else:
            st.markdown("#### Construire ta réponse")
            col_tone, col_emoji = st.columns(2, gap="small")
            with col_tone:
                tone_options = [
                    "calme",
                    "professionnel",
                    "empathique",
                    "direct mais respectueux",
                    "sarcastique / moqueur (déconseillé)",
                ]
                default_index = 4 if persona_mode == "Roast" else 0
                current_tone = st.session_state.get("tone_pref", tone_options[default_index])
                if current_tone in tone_options:
                    default_index = tone_options.index(current_tone)
                st.session_state["tone_pref"] = st.selectbox(
                    "Style de réponse",
                    tone_options,
                    index=default_index,
                    key="tone_select",
                )
            with col_emoji:
                st.session_state["emoji_allowed"] = st.checkbox(
                    "Autoriser les emojis",
                    value=st.session_state.get("emoji_allowed", True),
                    key="emoji_checkbox",
                )
            tone_pref = st.session_state["tone_pref"]
            emoji_allowed = st.session_state["emoji_allowed"]
            original_for_reply = st.session_state.get("input_text", "")
            st.caption("SUBTEXT te suggère 2 versions : une calme et une plus ferme.")
            if st.button("🛡️ Générer / mettre à jour la réponse suggérée", use_container_width=True):
                with st.spinner("Génération de la réponse…"):
                    replies = generate_replies_with_llm(
                        original_text=original_for_reply,
                        analysis=analysis,
                        tone_pref=tone_pref,
                        emoji_allowed=emoji_allowed,
                        persona_mode=persona_mode,
                    )
                st.session_state["replies"] = replies
                st.toast("Réponse générée ✅", icon="✅")
            replies = st.session_state["replies"]
            if replies.get("calm") or replies.get("assertive"):
                tabs_reply = st.tabs(["😌 Version calme", "💬 Version assertive"])
                with tabs_reply[0]:
                    if replies.get("calm"):
                        render_reply_block("Réponse calme (posée)", replies["calm"])
                    else:
                        st.caption("Pas de réponse calme dispo.")
                with tabs_reply[1]:
                    if replies.get("assertive"):
                        render_reply_block("Réponse assertive (ferme mais propre)", replies["assertive"])
                    else:
                        st.caption("Pas de réponse assertive dispo.")
            else:
                st.caption("Aucune réponse générée pour l'instant.")

    # Résumé partageable
    st.markdown("---")
    st.subheader("📸 Résumé partageable")
    score = global_score
    clean_score_color = get_score_color(score)
    clean_context = st.session_state["input_text"][:90].replace('"', '&quot;').replace('\n', ' ') + "..."
    clean_punchline = plain_translation.replace('"', '&quot;') if plain_translation else ""
    clean_viral = viral_punchline.replace('"', '&quot;') if viral_punchline else ""
    clean_tags = "".join([
        f"<span style='background:#334155;padding:2px 6px;border-radius:4px;color:#e2e8f0;margin-right:5px;font-size:0.7rem;'>{t}</span>"
        for t in tags[:3]
    ]) or "<span style='font-size:0.7rem;color:#6b7280;'>aucun signal critique</span>"

    # Punchline bienveillante en mode Calme, punchline violente uniquement en mode Roast
    if persona_mode == "Calme":
        supportive_text = reaction_validation or "Tu n'exagères pas : ce message est vraiment lourd pour toi."
        clean_supportive = supportive_text.replace('"', '&quot;')
        punchline_block = f"""
  <div style="background:#172a45;border:1px solid #38bdf8;border-radius:8px;padding:0.8rem;text-align:center;margin-bottom:1rem;">
    <div style="font-size:0.75rem;color:#38bdf8;text-transform:uppercase;margin-bottom:0.2rem;font-weight:700;">💬 Message pour toi :</div>
    <div style="font-size:1.05rem;font-weight:700;color:#e2e8f0;">"{clean_supportive}"</div>
  </div>
"""
    else:
        punchline_block = f"""
  <div style="background:#172a45;border:1px solid #f97373;border-radius:8px;padding:0.8rem;text-align:center;margin-bottom:1rem;">
    <div style="font-size:0.75rem;color:#f97373;text-transform:uppercase;margin-bottom:0.2rem;font-weight:700;">🔥 Punchline SUBTEXT :</div>
    <div style="font-size:1.15rem;font-weight:800;color:#f1f5f9;">"{clean_viral}"</div>
  </div>
"""

    html_code = f"""
<div style="border-radius:20px;padding:1.5rem;background:radial-gradient(circle at top left, #172a45, #0f172a);border:1px solid #334155;box-shadow:0 4px 20px rgba(0,0,0,0.5);color:#f1f5f9;font-family:sans-serif;margin-top:1rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #334155;padding-bottom:0.8rem;margin-bottom:1rem;">
    <div style="font-size:0.8rem;text-transform:uppercase;letter-spacing:0.15em;color:#94a3b8;font-weight:700;">RAPPORT SUBTEXT</div>
    <div style="font-size:0.7rem;background:#334155;padding:2px 6px;border-radius:4px;color:#e2e8f0;">SCAN IA</div>
  </div>
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.2rem;gap:0.8rem;flex-wrap:wrap;">
    <div style="display:flex;align-items:baseline;">
      <div style="font-size:2.2rem;font-weight:800;line-height:1;color:{clean_score_color};">{score}%</div>
      <div style="font-size:0.9rem;margin-left:0.5rem;font-weight:500;color:{clean_score_color};">{global_label}</div>
    </div>
    <div>{clean_tags}</div>
  </div>
  <div style="font-style:italic;font-size:0.9rem;color:#94a3b8;margin-bottom:1rem;border-left:3px solid #475569;padding-left:0.8rem;background:rgba(255,255,255,0.03);padding:0.5rem 0.8rem;border-radius:0 8px 8px 0;">
    "{clean_context}"
  </div>
  <div style="margin-bottom:1rem;">
    <div style="font-size:0.7rem;text-transform:uppercase;color:#475569;margin-bottom:0.3rem;font-weight:700;">TRADUCTION RELATIONNELLE :</div>
    <div style="font-size:1.05rem;font-weight:600;color:#e2e8f0;line-height:1.4;">{clean_punchline}</div>
  </div>
  {punchline_block}
  <div style="font-size:0.75rem;color:#475569;text-align:right;border-top:1px solid #334155;padding-top:0.5rem;">
    Généré par SUBTEXT • Détecteur de bullshit
  </div>
</div>
"""
    st.markdown(html_code, unsafe_allow_html=True)
    st.caption("Prends une capture de cet encadré pour partager le scan.")
    st.markdown("")
    st.markdown(
        "<p style='text-align:center;color:#475569;font-size:0.8rem;'>Made by Thomas — MVP SUBTEXT</p>",
        unsafe_allow_html=True,
    )
else:
    # message d'accueil quand aucune analyse n'est encore faite
    st.markdown(
        "<p style='color:#94a3b8;font-size:0.9rem;'>Après avoir lancé l'analyse, les résultats s'afficheront ici sous forme de carte et de conseils.</p>",
        unsafe_allow_html=True,
    )
