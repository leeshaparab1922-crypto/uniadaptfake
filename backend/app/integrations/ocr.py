"""Tesseract 5 OCR adapter via pytesseract (ADR-0013): English only, one page at
a time, pinned config. The engine version and config are returned so each OCR
stage record can trace its result."""

from __future__ import annotations

import io

from app.core.config import settings
from app.services.ingestion.ports import OcrResult


class TesseractOcrEngine:
    def __init__(self, *, language: str | None = None, config: str | None = None) -> None:
        self._language = language or settings.ocr_language
        self._config = config or settings.ocr_tesseract_config
        self._version: str | None = None

    def _engine_version(self) -> str:
        import pytesseract

        if self._version is None:
            self._version = str(pytesseract.get_tesseract_version())
        return self._version

    def ocr_png(self, png_bytes: bytes) -> OcrResult:
        import pytesseract
        from PIL import Image

        with Image.open(io.BytesIO(png_bytes)) as image:
            data = pytesseract.image_to_data(
                image, lang=self._language, config=self._config, output_type=pytesseract.Output.DICT
            )
        words: list[str] = []
        confidences: list[float] = []
        lines: dict[tuple[int, int, int], list[str]] = {}
        for i, word in enumerate(data["text"]):
            word = (word or "").strip()
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                conf = -1.0
            if not word or conf < 0:
                continue
            words.append(word)
            confidences.append(conf)
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(key, []).append(word)
        text = "\n".join(" ".join(parts) for _, parts in sorted(lines.items()))
        mean = sum(confidences) / len(confidences) if confidences else 0.0
        return OcrResult(
            text=text,
            mean_confidence=mean,
            engine_version=self._engine_version(),
            config=f"lang={self._language} {self._config}",
        )

    def is_blank(self, png_bytes: bytes, ink_ratio_threshold: float) -> bool:
        from PIL import Image

        with Image.open(io.BytesIO(png_bytes)) as image:
            gray = image.convert("L")
            hist = gray.histogram()
        total = sum(hist)
        if total == 0:
            return True
        dark = sum(hist[:200])  # pixels clearly darker than white
        return (dark / total) < ink_ratio_threshold
