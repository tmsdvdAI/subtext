import json
import re
from typing import Optional, Tuple, List

import requests
from bs4 import BeautifulSoup
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
    return detected_type.lower() in conversational_types


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
- Tu n'ajoutes AUCUN texte hors du JSON.
"""


# ───────────────── STATE ─────────────────

if "analysis_data" not in st.session_state:
    st.session_state["analysis_data"] = None
if "source_text" not in st.session_state:
    st.session_state["source_text"] = ""
if "word_count" not in st.session_state:
    st.session_state["word_count"] = 0


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
    )
else:
    st.info(
        "🔗 Analyse par URL arrive bientôt.\n\n"
        "Pour l’instant, colle simplement le texte de l’article ou du post à la main. "
        "Cela garantit une analyse plus fiable et évite les bugs de parsing."
    )
    # On bloque ici pour ne pas afficher les champs URL / forum
    st.stop()


analyze_button = st.button("Analyser ce texte")



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
                model="gpt-4.1-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": source_text,
                    },
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

    # ───────── VUE D’ENSEMBLE ─────────
    st.subheader("Vue d’ensemble")

    col_meta1, col_meta2 = st.columns([2, 1])

    detected_type = meta.get("detected_type", "other") or "other"
    intention = meta.get("intention", "").strip() or "Non précisé"

    with col_meta1:
        st.markdown(f"**Type détecté :** `{detected_type}`")
        st.markdown(f"**Intention apparente :** {intention}")
        st.markdown(f"**Résumé neutre :** {summary.get('neutral', '')}")

        # Cas article / news / discours politique
        if detected_type in ["article", "blog", "news", "political_speech"]:
            cred_score = int(credibility.get("score", 0) or 0)
            cred_justif = credibility.get("justification", "")
            art_bias = politics.get("article_bias", "")
            art_bias_score = int(politics.get("article_bias_score", 0) or 0)

            st.markdown("**Crédibilité de la source :**")
            render_score("Crédibilité perçue", cred_score)
            if cred_justif:
                st.caption(cred_justif)

            if art_bias:
                st.markdown(
                    f"**Bord politique du texte :** {art_bias} ({art_bias_score}/100)"
                )

        # Cas forum / réseaux
        if detected_type in ["forum_post", "social_post", "comment"]:
            auth_bias = politics.get("author_bias", "")
            auth_bias_score = int(politics.get("author_bias_score", 0) or 0)
            if auth_bias:
                st.markdown(
                    f"**Orientation probable de l'auteur :** {auth_bias} ({auth_bias_score}/100)"
                )

    with col_meta2:
        st.markdown("**Risque cognitif global**")
        risk_score = int(cog_risk.get("score", 0) or 0)
        render_score("Risque cognitif", risk_score)
        st.caption(
            "Facteurs principaux : "
            + (", ".join(cog_risk.get("factors", [])) or "Non précisés")
        )
        st.caption(f"Confiance globale de l’analyse : {overall_conf}/100")

    st.write("---")

    # ───────── PROPOSITION DE RÉPONSE (juste après la vue d’ensemble) ─────────
    st.subheader("💬 Générer une réponse à ce message ?")

    reply_button = st.button("Proposer une réponse", key="reply_after_analysis")

    if reply_button:
        if is_conversational_type(detected_type):
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
                        f"{summary.get('neutral', '')}\n\n"
                        "Intention apparente :\n"
                        f"{meta.get('intention', '')}\n"
                    )

                    reply_resp = client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[
                            {"role": "system", "content": reply_system_prompt},
                            {"role": "user", "content": reply_user_content},
                        ],
                    )

                    reply_text = reply_resp.choices[0].message.content.strip()

                    st.success("✅ Réponse générée ci-dessous 👇")
                    st.markdown("**Réponse suggérée :**")
                    st.write(reply_text)

                except Exception as e:
                    st.error(f"Erreur lors de la génération de la réponse : {e}")
        else:
            st.info(
                "Ce contenu n'a pas été identifié comme conversationnel "
                "(mail / DM / forum). La génération de réponse est désactivée pour ce type."
            )

    # ───────── SCORES DÉTAILLÉS ─────────
    st.subheader("Scores cognitifs")

    col1, col2, col3, col4, col5 = st.columns(5)

    noise = int(scores.get("noise", 0) or 0)
    manip = int(scores.get("manipulation", 0) or 0)
    host = int(scores.get("hostility", 0) or 0)
    emo = int(scores.get("emotional_intensity", 0) or 0)
    info_val = int(scores.get("informational_value", 0) or 0)

    with col1:
        render_score("Bruit", noise)
    with col2:
        render_score("Manipulation", manip)
    with col3:
        render_score("Hostilité", host)
    with col4:
        render_score("Émotion", emo)
    with col5:
        render_score("Valeur info", info_val)

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

    # ───────── TECHNIQUES ─────────
    with st.expander("Techniques rhétoriques détectées"):
        if not techniques:
            st.write("Aucune technique marquante détectée.")
        else:
            for t in techniques:
                label = t.get("label", "")
                excerpt = t.get("excerpt", "")
                st.markdown(f"- **{label}** — « {excerpt} »")

    # ───────── CLAIMS ─────────
    with st.expander("Claims factuels & pseudo fact-check (connaissances internes)"):
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

    # ───────── ACTIONS ─────────
    st.subheader("Actions possibles")
    sugg = actions.get("suggested", []) or []
    none_needed = actions.get("none_needed", False)

    if none_needed and not sugg:
        st.write("✅ Aucune action particulière n’est nécessaire.")
    else:
        if sugg:
            for a in sugg:
                st.markdown(f"✓ {a}")
        if none_needed:
            st.caption(
                "Le modèle estime qu’aucune action supplémentaire critique n’est nécessaire."
            )

    # ───────── ANALYSE SYSTÉMIQUE ─────────
    with st.expander("Analyse systémique (optionnelle)"):
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
                st.markdown("**Diagramme systémique (code Mermaid à copier) :**")
                st.code(mermaid, language="mermaid")

    # ───────── JSON BRUT ─────────
    with st.expander("Voir le JSON brut (debug)"):
        st.json(data)


   
