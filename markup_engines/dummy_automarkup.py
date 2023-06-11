# This is a dummy implementation of the AutoMarkup interface.
#
# Can be used to test the markup metric without having to use a real
# markup engine (e.g., GPT-4).

class AutoMarkup:
    def automarkup(self, input_text: str, prompt: str) -> str:
        title, *rest = input_text.split("\n")
        body = "\n".join(rest)

        return f"<html><title>{title}</title><body>{body}</body></html>"
