from vfb_connect.neo.neo4j_tools import Neo4jConnect, dict_cursor
import pandas as pd
import sys

# until hb predictions are available from neuprint, must use file as input

cutoff = float(sys.argv[1])
vfb_site = sys.argv[2]
infile = sys.argv[3]

template_outfile = 'tmp/template.tsv'
neurotransmitters = pd.read_csv(infile, sep='\t', index_col='accession', low_memory=False)
vfb_client = Neo4jConnect('http://kb.virtualflybrain.org', 'neo4j', 'vfb')

neurotransmitters = neurotransmitters[neurotransmitters['pre']>=cutoff]
neurotransmitters.rename({'conf_nt': 'NT', 'conf_nt_p': 'NT_prob'}, axis=1, inplace=True)
neurotransmitters.drop(['pre', 'top_nt', 'top_nt_p', 'acetylcholine', 'glutamate', 'gaba', 'dopamine', 'serotonin', 'octopamine'], axis=1, inplace=True)

# get VFB individuals
query = ('MATCH (n:Individual)-[r:database_cross_reference|hasDbXref]->'
         '(s:Site {short_form:"%s"}) '
         'WHERE ((NOT EXISTS(n.deprecated)) OR (NOT n.deprecated[0]))'
         'RETURN n.iri AS iri, toInteger(r.accession[0]) AS accession' % vfb_site)

q = vfb_client.commit_list([query])
result = dict_cursor(q)
vfb_ids = pd.DataFrame.from_records(result)

# merge nts with VFB IDs
data = vfb_ids.join(neurotransmitters, 
                         on='accession', how='inner', 
                         validate='one_to_one'
                        ).reset_index(drop=True)
data = data.drop('accession', axis=1)


# replace NT name with GO term
nt_dict = {'acetylcholine':'GO:0014055', 
           'glutamate':'GO:0061535', 
           'gaba':'GO:0061534', 
           'dopamine':'GO:0061527', 
           'serotonin':'GO:0060096', 
           'octopamine':'GO:0061540'}
data = data[data['NT'].isin(nt_dict.keys())]
data['NT'] = data['NT'].map(nt_dict)


# make template
data['type'] = 'owl:Class'
if vfb_site == 'neuprint_JRC_Hemibrain_1point1' or 'flywire783':
    data['ref'] = 'FlyBase:FBrf0259490'

template_strings = pd.DataFrame({'iri': ['ID'], 'type': ['TYPE'],
                                 'NT': ['SC RO:0002215 some %'], 
                                 'NT_prob': ['>AT custom:confidence_value^^xsd:float'],
                                 'ref': ['>A oboInOwl:hasDbXref SPLIT=|'']})

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
