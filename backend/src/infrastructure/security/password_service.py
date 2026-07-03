from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PasswordEncryptionService:
    """
    AES-256-GCM ile kamera kimlik bilgilerini şifreler/çözer.
    Key 32 bayt (256-bit) olmalıdır; ENCRYPTION_KEY env değişkeninden okunur.
    """

    _ENV_VAR = "CAMERA_ENCRYPTION_KEY"

    def __init__(self, key: bytes | None = None):
        if key is not None:
            self._key = key
        else:
            self._key = self._load_or_generate_key()

    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """Şifreler ve base64 kodlu string döner (nonce + ciphertext)."""
        nonce = os.urandom(12)                            # 96-bit GCM nonce
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, token: str) -> str:
        """base64 token'ı çözer ve düz metni döner."""
        data = base64.b64decode(token.encode("ascii"))
        nonce, ciphertext = data[:12], data[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")

    # ------------------------------------------------------------------

    @classmethod
    def _load_or_generate_key(cls) -> bytes:
        raw = os.environ.get(cls._ENV_VAR)
        if raw:
            key = base64.b64decode(raw)
            if len(key) != 32:
                raise ValueError(f"{cls._ENV_VAR} 32 bayt (256-bit) olmalıdır.")
            return key

        # Geliştirme ortamı için deterministik sabit key (üretimde env değişkeni zorunlu)
        import warnings
        warnings.warn(
            f"{cls._ENV_VAR} env değişkeni ayarlanmamış. "
            "Geliştirme ortamı için varsayılan key kullanılıyor. "
            "Üretimde mutlaka .env dosyasına ekleyin.",
            stacklevel=3,
        )
        return b"\x00" * 32  # 256-bit sıfır key — sadece geliştirme!
