.PHONY: demo-cutoffs
demo-cutoffs:
	mkdir -p out
	python3 -m demo.demo_runner_timeaware samples/demo_cutoff_switch.csv out/recs_before.csv calendars/cutoffs.sample.yaml
	python3 -m demo.demo_runner_timeaware samples/demo_cutoff_switch.csv out/recs_after.csv  calendars/cutoffs_after.yaml
	@echo "Before:" && sed -n '2p' out/recs_before.csv
	@echo "After: " && sed -n '2p' out/recs_after.csv
