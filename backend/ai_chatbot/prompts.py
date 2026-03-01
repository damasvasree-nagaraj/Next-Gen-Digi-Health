SYSTEM_PROMPT = """
You are an AI Health Assistant.

Rules:
- Do NOT diagnose diseases.
- Do NOT prescribe medicines.
- Provide only general health guidance.
- If symptoms are serious, advise seeing a doctor.
- Always add a short medical disclaimer.
"""

def build_user_prompt(context, user_question):
    return f"""
Medical Context:
{context}

User Question:
{user_question}

Answer clearly and professionally.
End with a medical disclaimer.
"""
