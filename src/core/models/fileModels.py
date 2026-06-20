from pydantic import BaseModel, Field
from typing import TypedDict


class FileModel(BaseModel):
    id: str = Field(..., description="ID of the file")
    name: str = Field(..., description="Name of the file")
    mime_type: str = Field(..., description="MIME type of the file")
    size: str = Field(..., description="Formatted size of the file (e.g., '2 MB')")
    web_content_link: str = Field(..., description="Web content link of the file")
    web_view_link: str = Field(..., description="Web view link of the file")
    file_type: str = Field(
        ..., description="Type of the file (e.g., 'image' or 'video')"
    )


class DownloadedFileModel(BaseModel):
    name: str = Field(..., description="Name of the file")
    size: str = Field(..., description="Formatted size of the file (e.g., '2 MB')")
    content: bytes = Field(..., description="Content of the file in bytes")


class FetchedModel(BaseModel):
    data: FileModel = Field(..., description="The fetched file data")
    children: list["FetchedModel"] = Field(
        default_factory=list,
        description="List of child files (if the file is a folder)",
    )
