wuv=/mnt/c/Users/katao/.local/bin/uv.exe
project_name=ytlive_helper
target=$(project_name)/$(project_name).exe
target_zip=$(project_name).zip
srcs=$(subst update.py,,$(wildcard *.py)) $(wildcard *.pyw)
#html_files=$(wildcard html/*.*)
html_files=$(wildcard *.html)
version=$(shell head -n1 version.txt)

all: $(target_zip)
$(target_zip): $(target) $(html_files) version.txt
	@cp version.txt $(project_name)
# 	@cp -a $(html_files) $(project_name)
	@rm -rf $(project_name)/log
	@zip $(target_zip) $(project_name)/*

$(target): $(srcs)
	$(wuv) run nuitka -j 16 \
	  --mingw64 \
 	  --onefile \
 	  --output-dir=$(project_name) \
	  --remove-output \
	  --windows-disable-console \
	  --standalone \
	  --company-name="dj-kata" \
	  --product-name="ytlive_helper" \
	  --file-version=$(version) \
	  --include-module=config_secret \
	  --enable-plugin=tk-inter --windows-icon-from-ico=icon.ico $(project_name).pyw

dist: 
	@cp -a html to_bin/
	@cp -a version.txt to_bin/
	@cp -a $(project_name)/*.exe to_bin/

clean:
	@rm -rf $(target)
	@rm -rf __pycache__

test:
	@$(wuv) run $(project_name).pyw
