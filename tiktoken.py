# Dummy tiktoken module to bypass missing dependencies on ARM64
# We only use Tavily for basic searches which don't invoke token counting.

def encoding_for_model(*args, **kwargs):
    class MockEncoding:
        def encode(self, *args, **kwargs):
            return []
    return MockEncoding()

def get_encoding(*args, **kwargs):
    class MockEncoding:
        def encode(self, *args, **kwargs):
            return []
    return MockEncoding()
