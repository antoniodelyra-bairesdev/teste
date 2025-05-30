import base64


class Base64EncoderDecoder:
    @staticmethod
    def encode(string: str) -> str:
        encoded_bytes = base64.b64encode(string.encode("utf-8"))
        return encoded_bytes.decode("utf-8")

    @staticmethod
    def decode(encoded_string: str) -> str:
        decoded_bytes = base64.b64decode(encoded_string.encode("utf-8"))
        return decoded_bytes.decode("utf-8")
