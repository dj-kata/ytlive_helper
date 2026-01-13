wuv=/mnt/c/Users/katao/.local/bin/uv.exe
project_name=ytlive_helper
target=$(project_name)/$(project_name).exe
target_zip=$(project_name).zip
srcs=$(subst update.py,,$(wildcard *.py)) $(wildcard *.pyw)
html_files=$(wildcard html/*.html)
version=$(shell head -n1 version.txt)

all: $(target_zip)
$(target_zip): $(target) $(html_files) version.txt
	@cp version.txt $(project_name)
	@cp -a html $(project_name)
	@cp icon.ico $(project_name)
	@rm -rf $(project_name)/log
	@rm -rf $(project_name)/*.json
	@zip -r $(target_zip) $(project_name)/*

# 	  --output-dir=$(project_name) --remove-output --onefile
# 	@mv $(project_name).dist/* $(project_name)/
# 	@rmdir $(project_name)/$(project_name).dist
$(target): $(srcs)
	@rm -rf $(project_name)
	$(wuv) run setup.py build

dist: 
	@cp -a html to_bin/
	@cp -a version.txt to_bin/
	@cp -a $(project_name)/*.exe to_bin/

clean:
	@rm -rf $(target)
	@rm -rf __pycache__

test:
	@$(wuv) run $(project_name).pyw
