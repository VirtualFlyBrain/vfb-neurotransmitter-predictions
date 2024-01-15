import neuprint
from vfb_connect.neo.neo4j_tools import Neo4jConnect, dict_cursor
import pandas as pd
import sys

cutoff = float(sys.argv[1])
np_dataset = sys.argv[3]
with open(sys.argv[2]) as file:
    token = file.read()

template_outfile = 'tmp/template.tsv'
np_client = neuprint.Client('https://neuprint.janelia.org', dataset=np_dataset, token=token)
vfb_client = Neo4jConnect('http://kb.virtualflybrain.org', 'neo4j', 'vfb')

query = ('MATCH (n:Neuron) WHERE EXISTS(n.ntAcetylcholineProb)'
         'RETURN n.bodyId AS bodyId, n.ntAcetylcholineProb AS Ach_prob, n.ntGabaProb AS GABA_prob, '
         'n.ntGlutamateProb AS Glut_prob')

neurotransmitters = np_client.fetch_custom(query).set_index('bodyId')

query = ('MATCH (n:Individual)-[r:database_cross_reference|hasDbXref]->(s:Site {short_form:"neuprint_JRC_Manc"}) '
         'RETURN n.iri AS iri, toInteger(r.accession[0]) AS bodyId')

q = vfb_client.commit_list([query])
result = dict_cursor(q)

manc_vfb_ids = pd.DataFrame.from_records(result)

data = manc_vfb_ids.join(neurotransmitters, 
                         on='bodyId', how='inner', 
                         validate='one_to_one'
                        ).reset_index(drop=True)
data = data.drop('bodyId', axis=1)
data['type'] = 'owl:Class'
data['Ach'] = 'GO:0014055'
data['GABA'] = 'GO:0061534'
data['Glut'] = 'GO:0061535'

data = data[['iri', 'type', 'Ach', 'Ach_prob', 'GABA', 'GABA_prob', 'Glut', 'Glut_prob']]

# filter by cutoff value
def filter_on_cutoff(row, columns, prob_cutoff=cutoff):
    for col in columns:
        prob_col = f'{col}_prob'
        if row[prob_col] <= prob_cutoff:
            row[col] = ''
            row[prob_col] = ''
    return row

neurotransmitter_cols = ['Ach', 'GABA', 'Glut']
filtered_data = data.apply(filter_on_cutoff, axis=1, columns=neurotransmitter_cols)
# remove any rows with no NT data
filtered_data = filtered_data[filtered_data[neurotransmitter_cols].apply(lambda x: ''.join(map(str, x)) != '', axis=1)]

# make template
template_strings = pd.DataFrame({'iri': ['ID'], 'type': ['TYPE'],
                                 'Ach': ['SC RO:0002215 some %'], 
                                 'Ach_prob': ['>AT custom:confidence_value^^xsd:float'],
                                 'GABA': ['SC RO:0002215 some %'], 
                                 'GABA_prob': ['>AT custom:confidence_value^^xsd:float'],
                                 'Glut': ['SC RO:0002215 some %'], 
                                 'Glut_prob': ['>AT custom:confidence_value^^xsd:float']})

typed_entities = pd.DataFrame({'iri': ['RO:0002215', 'GO:0014055', 'GO:0061534', 'GO:0061535', 'custom:confidence_value'], 
                               'type': ['owl:ObjectProperty', 'owl:Class', 'owl:Class', 'owl:Class', 'owl:AnnotationProperty'],
                                 'Ach': ['','','','',''], 
                                 'Ach_prob': ['','','','',''],
                                 'GABA': ['','','','',''], 
                                 'GABA_prob': ['','','','',''],
                                 'Glut': ['','','','',''], 
                                 'Glut_prob': ['','','','','']})
                                 
template = pd.concat([template_strings, filtered_data, typed_entities])
template.to_csv(template_outfile, index=None, sep='\t')