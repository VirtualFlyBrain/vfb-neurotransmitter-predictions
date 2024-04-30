import neuprint
from vfb_connect.neo.neo4j_tools import Neo4jConnect, dict_cursor
import pandas as pd
import sys

cutoff = float(sys.argv[1])
np_dataset = sys.argv[3]
vfb_site = sys.argv[4]
with open(sys.argv[2]) as file:
    token = file.read()

template_outfile = 'tmp/template.tsv'
np_client = neuprint.Client('https://neuprint.janelia.org', dataset=np_dataset, token=token)
vfb_client = Neo4jConnect('http://kb.virtualflybrain.org', 'neo4j', 'vfb')

# get predicted neurotransmitters
query = ('MATCH (n:Neuron) WHERE EXISTS(n.predictedNt) AND n.pre >= %s '
         'RETURN n.bodyId AS bodyId, n.predictedNt AS NT, n.predictedNtProb AS NT_prob'
         % cutoff)

neurotransmitters = np_client.fetch_custom(query).set_index('bodyId')

# get VFB individuals
query = ('MATCH (n:Individual)-[r:database_cross_reference|hasDbXref]->'
         '(s:Site {short_form:"%s"}) '
         'WHERE ((NOT EXISTS(n.deprecated)) OR (NOT n.deprecated[0]))'
         'RETURN n.iri AS iri, toInteger(r.accession[0]) AS bodyId' % vfb_site)

q = vfb_client.commit_list([query])
result = dict_cursor(q)
vfb_ids = pd.DataFrame.from_records(result)

# merge nts with VFB IDs
data = vfb_ids.join(neurotransmitters, 
                         on='bodyId', how='inner', 
                         validate='one_to_one'
                        ).reset_index(drop=True)
data = data.drop('bodyId', axis=1)

# replace NT name with GO term
data = data[data['NT']!='unknown']
nt_dict = {'acetylcholine':'GO:0014055', 
           'glutamate':'GO:0061535', 
           'gaba':'GO:0061534'}

data['NT'] = data['NT'].map(nt_dict)

# make template
data['type'] = 'owl:Class'
if np_dataset=='manc:v1.0':
    data['ref'] = 'doi:10.1101/2023.06.05.543757'

template_strings = pd.DataFrame({'iri': ['ID'], 'type': ['TYPE'],
                                 'NT': ['SC RO:0002215 some %'], 
                                 'NT_prob': ['>AT custom:confidence_value^^xsd:float'],
                                 'ref': ['>A oboInOwl:hasDbXref']})

extra_entities = ['RO:0002215', 'custom:confidence_value']
extra_entities.extend(list(nt_dict.values()))
typed_entities = pd.DataFrame({
    'iri': extra_entities,
    'type': ['owl:ObjectProperty', 'owl:AnnotationProperty'] + ['owl:Class'] * (len(extra_entities)-2),
    'NT': [''] * len(extra_entities),
    'NT_prob': [''] * len(extra_entities),
    'ref': [''] * len(extra_entities)
})

template = pd.concat([template_strings, data, typed_entities])
template.to_csv(template_outfile, index=None, sep='\t')