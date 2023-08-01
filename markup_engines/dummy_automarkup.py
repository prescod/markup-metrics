from xml.dom import minidom

# This is a dummy implementation of the AutoMarkup interface.
#
# Can be used to test the markup metric without having to use a real
# markup engine (e.g., GPT-4).

class AutoMarkup:
    def automarkup(self, input_text: str, prompt: str) -> str:
        lines = input_text.split("\n")

        doc = minidom.parseString("<!DOCTYPE task PUBLIC '-//OASIS//DTD DITA Task//EN' 'task.dtd'>\n<task></task>")
        root = doc.documentElement
        for line in lines:
            root.appendChild(doc.createElement("xyzzy")).appendChild(doc.createTextNode(line))

        return doc.toprettyxml(indent="  ")
