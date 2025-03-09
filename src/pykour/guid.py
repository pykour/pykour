from nanoid import generate

GUID_TOKENS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
GUID_SIZE = 24


class GUID:
    @staticmethod
    def generate() -> str:
        return generate(alphabet=GUID_TOKENS, size=GUID_SIZE)
