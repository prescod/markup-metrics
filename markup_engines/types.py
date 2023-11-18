from typing import Protocol
    
class MarkupEngine(Protocol):
    _name = None

    @property
    def name(self) -> str:
        return self._name or self.__class__.__name__
    
    @name.setter
    def name_setter(self, value: str) -> None:
        self._name = value


    def automarkup(self, input_text: str, prompt: str) -> str:
        ...

