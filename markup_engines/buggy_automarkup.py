template = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
   "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
    <title>{title}</title>
    <body>
    <p>{body}</p>
    <blah></blah>
    </body>
</html>
"""

class AutoMarkup:
    def automarkup(self, input_text: str, prompt: str) -> str:
        title, *rest = input_text.split("\n")
        body = "\n".join(rest)

        return template.format(title=title, body=body)
