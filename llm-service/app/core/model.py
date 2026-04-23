import os
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_DIR = os.getenv("MODEL_DIR", "/models/qwen35_9b_hrmatch_merged")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Загрузка слитой модели из {MODEL_DIR} ...")


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


system_prompt = (
    "Ты — интеллектуальная система оценки соответствия кандидатов. "
    "Отвечай строго на русском языке.\n"
    "Твоя задача — анализировать вакансию и резюме кандидата, выдавая числовую оценку от 0 до 1 "
    "(где 1 — полное соответствие требованиям) и короткое, но информативное объяснение.\n"
    "Формат ответа:\n"
    "1) Первая строка строго вида: 'Оценка: X.XX' (X.XX — число от 0 до 1 с двумя знаками после запятой).\n"
    "2) Далее 3–6 коротких буллетов с обоснованием по навыкам, опыту и содержанию резюме.\n"
    "Не описывай свой ход рассуждений, не используй заголовки вроде 'Thinking process', "
    "'Reasoning' или 'Chain of thought'. Отвечай только в указанном формате."
)


def build_messages(vacancy_text: str, resume_text: str):
    user_content = (
        "Оцени, насколько хорошо кандидат подходит под данную вакансию. "
        "Верни числовую оценку от 0 до 1 (1 — полное соответствие, 0 — полное несоответствие) "
        "и краткое объяснение, почему ты выбрал именно такую оценку.\n\n"
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


@torch.inference_mode()
def infer(vacancy_text: str, resume_text: str) -> str:
    messages = build_messages(vacancy_text, resume_text)

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
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