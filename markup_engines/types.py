from typing import Protocol
    
class MarkupEngine(Protocol):
    def automarkup(self, input_text: str, prompt: str) -> str:
        ...

