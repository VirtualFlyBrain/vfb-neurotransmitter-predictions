## Customize Makefile settings for VFB_NT
## 
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile

# accessing neuprint requires a token - save in a single line in a text file and specify path with this variable
# if no token is found, neuprint data will not be updated
NEUPRINT_TOKEN_FILE = '../../np_token.txt'
# threshold number of presynapses (we do not filter by probability)
CUTOFF = 100

.PHONY: install_modules
install_modules:
	python3 -m pip install -r $(SCRIPTSDIR)/requirements.txt

$(SRC): install_modules | $(TMPDIR)
	python3 $(SCRIPTSDIR)/make_neuprint_template.py $(CUTOFF) $(NEUPRINT_TOKEN_FILE) 'manc:v1.0' 'neuprint_JRC_Manc' &&\
	$(ROBOT) template --template $(TMPDIR)/template.tsv --prefix "custom: http://n2o.neo/custom/" \
		--output $(TMPDIR)/manc_nt_predictions.owl &&\
	python3 $(SCRIPTSDIR)/make_neuprint_template.py $(CUTOFF) $(NEUPRINT_TOKEN_FILE) 'optic-lobe:v1.0' 'neuprint_JRC_OpticLobe_v1_0' &&\
	$(ROBOT) template --template $(TMPDIR)/template.tsv --prefix "custom: http://n2o.neo/custom/" \
		--output $(TMPDIR)/OL_nt_predictions.owl &&\
	python3 $(SCRIPTSDIR)/make_template_from_file.py $(CUTOFF) 'neuprint_JRC_Hemibrain_1point1'  'data/hemibrain_predictions.tsv' &&\
	$(ROBOT) template --template $(TMPDIR)/template.tsv --prefix "custom: http://n2o.neo/custom/" \
		--output $(TMPDIR)/hb_nt_predictions.owl &&\
	$(ROBOT) merge --inputs "$(TMPDIR)/*_nt_predictions.owl" \
		--input VFB_NT-annotations.ofn \
		--output $(SRC) &&\
	python3 $(SCRIPTSDIR)/modify_owl.py $(SRC) &&\
	echo "\nOntology source file updated!\n"

# change iri
$(ONT).owl: $(ONT)-full.owl
	grep -v owl:versionIRI $< > $@.tmp.owl
	$(ROBOT) annotate -i $@.tmp.owl --ontology-iri http://virtualflybrain.org/data/VFB/OWL/VFB_NT.owl \
		convert -o $@.tmp.owl && mv $@.tmp.owl $@