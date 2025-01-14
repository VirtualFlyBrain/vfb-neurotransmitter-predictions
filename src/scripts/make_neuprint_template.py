from cypher_query import query_neo4j, auth, kb
import neuprint
import pandas as pd
import sys

cutoff = float(sys.argv[1])
np_dataset = sys.argv[3]
vfb_site = sys.argv[4]

try:
    with open(sys.argv[2]) as file:
        token = file.read()
    update = True
except FileNotFoundError:
    update = False

template_outfile = 'tmp/template.tsv'

if update:
    np_client = neuprint.Client('https://neuprint.janelia.org', dataset=np_dataset, token=token)
    # get predicted neurotransmitters
    # confidence has different name in manc and ol...
    query = ('MATCH (n:Neuron) WHERE EXISTS(n.predictedNt) AND n.pre >= %s '
             'RETURN n.bodyId AS bodyId, n.predictedNt AS NT, n.predictedNtProb AS NT_prob1, '
             'n.predictedNtConfidence AS NT_prob2 '
             'ORDER BY bodyId'
             % str(cutoff))
    
    neurotransmitters = np_client.fetch_custom(query).set_index('bodyId')
    # use prob1, with NA filled to prob2 values - then infer dtype (float) - this will not be done by fillna in future
    with pd.option_context('future.no_silent_downcasting', True):
        neurotransmitters['NT_prob'] = neurotransmitters['NT_prob1'].fillna(neurotransmitters['NT_prob2']).infer_objects()
    neurotransmitters = neurotransmitters.drop(['NT_prob1', 'NT_prob2'], axis=1)
    neurotransmitters.to_csv(f'data/{vfb_site}_download.tsv', sep='\t')

else:
    neurotransmitters = pd.read_csv(f'data/{vfb_site}_download.tsv', sep='\t', index_col='bodyId')

# drop anything that is missing a confidence value
neurotransmitters = neurotransmitters[~neurotransmitters['NT_prob'].isna()]

# get VFB individuals
query = ('MATCH (n:Individual)-[r:database_cross_reference|hasDbXref]->'
         '(s:Site {short_form:"%s"}) '
         'WHERE ((NOT EXISTS(n.deprecated)) OR (NOT n.deprecated[0]))'
         'RETURN n.iri AS iri, toInteger(r.accession[0]) AS bodyId' % vfb_site)

vfb_ids = query_neo4j(query, url=kb, auth=auth)

# merge nts with VFB IDs
data = vfb_ids.join(neurotransmitters, 
                         on='bodyId', how='inner', 
                         validate='one_to_one'
                        ).reset_index(drop=True)
data = data.drop('bodyId', axis=1)

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

if np_dataset.startswith('manc:'):
    data['ref'] = 'doi:10.1101/2023.06.05.543757'
if np_dataset.startswith('optic-lobe:'):
    data['ref'] = 'doi:10.1101/2024.04.16.589741'

template_strings = pd.DataFrame({'iri': ['ID'], 'type': ['TYPE'],
                                 'NT': ['SC RO:0002215 some %'], 
                                 'NT_prob': ['>AT custom:confidence_value^^xsd:float'],
                                 'ref': ['>A oboInOwl:hasDbXref SPLIT=|']})

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