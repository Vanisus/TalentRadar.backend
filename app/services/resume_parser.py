from pathlib import Path
import docx
import PyPDF2


def parse_resume(file_path: str) -> str:
    """
    Извлекает текст из резюме (docx или pdf)
    """
    file_path_obj = Path(file_path)
    file_ext = file_path_obj.suffix.lower()

    if file_ext == ".docx":
        return _parse_docx(file_path)
    elif file_ext == ".pdf":
        return _parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")


def _parse_docx(file_path: str) -> str:
    """Извлечение текста из .docx файла"""
    doc = docx.Document(file_path)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text


def _parse_pdf(file_path: str) -> str:
    """Извлечение текста из .pdf файла"""
    text = ""
    with open(file_path, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text
