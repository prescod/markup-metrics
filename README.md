# Markup Metrics

Markup Metrics is a Testing Tool for comparing implementations
of Automatic Markup (Auto-Markup) tools.

## Installation

```python
pip install -r requirements.txt
```

The two first auto-markup engines use OpenAI, so they need
the `OPENAI_API_KEY` environment variable to be set. You
can run the suite without that, but you won't be actually
testing anything remotely similar to real automarkup.

## Extensibility

If you create an Auto-Markup engine, you just make a driver for 
it that implements the AutoMarkup interface.

Look at the `markup_engines` directory to see how to implement
a new driver.

Actual metrics are also pluggable, so you can compare each
implementation multiple ways.

New data can be added to the `data` directory.

For every schema, you can add a "prompt.txt" and as many test
.txt files as you want. Beside every test .txt file you can
add a .xml file which represents what the output should look
like.

## Usage

```python
python markup-metric.py
```

This runs all metrics against all engines (even two dummy/test engines).

The output looks like this:

```txt
Processing gpt3.5_am1_automarkup with xater_metric
     dita
            data/dita/test1.txt (out/gpt3.5_am1_automarkup/dita/test1/test1.xml): 2.94%
            data/dita/test2.txt (out/gpt3.5_am1_automarkup/dita/test2/test2.xml): 2.94%
            data/dita/test3.txt (out/gpt3.5_am1_automarkup/dita/test3/test3.xml): 3.70%
     Average gpt3.5_am1_automarkup / xater_metric / dita: 3.20%
     html
            data/html/test1.txt (out/gpt3.5_am1_automarkup/html/test1/test1.xml): 4.65%
            data/html/test2.txt (out/gpt3.5_am1_automarkup/html/test2/test2.xml): 20.00%
            data/html/test3.txt (out/gpt3.5_am1_automarkup/html/test3/test3.xml): 16.67%
     Average gpt3.5_am1_automarkup / xater_metric / html: 13.77%
     Average gpt3.5_am1_automarkup / xater_metric: 8.48%
```

`gpt3.5_am1_automarkup` is an automarkup system based on GPT-4 and Prompt Engineering.

`xater_metric` is a metric based on XML tokenization and the industry 
standard Translation Edit Rate metric.

`dita` is a schema under test.

`data/dita/test1.txt` is a test file to be automatically encoded into DITA.
It should have a sibling file `data/dita/test1.xml` which describes ideal
target output.

`out/gpt3.5_am1_automarkup/dita/test1/test1.xml` is an output file.

In that same directory may be other files that the metrics output
to explain their scoring. For example:

`out/gpt3.5_am1_automarkup/dita/test1/test1.xater_metric.txt` is
a difference file which shows how different the output XML was
from the target.

At the end of each line is a score. For all built-in metrics, 0
is a good score and 100 is a bad score. For example, for 
`xater`, zero means zero edits were needed to match the sample file.

## Built-In Metrics

`xater_metric` ("XML Automarkup Translation Error Rate)
is a metric based on XML tokenization and the industry 
standard Translation Edit Rate metric. Zero means zero edits were
needed to match the sample file. 100 means, roughly, "everything
needed to change". It is actually possible for a horrible
TER to be worse than 100%, because the numerator and the denominator
are not counting the same thing.

`validation_error_metric` is a measure of how many errors there are
in the document. Zero means zero errors and 100 means, essentially,
that "everything was wrong."

## Built-In Auto-Markup Engines

`dummy_automarkup.py`: does basically nothing. It returns a hard-coded
HTML string. It can be used for testing.

`gpt3.5_am1_automarkup.py`: a simple prompt-engineering-based markup
system that uses the `gpt-3.5-turbo` API.

`gpt4_am1_automarkup.py`: a simple prompt-engineering-based markup
system that uses the `gpt-4` API.

buggy_automarkup__DISABLED.py: A buggy markup engine that is disabled by default.

This engine can be used to test what happens when a markup engine
fails to produce valid markup.
