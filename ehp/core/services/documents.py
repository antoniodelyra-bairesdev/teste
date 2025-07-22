# pyright: reportMissingTypeStubs=false, reportImplicitAbstractClass=false

from abc import abstractmethod
from io import BytesIO
from typing import Any, BinaryIO, cast
from bs4.element import NavigableString
from fastapi import HTTPException, status
from odfdo.container import is_zipfile
import orjson
from sqlalchemy import exc
from typing_extensions import override
from autoregistry import Registry
import pypdf
import pypdf.errors
import docx2txt
import odfdo
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from ehp.core.models.schema.wikiclip import WikiClipSchema
from ehp.utils.base import log_error


def binio_to_bytes(binio: BinaryIO) -> bytes:
    """Convert a BinaryIO stream to bytes."""
    if isinstance(binio, BytesIO):
        return binio.getvalue()
    return binio.read()


def as_bytesio(data: bytes) -> BytesIO:
    """Convert bytes to a BytesIO stream."""
    return BytesIO(data)


# Create a registry for document extractors
# This registry will automatically register classes that end with "Extractor"
# and are subclasses of the Extractor base class.
# The registry can be used to dynamically load and use different document extractors.
# The class name must be <Extension>Extractor, where <Extension> is the file extension
# (e.g., PDFExtractor for .pdf files).
class DocumentExtractor(Registry, suffix="Extractor"):
    @abstractmethod
    def extract(self, reader: BinaryIO, filename: str) -> WikiClipSchema:
        """Extract text from a document using the appropriate extractor."""
        ...

    @classmethod
    def get_extractor(cls, key: str) -> "DocumentExtractor":
        """Get the extractor instance."""
        return cast(DocumentExtractor, cls[key]())


class PDFExtractor(DocumentExtractor):
    """Extractor for PDF documents using the library `pymupdf`."""

    @override
    def extract(self, reader: BinaryIO, filename: str) -> WikiClipSchema:
        """Extract text from a PDF document."""
        try:
            pdf_reader = pypdf.PdfReader(reader)

            text = "".join(
                # Page has the get_text method, the package is just poorly typed
                page.extract_text()
                for page in pdf_reader.pages
            ).strip()

            return WikiClipSchema.model_construct(
                content=text,
                title=filename,
                url=None,  # URL is not applicable for local files
                related_links=None,  # No related links for local files
            )
        except pypdf.errors.PyPdfError as e:
            log_error(f"Error reading PDF document: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid PDF format",
            ) from e


class TXTExtractor(DocumentExtractor):
    """Extractor for TXT documents using builtin reader API.
    Assumes the text is plain text without any formatting and
    encoded with UTF-8."""

    @override
    def extract(self, reader: BinaryIO, filename: str) -> WikiClipSchema:
        """Extract text from a TXT document."""
        text = reader.read().decode("utf-8", errors="ignore")
        return WikiClipSchema.model_construct(
            content=text,
            title=filename,
            url=None,  # URL is not applicable for local files
            related_links=None,  # No related links for local files
        )


class DOCXExtractor(DocumentExtractor):
    """Extractor for DOCX documents using the library `docx2txt`."""

    @override
    def extract(self, reader: BinaryIO, filename: str) -> WikiClipSchema:
        """Extract text from a DOCX document."""
        try:
            text = docx2txt.process(reader)
            if not text.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Empty DOCX content",
                )
            return WikiClipSchema.model_construct(
                content=text,
                title=filename,
                url=None,  # URL is not applicable for local files
                related_links=None,  # No related links for local files
            )
        except Exception as e:
            log_error(f"Error reading DOCX document: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid DOCX format",
            ) from e


class ODTExtractor(DocumentExtractor):
    """Extractor for ODT documents using the library `odfdo`."""

    @override
    def extract(self, reader: BinaryIO, filename: str) -> WikiClipSchema:
        """Extract text from an ODT document."""
        content = as_bytesio(binio_to_bytes(reader))
        # Valid ODT files should be zip files, so we check if the content is a valid zip file
        if not is_zipfile(content):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid ODT format",
            )
        try:
            doc = odfdo.Document(content)
        except Exception as e:
            log_error(f"Error reading ODT document: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid ODT format",
            ) from e
        text = doc.get_formatted_text().strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Empty ODT content",
            )
        return WikiClipSchema.model_construct(
            content=text,
            title=filename,
            url=None,  # URL is not applicable for local files
            related_links=None,  # No related links for local files
        )


class MappingExtractor(DocumentExtractor):
    """Extractor for formats that behave like maps, such as JSON or XML or HTML."""

    @abstractmethod
    def extract_map(self, reader: BinaryIO) -> dict[str, str]:
        """Extract text from a Map document."""
        ...

    def important_keys(self) -> set[str]:
        """Return a list of important keys to extract from the map. If no keys are defined, extract all."""
        return set()

    @override
    def extract(self, reader: BinaryIO, filename: str) -> WikiClipSchema:
        """Extract text from a Map document."""
        mapping = self.extract_map(reader)
        if mapping is None:  # pyright: ignore[reportUnnecessaryComparison]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Empty map content",
            )
        if not isinstance(mapping, dict):
            # If the map is not a dictionary, we convert it to one
            # as fallback

            # TODO: consider how to handle this case better
            mapping = {"fileContents": orjson.dumps(mapping).decode("utf-8")}
        text = self.extract_text_from_map(mapping)
        return WikiClipSchema.model_construct(
            content=text,
            title=filename,
            url=None,  # URL is not applicable for local files
            related_links=None,  # No related links for local files
        )

    def extract_text_from_map(self, map: dict[str, Any]) -> str:
        """Extract text from a map. If no keys are defined, extract all."""
        important_keys = self.important_keys()
        content = ""
        for key, value in map.items():
            if key in important_keys or not important_keys:
                content += f"{key}: {value}\n"
        return content.strip()


class JSONExtractor(MappingExtractor):
    """Extractor for JSON documents."""

    @override
    def extract_map(self, reader: BinaryIO) -> dict[str, str]:
        try:
            content = orjson.loads(reader.read())
            return (
                {k: str(v) for k, v in content.items()}
                if isinstance(content, dict)
                else content
            )
        except Exception as e:
            log_error(f"Error extracting JSON: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON format",
            ) from e


class XMLExtractor(MappingExtractor):
    """Extractor for XML documents."""

    @override
    def extract_map(self, reader: BinaryIO) -> dict[str, str]:
        try:
            # Parse the XML content
            tree = ET.parse(reader)
            root = tree.getroot()
            # TODO: implement more sophisticated xml to map conversion to support properly nested structures
            # For now, we just return a flat map of tag names to text content
            return {
                elem.tag: elem.text.strip()
                for elem in root.iter()
                if elem.text is not None
            }
        except ET.ParseError as e:
            log_error(f"Error parsing XML: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid XML format",
            ) from e


class HTMLExtractor(MappingExtractor):
    """Extractor for HTML documents."""

    @override
    def extract_map(self, reader: BinaryIO) -> dict[str, str]:
        # TODO: implement more sophisticated html to map conversion to support properly nested structures
        # For now, we just return a flat map of tag names to text content
        soup = BeautifulSoup(reader.read(), "html.parser")
        result = {}
        for tag in soup.find_all():
            name = getattr(tag, "name", None)
            if not name:
                continue  # Skip tags without a name
            text = "".join(  # doing this to ensure we only get content that belongs only to the tag
                # and not any nested tags, which is what we want for a map-like structure
                item
                for item in (tag.contents)
                if isinstance(item, NavigableString) and item.strip()
            )
            result[name] = text
        if not result:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid HTML format",
            )
        return result
