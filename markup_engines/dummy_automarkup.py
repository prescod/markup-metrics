class AutoMarkup:
    def automarkup(self, input_text: str, prompt: str) -> str:
        title, *rest = input_text.split("\n")
        body = "\n".join(rest)

        return f"<html><title>{title}</title><body>{body}</body></html>"
