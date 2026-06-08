from pathlib import Path
from fastapi import UploadFile


class FileHandler:
    class Storage:
        UPLOAD_DIR = (
            Path(__file__).resolve().parent.parent.parent.parent.joinpath("uploads")
        )
        VECTOR_DIR = (
            Path(__file__)
            .resolve()
            .parent.parent.joinpath("infrastructure")
            .joinpath("vectorDB")
            .joinpath("vectors")
        )

    allowed_extensions = {
        ".wav",
        ".mp3",
        ".flac",
        ".m4a",
        ".ogg",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
    }

    @staticmethod
    def _read_file_signature(file: UploadFile, size: int = 2048) -> bytes:
        stream = file.file
        original_position = None

        try:
            original_position = stream.tell()
        except Exception:
            original_position = None

        try:
            if original_position is not None:
                stream.seek(0)
            content = stream.read(size)
            return content if isinstance(content, bytes) else b""
        finally:
            if original_position is not None:
                stream.seek(original_position)

    @classmethod
    def _get_file_extension_from_name(cls, file: UploadFile) -> str | None:
        extension = Path(file.filename or "").suffix.lower().strip()
        if extension in cls.allowed_extensions:
            return extension
        return None

    @staticmethod
    def _get_file_extension_from_binary(file_content: bytes) -> str:
        """
        Determines file extension from raw bytes.
        Pass file.file.read(2048) to this function.
        """
        # --- IMAGES ---
        if file_content.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if file_content.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if file_content.startswith(b"GIF87a") or file_content.startswith(b"GIF89a"):
            return ".gif"
        if file_content.startswith(b"RIFF") and file_content[8:12] == b"WEBP":
            return ".webp"

        # --- AUDIO ---
        # WAV: RIFF header + WAVE chunk
        if file_content.startswith(b"RIFF") and file_content[8:12] == b"WAVE":
            return ".wav"

        # FLAC: fLaC header
        if file_content.startswith(b"fLaC"):
            return ".flac"

        # MP3: ID3 tag or Sync Frame (0xFFE / 0xFFF)
        if file_content.startswith(b"ID3") or (
            len(file_content) > 1
            and file_content[0] == 0xFF
            and (file_content[1] & 0xE0) == 0xE0
        ):
            return ".mp3"

        # M4A / MP4 / MOV: Look for 'ftyp' starting at byte 4
        # Format: [4 bytes size][4 bytes 'ftyp'][4 bytes major brand]
        if len(file_content) > 12 and file_content[4:8] == b"ftyp":
            brand = file_content[8:12]
            if brand in [b"M4A ", b"M4B ", b"M4P "]:
                return ".m4a"
            if brand in [b"mp41", b"mp42", b"isom", b"iso2"]:
                # Often m4a files are labeled as mp4/isom
                return ".m4a"
            if brand == b"qt  ":
                return ".mov"

        # OGG: OggS header
        if file_content.startswith(b"OggS"):
            return ".ogg"

        raise ValueError("Unsupported file type or corrupt header")

    @classmethod
    def get_file_extension(cls, file: UploadFile) -> str:
        content_type = (file.headers.get("content-type") or "").lower().strip()
        if content_type.startswith("image/jpeg") or content_type.startswith(
            "image/pjpeg"
        ):
            return ".jpg"
        if content_type.startswith("image/jpg"):
            return ".jpg"
        if content_type.startswith("image/png"):
            return ".png"
        if content_type.startswith("image/gif"):
            return ".gif"
        if content_type.startswith("image/webp"):
            return ".webp"
        if content_type.startswith("audio/wav") or content_type.startswith(
            "audio/x-wav"
        ):
            return ".wav"
        if content_type.startswith("audio/flac"):
            return ".flac"
        if content_type.startswith("audio/mpeg"):
            return ".mp3"
        if content_type.startswith("audio/mp4"):
            return ".m4a"
        if content_type.startswith("audio/ogg"):
            return ".ogg"

        extension = cls._get_file_extension_from_name(file)
        if extension:
            return extension

        signature = cls._read_file_signature(file, 2048)
        if not signature:
            raise ValueError("Empty file")

        return cls._get_file_extension_from_binary(signature)

    @staticmethod
    def generate_file_path(file_name: str) -> Path:
        path = Path(FileHandler.Storage.UPLOAD_DIR).joinpath(file_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def retrieve_file_path(cls, relative_path: str) -> Path:
        if not relative_path:
            raise FileNotFoundError("File does not exist")

        path = Path(str(relative_path).strip())

        if path.is_absolute() and path.exists():
            return path

        normalized_path = str(relative_path).strip().replace("\\", "/")

        if "/uploads/" in normalized_path:
            normalized_path = normalized_path.split("/uploads/", 1)[1]
        elif normalized_path.startswith("uploads/"):
            normalized_path = normalized_path[len("uploads/") :]
        elif normalized_path.startswith("/uploads/"):
            normalized_path = normalized_path[len("/uploads/") :]

        path = cls.Storage.UPLOAD_DIR.joinpath(Path(normalized_path.lstrip("/")))
        if not path.exists():
            raise FileNotFoundError("File does not exist")
        return path
