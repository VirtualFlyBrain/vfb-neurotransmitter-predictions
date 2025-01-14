import requests
import pandas as pd


kb = 'http://kb.virtualflybrain.org/db/neo4j/tx/commit'
kbw = 'http://kbw.virtualflybrain.org:7474/db/neo4j/tx/commit'
pdb = 'http://pdb.virtualflybrain.org/db/neo4j/tx/commit'
pdb_dev = 'http://pdb-dev.virtualflybrain.org/db/neo4j/tx/commit'
auth = ("neo4j", "vfb")

def query_neo4j(query, url=kb, auth=auth, verbose=False):
    """Runs cypher query and returns results as a Dataframe.
    No results gives empty dataframe, error returns False."""
    
    json_query = {"statements": [{"statement": query}]}
    
    if verbose:
        print(f'Running query: {query}')
    try:
        response = requests.post(
            url,
            json=json_query,
            auth=auth,
            headers={'Content-Type': 'application/json'}
            )
        response_json = response.json()
        if verbose:
            print("Response:", response_json)
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False
    
    flat_json = pd.json_normalize(response_json['results'][0]['data'])
    if flat_json.empty:
        return pd.DataFrame(columns=response_json['results'][0]['columns'])
    else:
        response_dataframe = pd.DataFrame.from_records(
            data=flat_json['row'], 
            columns=response_json['results'][0]['columns']
            )
        return response_dataframe


# FOR TESTING

if __name__ == '__main__':
    query = ("""
    MATCH (n:Class)
    WHERE n.short_form IN ['FBbt_00017015']
    RETURN n.short_form, n.label
    """)
    
    results = query_neo4j(query=query, verbose=True)
    print(results)
