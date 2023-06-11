from markup_engines import gpt4_automarkup

class AutoMarkup(gpt4_automarkup.AutoMarkup):
    model = "gpt-3.5-turbo"