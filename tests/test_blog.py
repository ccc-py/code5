"""Test: Use code5 with real LLM to generate and test a FastAPI blog system."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from code5.client import NVIDIAClient
from code5.config import load_config_from_env

needs_llm = pytest.mark.skipif(
    os.environ.get("TEST_LLM", "").lower() not in ("1", "true", "yes"),
    reason="LLM tests require TEST_LLM=1 environment variable",
)


def _kill_server(port: int = 8765):
    try:
        subprocess.run(
            f"lsof -ti:{port} | xargs kill -9 2>/dev/null",
            shell=True,
            timeout=5,
        )
    except Exception:
        pass


@needs_llm
class TestFastAPIBlog:
    """Test that code5 can use FastAPI to build a blog system via real LLM."""

    def setup_method(self):
        config = load_config_from_env()
        if not config.api_key:
            pytest.skip("No NVIDIA API key")
        self.client = NVIDIAClient(config)
        self.workdir = Path("/tmp/code5-blog-test")
        self.workdir.mkdir(parents=True, exist_ok=True)
        blog_file = self.workdir / "blog.py"
        if blog_file.exists():
            blog_file.unlink()

    def teardown_method(self):
        _kill_server()
        import shutil
        shutil.rmtree(self.workdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_llm_generates_and_runs_blog(self):
        """Use real LLM to generate FastAPI blog code and test all endpoints."""
        prompt = """Generate a complete Python file for a FastAPI blog system.

Requirements:
- File: blog.py
- Use FastAPI with Pydantic's BaseModel
- Use an in-memory list to store posts
- Each post has: id (auto-increment int), title (str), content (str), created_at (str)

Endpoints:
1. GET / -> returns {"message": "Blog API", "posts_count": N}
2. GET /posts -> returns list of all posts
3. POST /posts -> creates a new post (accepts JSON: {"title": "...", "content": "..."})
4. GET /posts/{post_id} -> returns a single post by ID
5. DELETE /posts/{post_id} -> deletes a post by ID

Error handling:
- Return 404 with {"detail": "Post not found"} for non-existent post IDs

Important:
- Import datetime.now() for created_at
- Use proper Pydantic models for request/response with type hints
- The file must be runnable as: uvicorn blog:app
- Include CORS middleware for all origins

Return ONLY the complete Python code. No markdown formatting, no explanations."""

        print("\n[LLM] Generating blog code...")
        code = await self.client.generate(prompt, "")
        print(f"[LLM] Generated {len(code)} characters")

        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        blog_file = self.workdir / "blog.py"
        blog_file.write_text(code)
        print(f"[Test] Written to {blog_file}")

        content = blog_file.read_text()
        assert "FastAPI" in content, "Missing FastAPI import"
        assert "app = FastAPI" in content, "Missing FastAPI() app"
        assert "/posts" in content, "Missing /posts endpoint"
        assert "BaseModel" in content, "Missing Pydantic BaseModel"
        print("[Test] Code validation passed")

        _kill_server()
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "blog:app", "--host", "127.0.0.1", "--port", "8765"],
            cwd=str(self.workdir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)

        import httpx

        try:
            r = httpx.get("http://127.0.0.1:8765/", timeout=5)
            assert r.status_code == 200, f"GET / returned {r.status_code}"
            data = r.json()
            assert "message" in data
            print(f"[Test] GET /: {data}")

            post_data = {"title": "Hello Blog", "content": "First post content"}
            r = httpx.post("http://127.0.0.1:8765/posts", json=post_data, timeout=5)
            assert r.status_code in (200, 201), f"POST /posts returned {r.status_code}"
            created = r.json()
            assert created["title"] == "Hello Blog"
            assert created["content"] == "First post content"
            assert "id" in created
            post_id = created["id"]
            print(f"[Test] POST /posts: id={post_id}")

            r = httpx.get("http://127.0.0.1:8765/posts", timeout=5)
            assert r.status_code == 200
            posts = r.json()
            assert isinstance(posts, list)
            assert len(posts) >= 1
            print(f"[Test] GET /posts: {len(posts)} posts")

            r = httpx.get(f"http://127.0.0.1:8765/posts/{post_id}", timeout=5)
            assert r.status_code == 200
            assert r.json()["id"] == post_id
            print(f"[Test] GET /posts/{post_id}: OK")

            r = httpx.get("http://127.0.0.1:8765/posts/99999", timeout=5)
            assert r.status_code == 404, f"Expected 404, got {r.status_code}"
            print("[Test] GET /posts/99999: 404 OK")

            r = httpx.delete(f"http://127.0.0.1:8765/posts/{post_id}", timeout=5)
            assert r.status_code in (200, 204), f"DELETE /posts/{post_id} returned {r.status_code}"
            print(f"[Test] DELETE /posts/{post_id}: OK")

            r = httpx.get(f"http://127.0.0.1:8765/posts/{post_id}", timeout=5)
            assert r.status_code == 404
            print("[Test] Deleted post returns 404: OK")

            print("\n[PASS] All blog endpoints passed!")
        finally:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
            _kill_server()
            await self.client.close()
