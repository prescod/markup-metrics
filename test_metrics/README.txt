This folder has files that test the extremes of
metric engines.

If an engine gives high marks to the examples other than "identical.xml",
something is not correct about that metric.

Such as:

**/*.empty.xml - what if the root XML element produced is empty?
**/*.identical.xml - what if it is exactly right?
**/*.nomarkup.xml - what if there is no markup, just PCDATA?
**/*.notext.xml - what if there is no text, just (correct) markup? 
**/*.textchanged.xml - what if the text was incorrectly mutated?
