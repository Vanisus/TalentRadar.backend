from typing import Optional

from pydantic import BaseModel


class CertificateUploadResponse(BaseModel):
    id: int
    title: str
    file_path: str
