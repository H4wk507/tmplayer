clean-cache:
	find . \( \
		-type d -name __pycache__ -o -name "*.pyc" -o -type d -name .mypy_cache \
	\) -prune -exec rm -rf {} \;

clean-build:
	rm -rf build *.egg-info dist


clean: clean-cache clean-build

codetest:
	isort .
	black --line-length 79 --preview .
	flake8 . 
	mypy .

upload:
	python3 setup.py sdist bdist_wheel
	twine upload dist/*
