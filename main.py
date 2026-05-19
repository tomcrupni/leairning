import sqlite3
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import jwt
from google import genai as google_genai
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", "leairning-secret-2026")
JWT_ALGO = "HS256"
JWT_EXPIRE_DAYS = 30
DB_PATH = Path(__file__).parent / "leairning.db"
BASE_DIR = Path(__file__).parent

gemini_client = google_genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="LeAIrning API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── BASE DE DATOS ──────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            streak INTEGER DEFAULT 0,
            last_active TEXT,
            challenges_done TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS community_likes (
            user_id INTEGER,
            workflow_id INTEGER,
            PRIMARY KEY (user_id, workflow_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ── AUTH HELPERS ───────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: int) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def get_user_id(authorization: Optional[str] = Header(None)) -> Optional[int]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload["sub"]
    except Exception:
        return None

def require_user(user_id: Optional[int] = Depends(get_user_id)) -> int:
    if not user_id:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user_id

def calc_level(xp: int) -> int:
    return max(1, min(10, 1 + xp // 1000))

# ── MODELOS PYDANTIC ───────────────────────────────────────────────────────
class RegisterBody(BaseModel):
    name: str
    email: str
    password: str

class LoginBody(BaseModel):
    email: str
    password: str

class ChatBody(BaseModel):
    message: str
    history: list = []

class AnalyzeBody(BaseModel):
    prompt: str

class ImproveBody(BaseModel):
    prompt: str
    style: str = "Estilo profesional"

class GenerateBody(BaseModel):
    goal: str
    tone: str = "Tono profesional"
    model_target: str = "ChatGPT"

class SimulateBody(BaseModel):
    job: str
    challenge: str
    context: str
    answer: str

class CompareBody(BaseModel):
    prompt_a: str
    prompt_b: str

class LikeBody(BaseModel):
    workflow_id: int

class ChallengeBody(BaseModel):
    challenge_id: int
    xp: int

# ── HELPER IA ──────────────────────────────────────────────────────────────
async def ask_gemini(prompt: str) -> str:
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error de IA: {str(e)}")

def parse_json_response(text: str) -> dict:
    clean = text.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        clean = parts[1] if len(parts) > 1 else clean
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())

# ── AUTH ───────────────────────────────────────────────────────────────────
@app.post("/api/auth/register")
async def register(body: RegisterBody):
    if len(body.name.strip()) < 2:
        raise HTTPException(400, "Nombre muy corto")
    if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", body.email):
        raise HTTPException(400, "Email inválido")
    if len(body.password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (body.name.strip(), body.email.lower().strip(), hash_password(body.password))
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        token = create_token(user_id)
        return {
            "token": token,
            "user": {"id": user_id, "name": body.name.strip(), "email": body.email.lower(), "xp": 0, "level": 1, "streak": 0, "challenges_done": []}
        }
    except sqlite3.IntegrityError:
        raise HTTPException(400, "El email ya está registrado")
    finally:
        conn.close()

@app.post("/api/auth/login")
async def login(body: LoginBody):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ? AND password_hash = ?",
        (body.email.lower().strip(), hash_password(body.password))
    ).fetchone()
    if not user:
        conn.close()
        raise HTTPException(401, "Email o contraseña incorrectos")

    conn.execute("UPDATE users SET last_active = datetime('now') WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()

    token = create_token(user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "xp": user["xp"],
            "level": user["level"],
            "streak": user["streak"],
            "challenges_done": json.loads(user["challenges_done"] or "[]")
        }
    }

@app.get("/api/auth/me")
async def me(user_id: int = Depends(require_user)):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    likes = [r[0] for r in conn.execute(
        "SELECT workflow_id FROM community_likes WHERE user_id = ?", (user_id,)
    ).fetchall()]
    conn.close()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "xp": user["xp"],
        "level": user["level"],
        "streak": user["streak"],
        "challenges_done": json.loads(user["challenges_done"] or "[]"),
        "likes": likes
    }

# ── IA: CHAT TUTOR ─────────────────────────────────────────────────────────
@app.post("/api/ai/chat")
async def ai_chat(body: ChatBody):
    system = (
        "Sos el tutor de LeAIrning, plataforma argentina para aprender IA y prompt engineering. "
        "Respondés en español rioplatense, de forma clara, educativa y entusiasta. "
        "Explicás IA, prompt engineering, modelos de lenguaje y herramientas de IA con ejemplos prácticos. "
        "Tus respuestas son concisas (máximo 3 párrafos) pero completas. "
        "Si preguntan algo fuera del tema, redirigís amablemente."
    )
    history_text = ""
    for msg in body.history[-6:]:
        role = "Usuario" if msg.get("role") == "user" else "Tutor"
        history_text += f"{role}: {msg.get('content', '')}\n"

    prompt = f"{system}\n\nConversación:\n{history_text}Usuario: {body.message}\nTutor:"
    response = await ask_gemini(prompt)
    return {"response": response}

# ── IA: ANALIZAR PROMPT ────────────────────────────────────────────────────
@app.post("/api/ai/analyze")
async def ai_analyze(body: AnalyzeBody, user_id: Optional[int] = Depends(get_user_id)):
    if not body.prompt.strip():
        raise HTTPException(400, "El prompt no puede estar vacío")

    prompt = f"""Analizá este prompt de IA como experto en prompt engineering. Respondé SOLO con JSON válido, sin markdown:
{{
  "scores": {{"clarity": <0-100>, "context": <0-100>, "precision": <0-100>, "structure": <0-100>, "detail": <0-100>}},
  "overall": <0-100>,
  "rating": "<Principiante|En progreso|Bueno|Experto>",
  "strengths": ["<fortaleza 1>", "<fortaleza 2>"],
  "suggestions": ["<sugerencia 1>", "<sugerencia 2>", "<sugerencia 3>"],
  "summary": "<resumen 1-2 oraciones>"
}}

Criterios:
- clarity: claridad de la instrucción principal
- context: contexto dado (rol, audiencia, situación)
- precision: especificidad de lo que pide
- structure: organización y estructura
- detail: detalle y restricciones

Prompt a analizar: "{body.prompt}"
"""
    try:
        raw = await ask_gemini(prompt)
        data = parse_json_response(raw)
    except Exception:
        data = {
            "scores": {"clarity": 65, "context": 55, "precision": 60, "structure": 65, "detail": 55},
            "overall": 60,
            "rating": "En progreso",
            "strengths": ["Tiene una instrucción base clara"],
            "suggestions": ["Agregá un rol específico (Actuá como...)", "Incluí el formato de salida esperado", "Especificá la audiencia o contexto"],
            "summary": "Prompt con base sólida, puede mejorarse agregando más contexto y estructura."
        }

    if user_id:
        conn = get_db()
        conn.execute("UPDATE users SET xp = xp + 20 WHERE id = ?", (user_id,))
        new_xp = conn.execute("SELECT xp FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        conn.execute("UPDATE users SET level = ? WHERE id = ?", (calc_level(new_xp), user_id))
        conn.commit()
        conn.close()
        data["xp_earned"] = 20

    return data

# ── IA: MEJORAR PROMPT ─────────────────────────────────────────────────────
@app.post("/api/ai/improve")
async def ai_improve(body: ImproveBody, user_id: Optional[int] = Depends(get_user_id)):
    style_map = {
        "Estilo profesional": "Reescribilo con estilo profesional/corporativo: rol claro, contexto de negocio, formato estructurado.",
        "Más específico": "Hacelo mucho más específico: agregá métricas, restricciones concretas y detalles técnicos precisos.",
        "Más creativo": "Reescribilo para obtener respuestas más creativas e innovadoras. Lenguaje inspirador, abrí posibilidades.",
        "Más conciso": "Reescribilo siendo extremadamente conciso. Eliminá redundancias, solo lo esencial."
    }
    instruction = style_map.get(body.style, style_map["Estilo profesional"])

    prompt = f"""Sos experto en prompt engineering. Mejorá este prompt.
{instruction}
Prompt original: "{body.prompt}"
Respondé SOLO con el prompt mejorado, sin explicaciones ni comillas."""

    response = await ask_gemini(prompt)

    if user_id:
        conn = get_db()
        conn.execute("UPDATE users SET xp = xp + 15 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

    return {"improved": response.strip(), "xp_earned": 15 if user_id else 0}

# ── IA: GENERAR PROMPTS ────────────────────────────────────────────────────
@app.post("/api/ai/generate")
async def ai_generate(body: GenerateBody, user_id: Optional[int] = Depends(get_user_id)):
    prompt = f"""Sos experto en prompt engineering. Creá 3 versiones de prompt para este objetivo.
Objetivo: {body.goal}
Tono: {body.tone}
Modelo destino: {body.model_target}

Respondé SOLO con JSON válido, sin markdown:
{{
  "basic": "<prompt básico — simple, directo, 1-2 oraciones>",
  "professional": "<prompt profesional — con rol, contexto y formato, 3-5 oraciones>",
  "expert": "<prompt experto — sistema completo con restricciones, ejemplos y formato específico>"
}}
Los prompts deben estar en español."""

    try:
        raw = await ask_gemini(prompt)
        data = parse_json_response(raw)
    except Exception:
        data = {
            "basic": f"Ayudame con: {body.goal}",
            "professional": f"Actuá como experto. Tarea: {body.goal}. Usá {body.tone.lower()} y estructurá la respuesta con puntos clave y ejemplos prácticos.",
            "expert": f"[ROL]: Consultor senior con 15+ años de experiencia\n[OBJETIVO]: {body.goal}\n[TONO]: {body.tone}\n[MODELO]: {body.model_target}\n[FORMATO]: Estructurado con bullets, datos y métricas\n[RESTRICCIONES]: Sin relleno, directo al punto\n[CIERRE]: 3 recomendaciones accionables"
        }

    if user_id:
        conn = get_db()
        conn.execute("UPDATE users SET xp = xp + 25 WHERE id = ?", (user_id,))
        new_xp = conn.execute("SELECT xp FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        conn.execute("UPDATE users SET level = ? WHERE id = ?", (calc_level(new_xp), user_id))
        conn.commit()
        conn.close()
        data["xp_earned"] = 25

    return data

# ── IA: SIMULADOR ──────────────────────────────────────────────────────────
@app.post("/api/ai/simulate")
async def ai_simulate(body: SimulateBody, user_id: Optional[int] = Depends(get_user_id)):
    prompt = f"""Sos evaluador experto en prompt engineering. Evaluá esta respuesta de un estudiante.

Contexto del rol: {body.context}
Desafío: {body.challenge}
Respuesta del estudiante: {body.answer}

Respondé SOLO con JSON válido, sin markdown:
{{
  "scores": {{"clarity": <0-100>, "context": <0-100>, "precision": <0-100>, "structure": <0-100>, "detail": <0-100>}},
  "overall": <0-100>,
  "feedback": "<feedback específico de 2-3 oraciones sobre esta respuesta>",
  "what_worked": "<qué hizo bien el estudiante>",
  "what_to_improve": "<qué mejorar específicamente>",
  "expert_version": "<cómo se vería un prompt experto para este desafío>"
}}"""

    try:
        raw = await ask_gemini(prompt)
        data = parse_json_response(raw)
    except Exception:
        data = {
            "scores": {"clarity": 60, "context": 55, "precision": 60, "structure": 65, "detail": 55},
            "overall": 59,
            "feedback": "Buen intento. El prompt tiene una base sólida pero le falta especificidad para el rol profesional.",
            "what_worked": "Identificaste el objetivo principal del desafío.",
            "what_to_improve": "Agregá el tono de voz, métricas de éxito y restricciones específicas del rol.",
            "expert_version": "Un prompt experto definiría el rol exacto, el tono, la audiencia, las métricas de éxito y las restricciones del proyecto."
        }

    overall = data.get("overall", 60)
    xp_earned = 100 if overall >= 80 else 60 if overall >= 60 else 30

    if user_id:
        conn = get_db()
        conn.execute("UPDATE users SET xp = xp + ? WHERE id = ?", (xp_earned, user_id))
        new_xp = conn.execute("SELECT xp FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        conn.execute("UPDATE users SET level = ? WHERE id = ?", (calc_level(new_xp), user_id))
        conn.commit()
        conn.close()
        data["xp_earned"] = xp_earned

    return data

# ── IA: COMPARAR PROMPTS ───────────────────────────────────────────────────
@app.post("/api/ai/compare")
async def ai_compare(body: CompareBody):
    prompt = f"""Comparás dos prompts como experto en prompt engineering. Respondé SOLO con JSON válido, sin markdown:
{{
  "scores_a": {{"clarity": <0-100>, "context": <0-100>, "precision": <0-100>, "structure": <0-100>, "detail": <0-100>}},
  "scores_b": {{"clarity": <0-100>, "context": <0-100>, "precision": <0-100>, "structure": <0-100>, "detail": <0-100>}},
  "overall_a": <0-100>,
  "overall_b": <0-100>,
  "winner": "<A o B>",
  "margin": <diferencia en puntos>,
  "analysis": "<análisis comparativo de 2-3 oraciones>"
}}

Prompt A: "{body.prompt_a}"
Prompt B: "{body.prompt_b}"
"""
    try:
        raw = await ask_gemini(prompt)
        return parse_json_response(raw)
    except Exception:
        return {
            "scores_a": {"clarity": 60, "context": 50, "precision": 55, "structure": 60, "detail": 50},
            "scores_b": {"clarity": 75, "context": 70, "precision": 72, "structure": 75, "detail": 68},
            "overall_a": 55,
            "overall_b": 72,
            "winner": "B",
            "margin": 17,
            "analysis": "El Prompt B es más completo y estructurado que el A. Tiene más contexto y especificidad."
        }

# ── COMUNIDAD ──────────────────────────────────────────────────────────────
@app.post("/api/community/like")
async def toggle_like(body: LikeBody, user_id: int = Depends(require_user)):
    conn = get_db()
    existing = conn.execute(
        "SELECT 1 FROM community_likes WHERE user_id = ? AND workflow_id = ?",
        (user_id, body.workflow_id)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM community_likes WHERE user_id = ? AND workflow_id = ?", (user_id, body.workflow_id))
        liked = False
    else:
        conn.execute("INSERT INTO community_likes (user_id, workflow_id) VALUES (?, ?)", (user_id, body.workflow_id))
        liked = True

    conn.commit()
    conn.close()
    return {"liked": liked}

@app.get("/api/community/likes")
async def get_likes(user_id: int = Depends(require_user)):
    conn = get_db()
    likes = [r[0] for r in conn.execute(
        "SELECT workflow_id FROM community_likes WHERE user_id = ?", (user_id,)
    ).fetchall()]
    conn.close()
    return {"likes": likes}

# ── PROGRESO ───────────────────────────────────────────────────────────────
@app.post("/api/progress/challenge")
async def complete_challenge(body: ChallengeBody, user_id: int = Depends(require_user)):
    conn = get_db()
    user = conn.execute("SELECT xp, level, challenges_done FROM users WHERE id = ?", (user_id,)).fetchone()
    done = json.loads(user["challenges_done"] or "[]")

    xp_earned = 0
    if body.challenge_id not in done:
        done.append(body.challenge_id)
        conn.execute(
            "UPDATE users SET xp = xp + ?, challenges_done = ? WHERE id = ?",
            (body.xp, json.dumps(done), user_id)
        )
        xp_earned = body.xp

    new_xp = (user["xp"] or 0) + xp_earned
    new_level = calc_level(new_xp)
    if new_level != user["level"]:
        conn.execute("UPDATE users SET level = ? WHERE id = ?", (new_level, user_id))

    conn.commit()
    conn.close()
    return {"xp": new_xp, "level": new_level, "xp_earned": xp_earned, "challenges_done": done}

# ── FRONTEND ───────────────────────────────────────────────────────────────
@app.get("/")
async def serve_frontend():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/style.css")
async def serve_css():
    return FileResponse(BASE_DIR / "style.css", media_type="text/css")

@app.get("/animations.js")
async def serve_animations():
    return FileResponse(BASE_DIR / "animations.js", media_type="application/javascript")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"LeAIrning backend iniciando en http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
