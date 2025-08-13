.PHONY: demo gif
demo:
	./scripts/run_demo.sh
gif:
	asciinema rec --overwrite -c "./scripts/run_demo.sh" demo.cast
	agg --theme dracula --font-size 18 --cols 100 --rows 28 demo.cast docs/demo/junction-demo.gif
