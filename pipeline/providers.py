import base64
import fitz
import io
from typing import Any

SUPPORTED_PROVIDERS = {
    "gemini": {
        "embedding_model": "models/gemini-embedding-2",
        "llm_model": "models/gemini-2.5-flash",
        "env_key": "GEMINI_API_KEY",
    },
    "openai": {
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "openrouter": {
        "embedding_model": None,
        "llm_model": "openrouter/free",
        "env_key": "OPENROUTER_API_KEY",
    },
}


def _text_to_pdf_bytes(text: str, title: str = "Evidencia") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(50, 50), title, fontsize=14, fontname="helv")
    y = 90
    for line in text.split("\n"):
        for chunk in [line[i:i+90] for i in range(0, len(line), 90)]:
            if y > 780:
                page = doc.new_page()
                y = 50
            page.insert_text(fitz.Point(50, y), chunk, fontsize=9, fontname="helv")
            y += 14
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def get_embeddings(
    texts: list[str],
    provider: str,
    api_key: str,
    model: str | None = None,
) -> list[list[float]]:
    if provider == "gemini":
        from google import genai
        client = genai.Client(api_key=api_key)
        m = model or SUPPORTED_PROVIDERS["gemini"]["embedding_model"]
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), 20):
            batch = texts[i:i+20]
            result = client.models.embed_content(model=m, contents=batch)
            batch_embeds = [e.values for e in result.embeddings]
            # Pad if API returns fewer embeddings than requested
            if len(batch_embeds) < len(batch):
                import logging
                logging.warning(
                    f"Embedding API devolvió {len(batch_embeds)}/{len(batch)} embeddings en lote {i//20+1}"
                )
                batch_embeds.extend([[]] * (len(batch) - len(batch_embeds)))
            all_embeddings.extend(batch_embeds)
        return all_embeddings

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        m = model or SUPPORTED_PROVIDERS["openai"]["embedding_model"]
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), 20):
            batch = texts[i:i+20]
            resp = client.embeddings.create(input=batch, model=m)
            batch_embeds = [d.embedding for d in resp.data]
            if len(batch_embeds) < len(batch):
                import logging
                logging.warning(
                    f"Embedding API devolvió {len(batch_embeds)}/{len(batch)} embeddings en lote {i//20+1}"
                )
                batch_embeds.extend([[]] * (len(batch) - len(batch_embeds)))
            all_embeddings.extend(batch_embeds)
        return all_embeddings

    elif provider == "openrouter":
        raise ValueError(
            "OpenRouter no soporta embeddings. Usa Gemini (GEMINI_API_KEY) u OpenAI (OPENAI_API_KEY) para C4."
        )

    else:
        raise ValueError(f"Provider no soportado: {provider}")


def evaluate_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str,
    api_key: str,
    model: str | None = None,
    evidence_texts: list[str] | None = None,
) -> str:
    if provider == "gemini":
        from google import genai
        from google.genai import types as gtypes
        client = genai.Client(api_key=api_key)
        m = model or SUPPORTED_PROVIDERS["gemini"]["llm_model"]

        contents = []
        if evidence_texts:
            for ev_text in evidence_texts:
                pdf_bytes = _text_to_pdf_bytes(ev_text)
                contents.append(gtypes.Part.from_bytes(
                    data=pdf_bytes, mime_type="application/pdf"
                ))
        contents.append(gtypes.Part.from_text(text=user_prompt))

        try:
            resp = client.models.generate_content(
                model=m,
                contents=contents,
                config=gtypes.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )
            return resp.text or ""
        except Exception as e:
            return f"__LLM_ERROR__{e}"

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        m = model or SUPPORTED_PROVIDERS["openai"]["llm_model"]
        try:
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            if evidence_texts:
                content_parts = [{"type": "text", "text": user_prompt}]
                for ev_text in evidence_texts:
                    pdf_bytes = _text_to_pdf_bytes(ev_text)
                    try:
                        file = client.files.create(
                            file=("evidence.pdf", pdf_bytes, "application/pdf"),
                            purpose="assistants",
                        )
                        content_parts.append({
                            "type": "file",
                            "file": {"file_id": file.id, "filename": "evidence.pdf"},
                        })
                    except Exception:
                        content_parts.append({"type": "text", "text": ev_text})
                messages.append({"role": "user", "content": content_parts})
            else:
                messages.append({"role": "user", "content": user_prompt})

            resp = client.chat.completions.create(
                model=m,
                messages=messages,
                max_tokens=4096,
                temperature=0.1,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"__LLM_ERROR__{e}"

    elif provider == "openrouter":
        from openai import OpenAI
        m = model or SUPPORTED_PROVIDERS["openrouter"]["llm_model"]
        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        try:
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            if evidence_texts:
                content_parts = [{"type": "text", "text": user_prompt}]
                for ev_text in evidence_texts:
                    pdf_bytes = _text_to_pdf_bytes(ev_text)
                    try:
                        content_parts.append({
                            "type": "file",
                            "file": {
                                "file_data": f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode()}",
                                "filename": "evidence.pdf",
                            },
                        })
                    except Exception:
                        content_parts.append({"type": "text", "text": ev_text})
                messages.append({"role": "user", "content": content_parts})
            else:
                messages.append({"role": "user", "content": user_prompt})

            resp = client.chat.completions.create(
                model=m,
                messages=messages,
                max_tokens=4096,
                temperature=0.1,
                extra_headers={
                    "HTTP-Referer": "https://github.com/opencode-ia",
                    "X-Title": "Evaluador IAA",
                },
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"__LLM_ERROR__{e}"

    else:
        raise ValueError(f"Provider no soportado: {provider}")
