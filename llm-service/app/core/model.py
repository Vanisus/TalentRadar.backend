import os
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_DIR = os.getenv("MODEL_DIR", "/models/qwen35_9b_hrmatch_merged")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Загрузка слитой модели из {MODEL_DIR} ...", flush=True)

if not os.path.isdir(MODEL_DIR):
    raise FileNotFoundError(f"Папка модели не найдена: {MODEL_DIR}")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR,
    use_fast=True,
    local_files_only=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32,
    local_files_only=True,
).to(DEVICE)

print(f"Модель загружена на {DEVICE}", flush=True)

# ─── Промпты для оценки ─────────────────────────────────────────────────

system_prompt = (
    "Ты — строгий HR-аналитик. Оценивай соответствие кандидата вакансии строго и честно. "
    "Отвечай строго на русском языке.\n\n"
    "Правила вычисления оценки (0.00 — 0.99):\n"
    "1. Начинай с 0.50 (базовый балл).\n"
    "2. За каждое выполненное обязательное требование (must-have): +0.05.\n"
    "3. За каждое ОТСУТСТВУЮЩЕЕ обязательное требование: − 0.07.\n"
    "4. За каждый выполненный пункт 'будет плюсом' (nice-to-have): +0.03 (максимум +0.09 за все nice-to-have).\n"
    "5. Если вакансия требует Senior или Lead, а опыт кандидата меньше 3 лет: − 0.12.\n"
    "6. Если отсутствует опыт в требуемом домене (финтех, медтех, банкинг, госсектор, Big Data, mission-critical системы): − 0.10.\n"
    "7. Максимальная итоговая оценка — 0.99. Если считаешь что 1.00, выставляй 0.97.\n\n"
    "Важно: несколько недостатков = низкая оценка. "
    "Не завышай оценку по причине потенциала или хороших знаний основ — оценивай на основе фактического соответствия.\n\n"
    "Формат ответа:\n"
    "1) Первая строка строго вида: 'Оценка: X.XX' (число от 0 до 1 с двумя знаками после запятой).\n"
    "2) Далее 3–6 коротких буллетов: положительные и отрицательные (честно, конкретно, без лишнего оптимизма).\n"
    "Не описывай ход рассуждений, не используй заголовки 'Thinking process', 'Reasoning' или 'Chain of thought'. "
    "Отвечай только в указанном формате."
)


def build_messages(vacancy_text: str, resume_text: str):
    user_content = (
        "Оцени, насколько хорошо кандидат подходит под данную вакансию. "
        "Следуй правилам оценки из системного сообщения. "
        "Верни числовую оценку от 0 до 1 и краткое объективное объяснение.\n\n"
        f"Вакансия:\n{vacancy_text}\n\n"
        f"Резюме кандидата:\n{resume_text}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def postprocess(text: str) -> str:
    idx = text.find("Оценка:")
    if idx != -1:
        text = text[idx:]
    text = text.strip()
    patterns = [
        r"(?is)\nthinking process[:\s].*",
        r"(?is)\nchain of thought[:\s].*",
        r"(?is)\nreasoning[:\s].*",
    ]
    for p in patterns:
        text = re.sub(p, "", text).strip()
    return text


# ─── Промпты для парсинга ───────────────────────────────────────────────

PARSE_SYSTEM_PROMPT = (
    "Ты — система парсинга резюме. "
    "Извлекай структурированную информацию из текста резюме. "
    "Отвечай строго в формате JSON без markdown, без пояснений, без лишнего текста. "
    "Не используй блок <think>. Верни ТОЛЬКО JSON."
)

PARSE_USER_TEMPLATE = (
    "Извлеки структурированные данные из следующего резюме и верни JSON:\n\n"
    "{resume_text}\n\n"
    "Структура JSON:\n"
    "{{\n"
    "  \"full_name\": \"...\",\n"
    "  \"desired_position\": \"...\",\n"
    "  \"city\": \"...\",\n"
    "  \"phone\": \"...\",\n"
    "  \"email\": \"...\",\n"
    "  \"about_me\": \"...\",\n"
    "  \"skills\": [\"\u043dавык1\", \"\u043dавык2\"],\n"
    "  \"experiences\": [\n"
    "    {{\"company\": \"...\", \"position\": \"...\", \"start_date\": \"YYYY-MM-DD\",\n"
    "      \"end_date\": \"YYYY-MM-DD или null\", \"is_current\": false, \"description\": \"...\"}}\n"
    "  ],\n"
    "  \"educations\": [\n"
    "    {{\"institution\": \"...\", \"degree\": \"...\", \"field_of_study\": \"...\",\n"
    "      \"start_year\": 2018, \"end_year\": 2022}}\n"
    "  ],\n"
    "  \"certificates\": [\n"
    "    {{\"title\": \"...\", \"issuer\": \"...\", \"issue_date\": \"YYYY-MM-DD или null\"}}\n"
    "  ]\n"
    "}}\n"
    "Верни ТОЛЬКО JSON."
)


def _strip_think(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"(?is)^(thinking process|думаю|размышление)[:\s\n].*?(\{)", r"\2", text)
    if "{" in text and not text.strip().startswith("{"):
        text = text[text.index("{"):]
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip()


# ─── Инференс ────────────────────────────────────────────────────────────────────

@torch.inference_mode()
def infer(vacancy_text: str, resume_text: str) -> str:
    messages = build_messages(vacancy_text, resume_text)
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    output = model.generate(
        **inputs,
        max_new_tokens=1024,
        do_sample=True,
        temperature=0.2,
        top_p=0.9,
        repetition_penalty=1.05,
    )
    gen_ids = output[0, inputs.input_ids.shape[1]:]
    raw = tokenizer.decode(gen_ids, skip_special_tokens=True)
    return postprocess(raw)


@torch.inference_mode()
def infer_parse(resume_text: str) -> str:
    messages = [
        {"role": "system", "content": PARSE_SYSTEM_PROMPT},
        {"role": "user", "content": PARSE_USER_TEMPLATE.format(resume_text=resume_text)},
    ]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    output = model.generate(
        **inputs,
        max_new_tokens=2048,
        do_sample=False,
        repetition_penalty=1.05,
    )
    gen_ids = output[0, inputs.input_ids.shape[1]:]
    raw = tokenizer.decode(gen_ids, skip_special_tokens=True)
    raw = _strip_think(raw)
    print(f"[infer_parse] raw[:600]: {raw[:600]}", flush=True)
    return raw
