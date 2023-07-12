from pathlib import Path
from lxml import etree
from io import BytesIO, StringIO
from typing import List

from metrics.types import MetricInput

class MetricEngine:
    """A metric which validates the DTD validity of the hypothesis XML.
    
    A score of 0 means the XML is well-formed and there are no DTD errors.
    The first DTD error drops the perfect score to 0.2.
    The first well-formedness error drops the perfect score to 0.5.
    The score between 1 error and 100% errors is linear, based on the percent of correct tags.
    """

    unit = "%"
    
    def calculate(self, input: MetricInput, output_file_dir: Path) -> float:
        hypothesis_xml = input.hypothesis_text
        perfect_score = 0

        # First, check if the XML is well-formed without DTD validation
        well_formed_parser = etree.XMLParser(recover=True)
        well_formed_tree = etree.parse(BytesIO(hypothesis_xml.encode()), well_formed_parser)
        
        # Count the number of well-formedness errors
        num_wf_errors = len(well_formed_parser.error_log)
        
        # Count the number of elements in the XML
        total_elements = sum(1 for _ in well_formed_tree.iter())
        
        # If there are well-formedness errors, the perfect score is 0.5

        if num_wf_errors > 0:
            errors = list(map(str, well_formed_parser.error_log))
            output_file_path = output_file_dir / "well_formedness_errors.txt"
            
            output_file_path.write_text("\n".join( errors))
            perfect_score = 0.5

        # Check for DTD in the hypothesis
        has_dtd = '<!DOCTYPE' in hypothesis_xml

        # Perform DTD validation only if DTD is present
        if has_dtd:
            dtd_parser = etree.XMLParser(dtd_validation=True, load_dtd=True, recover=True, resolve_entities=True)
            tree = etree.parse(BytesIO(hypothesis_xml.encode()), dtd_parser)
            # Get the number of DTD errors
            num_dtd_errors = len(dtd_parser.error_log)

            # If there are DTD errors, the perfect score is 0.2
            if num_dtd_errors > 0:
                perfect_score = min(perfect_score, 0.2)
                errors = list(map(str, dtd_parser.error_log))
                output_file_path = output_file_dir / "dtd_errors.txt"
                output_file_path.write_text("\n".join(["DTD errors: "] + errors ))
        else:
            num_dtd_errors = 0
        

        # Calculate the score linearly based on the percent of correct tags
        total_errors = max(num_wf_errors, num_dtd_errors)

        wrong_tags_ratio = total_errors / total_elements
        score = (1 - perfect_score) * wrong_tags_ratio
        return score * 100

# Test code
if __name__ == "__main__":
    # Instantiate the MetricEngine class
    metric_engine = MetricEngine()
    
    # Test 1: Well-formed XML with no DTD errors
    well_formed_xml = ['<root>', '<child>content</child>', '</root>']
    print(metric_engine.calculate(well_formed_xml, []))  # Should output 0
    
    # Test 2: Non-well-formed XML
    non_well_formed_xml = ['<root>', '<child>content</child>']
    print(metric_engine.calculate(non_well_formed_xml, []))  # Should output a value <= 0.5
    
    # Test 3: Well-formed XML with DTD errors
    xml_with_dtd_errors = ['<!DOCTYPE root [', '<!ELEMENT root (child)>', '<!ELEMENT child ANY>', ']>', '<root>', '<child>content<child></child></child><extra>error</extra>', '</root>']
    # Note: For this test case, you would need an appropriate DTD to actually test DTD validation errors.
    print(metric_engine.calculate(xml_with_dtd_errors, []))
