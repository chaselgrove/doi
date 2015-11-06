.PHONY : www

default : install

install : www /var/www/doi/index.html

/var/www/doi/index.html : apps/templates/site_index.tmpl apps/templates/base.tmpl
	./compile_site_index

www :
	cp -v www/* /var/www/doi/.

# eof
