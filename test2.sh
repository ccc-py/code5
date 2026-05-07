TEST_LLM=1 python -m pytest tests/test_integration.py -v --tb=short -m llm

python -m pytest tests/test_integration.py -v --tb=short

# 只跑 Mock
pytest tests/test_integration.py::TestBgFix -v

# 包含 LLM
TEST_LLM=1 pytest tests/test_integration.py::TestBgFix -v

TEST_LLM=1 pytest tests/test_integration.py::TestWithLLM -v