import os
import json
import hashlib
from pathlib import Path
import guidance


class AutoMarkup:
    message = """
    {{#system~}}
    You are an expert at adding XML markup to text documents.
    {{~/system}}

    {{#user~}}
    {{prompt}}

    The text:
    {{input}}
    {{~/user}}

    {{#assistant~}}
    {{gen 'markup' temperature=0 max_tokens=3500}}
    {{~/assistant}}
    """
    model = "gpt-4"

    def __init__(self):
        self.llm = guidance.llms.OpenAI(self.model)
        self.endpoint = guidance(self.message, llm=self.llm)  # type: ignore


    # note that guidance does caching, so I don't need to
    def automarkup(self, input_text: str, prompt: str) -> str:
        # Perform the automarkup
        out = self.endpoint(input=input_text, prompt=prompt)
        markup = out["markup"]
        doctype_loc = markup.find("<!DOCTYPE")
        if doctype_loc == -1:
            raise ValueError("No DOCTYPE found")
        else:
            markup = markup[doctype_loc:]
        
        return markup.strip().strip("`")
