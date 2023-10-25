import re
import sys

file = sys.argv[1]

with open(file, 'r') as f:
    text = f.read()

pattern_1 = ("    <owl:Class rdf:about=\"http://virtualflybrain.org/reports/VFB_([A-Za-z0-9]{8})\">\n"
"        <rdfs:subClassOf rdf:nodeID=\"genid([0-9]+)\"/>\n"
"        <rdfs:subClassOf rdf:nodeID=\"genid([0-9]+)\"/>\n"
"        <rdfs:subClassOf rdf:nodeID=\"genid([0-9]+)\"/>\n"
"    </owl:Class>")

replacement_1 = ("    <owl:NamedIndividual rdf:about=\"http://virtualflybrain.org/reports/VFB_\\1\">\n"
"        <rdf:type rdf:nodeID=\"genid\\2\"/>\n"
"        <rdf:type rdf:nodeID=\"genid\\3\"/>\n"
"        <rdf:type rdf:nodeID=\"genid\\4\"/>\n"
"    </owl:NamedIndividual>")

pattern_2 = ("        <owl:annotatedProperty rdf:resource=\"http://www.w3.org/2000/01/rdf-schema#subClassOf\"/>")

replacement_2 = ("        <owl:annotatedProperty rdf:resource=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#type\"/>")

text = re.sub(pattern_1, replacement_1, text)
text = re.sub(pattern_2, replacement_2, text)

with open(file, 'w') as f:
    f.write(text)