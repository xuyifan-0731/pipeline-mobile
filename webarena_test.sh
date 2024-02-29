
# python webarena_tools/generate_test_data.py
# mkdir -p ./.auth
# python webarena_tools/auto_login.py


python -m Pipeline.webarena_tools.generate_test_data
mkdir -p ./.auth
python -m Pipeline.webarena_tools.auto_login