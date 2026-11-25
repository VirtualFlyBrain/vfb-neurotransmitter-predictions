from cypher_query import query_neo4j, auth, kb
import neuprint
import pandas as pd
import os
import sys

cutoff = float(sys.argv[1])
np_dataset = sys.argv[3]
vfb_site = sys.argv[4]

template_outfile = 'tmp/template.tsv'
# latest download only, named without version (e.g. data/manc_download.tsv)
download_file = f'data/{np_dataset.split(":")[0]}_download.tsv'

if sys.argv[2] == 'OFFLINE':
    # CI: build from the committed download instead of querying neuPrint
    neurotransmitters = pd.read_csv(download_file, sep='\t')
else:
    token_file = os.path.expanduser(sys.argv[2])
    try:
        with open(token_file) as file:
            token = file.read().strip()
    except FileNotFoundError:
        sys.exit(f'neuPrint token file not found: {token_file}')
    if not token:
        sys.exit(f'neuPrint token file is empty: {token_file}')

    np_client = neuprint.Client('https://neuprint.janelia.org', dataset=np_dataset, token=token)
    # get predicted neurotransmitters
    # confidence has different name in manc and ol...
    query = ('MATCH (n:Neuron) WHERE EXISTS(n.predictedNt) AND n.pre >= %s '
             'RETURN n.bodyId AS bodyId, n.predictedNt AS NT, n.predictedNtProb AS NT_prob1, '
             'n.predictedNtConfidence AS NT_prob2 '
             'ORDER BY bodyId'
             % str(cutoff))

    neurotransmitters = np_client.fetch_custom(query)
    # use prob1, with NA filled to prob2 values - then infer dtype (float) - this will not be done by fillna in future
    with pd.option_context('future.no_silent_downcasting', True):
        neurotransmitters['NT_prob'] = neurotransmitters['NT_prob1'].fillna(neurotransmitters['NT_prob2']).infer_objects()
    neurotransmitters = neurotransmitters.drop(['NT_prob1', 'NT_prob2'], axis=1)
    neurotransmitters.to_csv(download_file, sep='\t', index=None)

# drop anything that is missing a confidence value, adjust to % and round down
neurotransmitters = neurotransmitters[~neurotransmitters['NT_prob'].isna()]
if all(neurotransmitters['NT_prob'] <= 1):
    neurotransmitters['NT_prob'] = neurotransmitters['NT_prob']*100
neurotransmitters['NT_prob'] = neurotransmitters['NT_prob'].apply(int) / 100

# get VFB individuals
query = ('MATCH (n:Individual)-[r:database_cross_reference|hasDbXref]->'
         '(s:Site {short_form:"%s"}) '
         'WHERE ((NOT EXISTS(n.deprecated)) OR (NOT n.deprecated[0]))'
         'RETURN n.iri AS iri, toInteger(r.accession[0]) AS bodyId' % vfb_site)

vfb_ids = query_neo4j(query, url=kb, auth=auth)

# merge nts with VFB IDs
data = vfb_ids.merge(neurotransmitters, 
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
    data['ref'] = 'doi:10.7554/eLife.97769.1'
elif np_dataset.startswith('optic-lobe:'):
    data['ref'] = 'FlyBase:FBrf0262545'
elif np_dataset.startswith('male-cns:'):
    data['ref'] = 'doi:10.1101/2025.10.09.680999'
else:
    raise ValueError(f'No reference set for dataset {np_dataset}')

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