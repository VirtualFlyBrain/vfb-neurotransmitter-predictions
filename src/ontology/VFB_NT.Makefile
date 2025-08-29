## Customize Makefile settings for VFB_NT
## 
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile

# accessing neuprint requires a token - save in a single line in a text file and specify path with this variable
# if no token is found, neuprint data will not be updated
NEUPRINT_TOKEN_FILE = '../../np_token.txt'
# threshold number of presynapses (we do not filter by probability) 
# Eckstein (2024) analysis filters to >=100 already
CUTOFF = 100

########## Installations

.PHONY: setup_venv
setup_venv:
	apt-get update
	apt-get -y install python3.12-venv
	python3 -m venv my-venv

.PHONY: install_requirements
install_requirements: setup_venv
	my-venv/bin/pip install -r $(SCRIPTSDIR)/requirements.txt

get_query_script:
	wget -O $(SCRIPTSDIR)/cypher_query.py https://raw.githubusercontent.com/VirtualFlyBrain/vfb-scRNAseq-ontology/main/src/scripts/cypher_query.py


$(SRC): get_query_script install_requirements | $(TMPDIR)
	my-venv/bin/python3 $(SCRIPTSDIR)/make_neuprint_template.py $(CUTOFF) $(NEUPRINT_TOKEN_FILE) 'manc:v1.2.1' 'neuprint_JRC_Manc' &&\
	$(ROBOT) template --template $(TMPDIR)/template.tsv --prefix "custom: http://n2o.neo/custom/" \
		--output $(TMPDIR)/manc_nt_predictions.owl &&\
	my-venv/bin/python3 $(SCRIPTSDIR)/make_neuprint_template.py $(CUTOFF) $(NEUPRINT_TOKEN_FILE) 'optic-lobe:v1.0.1' 'neuprint_JRC_OpticLobe_v1_0_1' &&\
	$(ROBOT) template --template $(TMPDIR)/template.tsv --prefix "custom: http://n2o.neo/custom/" \
		--output $(TMPDIR)/OL_nt_predictions.owl &&\
	my-venv/bin/python3 $(SCRIPTSDIR)/make_template_from_file.py $(CUTOFF) 'neuprint_JRC_Hemibrain_1point2point1'  'data/hemibrain_predictions.tsv' &&\
	$(ROBOT) template --template $(TMPDIR)/template.tsv --prefix "custom: http://n2o.neo/custom/" \
		--output $(TMPDIR)/hb_nt_predictions.owl &&\
	my-venv/bin/python3 $(SCRIPTSDIR)/make_template_from_file.py $(CUTOFF) 'flywire783' 'data/flywire_predictions.tsv' &&\
	$(ROBOT) template --template $(TMPDIR)/template.tsv --prefix "custom: http://n2o.neo/custom/" \
		--output $(TMPDIR)/fw_nt_predictions.owl &&\
	$(ROBOT) merge --inputs "$(TMPDIR)/*_nt_predictions.owl" \
		--input VFB_NT-annotations.ofn \
		--output $(SRC) &&\
	my-venv/bin/python3 $(SCRIPTSDIR)/modify_owl.py $(SRC) &&\
	$(ROBOT) convert -i $(SRC) -o $(SRC).gz -f owl &&\
	rm $(TMPDIR)/*_nt_predictions.owl &&\
	echo "\nOntology source file updated!\n"

# change iri
$(ONT).owl: $(ONT)-full.owl
	grep -v owl:versionIRI $< > $@.tmp.owl
	$(ROBOT) annotate -i $@.tmp.owl --ontology-iri http://virtualflybrain.org/data/VFB/OWL/VFB_NT.owl \
		convert -o $@.tmp.owl && mv $@.tmp.owl $@

# make ontologyterms.txt report
robot_reports: $(TMPDIR)/ontologyterms.txt
	sort -o $< $<
	cp $< $(REPORTDIR)/ontologyterms.txt
