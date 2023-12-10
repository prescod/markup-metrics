import xml.sax


class TokenizingSaxHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.tokens = []
        self.chars = []

    def startElement(self, name, attrs):
        self.flush_chars()
        self.tokens.append(f"<{name} ")
        # Sort attributes by key
        for attr_name, attr_value in sorted(attrs.items()):
            if attr_name == "id":
                attr_value = f"ID {len(self.tokens)}"
            self.tokens.append(f'{attr_name}="{attr_value}" ')
        self.tokens.append(">")

    def endElement(self, name):
        # Process characters buffer as text
        self.flush_chars()
        self.tokens.append(f"</{name}>")

    def characters(self, content):
        # Buffer characters for later processing
        self.chars.append(content)

    def flush_chars(self):
        # Process characters buffer as text
        if self.chars:
            text = " ".join(c for c in self.chars)
            text = " ".join(text.split()).strip()
            if text:
                self.tokens.append(text)
        self.chars = []


class Tokenizer:
    def tokenize(self, xml_string):
        handler = TokenizingSaxHandler()
        xml.sax.parseString(xml_string, handler)
        return handler.tokens


if __name__ == "__main__":
    # Test XML
    xml_string = """
    <note date="8/31/12" to="Tove">
        <to>Tove</to>
        <from>Jani</from>
        <heading type="Reminder" priority="high">Don't forget me this weekend!</heading>
        <body>Dear Tove, wish you have a nice weekend!</body>
    </note>
    """

    # Run the parser
    tokens = Tokenizer().tokenize(xml_string)

    # Output the tokens
    for token in tokens:
        print(token)
