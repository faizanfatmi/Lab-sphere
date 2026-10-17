"""
Code Execution and Automated Grading Service for LabSphere.
Supports Judge0 CE/RapidAPI and isolated local sandboxing with strict timeouts and output sanitization.
"""

import os
import sys
import time
import base64
import subprocess
import tempfile
import requests
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from django.conf import settings


@dataclass
class ExecutionResult:
    status: str  # ACCEPTED, WRONG_ANSWER, COMPILATION_ERROR, TIME_LIMIT_EXCEEDED, RUNTIME_ERROR, INTERNAL_ERROR
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    time_ms: int = 0
    memory_kb: int = 0
    exit_code: int = 0
    is_success: bool = False


@dataclass
class TestEvaluationResult:
    test_case_id: int
    is_sample: bool
    status: str
    time_ms: int
    memory_kb: int
    user_stdout: str
    expected_output: str
    error_message: str = ""
    passed: bool = False


class BaseExecutor:
    def execute(self, language: str, source_code: str, stdin: str, time_limit_sec: float = 2.0, memory_limit_mb: int = 256) -> ExecutionResult:
        raise NotImplementedError


class Judge0Executor(BaseExecutor):
    """
    Integrates with Judge0 CE or RapidAPI hosted instance.
    """
    LANGUAGE_IDS = {
        'cpp': 54,     # C++ (GCC 9.2.0)
        'c': 50,       # C (GCC 9.2.0)
        'java': 62,    # Java (OpenJDK 13.0.1)
        'python': 71,  # Python (3.8.1)
    }

    def __init__(self):
        self.api_url = getattr(settings, 'JUDGE0_API_URL', 'https://judge0-ce.p.rapidapi.com').rstrip('/')
        self.api_key = getattr(settings, 'JUDGE0_API_KEY', '')
        self.api_host = getattr(settings, 'JUDGE0_API_HOST', 'judge0-ce.p.rapidapi.com')

    def execute(self, language: str, source_code: str, stdin: str, time_limit_sec: float = 2.0, memory_limit_mb: int = 256) -> ExecutionResult:
        lang_id = self.LANGUAGE_IDS.get(language.lower(), 71)
        endpoint = f"{self.api_url}/submissions?base64_encoded=true&wait=true"
        
        headers = {
            'Content-Type': 'application/json',
        }
        if self.api_key:
            headers['X-RapidAPI-Key'] = self.api_key
            headers['X-RapidAPI-Host'] = self.api_host

        payload = {
            "language_id": lang_id,
            "source_code": base64.b64encode(source_code.encode()).decode(),
            "stdin": base64.b64encode((stdin or "").encode()).decode(),
            "cpu_time_limit": min(float(time_limit_sec), 5.0),
            "memory_limit": min(int(memory_limit_mb) * 1024, 512000),  # in KB
        }

        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=12)
            if response.status_code not in (200, 201):
                return ExecutionResult(
                    status="INTERNAL_ERROR",
                    stderr=f"Judge0 API returned HTTP {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            status_desc = data.get("status", {}).get("description", "Unknown")
            status_id = data.get("status", {}).get("id", 0)

            stdout = base64.b64decode(data.get("stdout") or "").decode(errors="replace")
            stderr = base64.b64decode(data.get("stderr") or "").decode(errors="replace")
            compile_output = base64.b64decode(data.get("compile_output") or "").decode(errors="replace")

            time_ms = int(float(data.get("time") or 0) * 1000)
            memory_kb = int(data.get("memory") or 0)

            # Map Judge0 status ID
            # 3 = Accepted, 4 = Wrong Answer, 5 = TLE, 6 = Compilation Error, 7-12 = Runtime Errors
            if status_id == 3:
                mapped_status = "ACCEPTED"
            elif status_id == 4:
                mapped_status = "WRONG_ANSWER"
            elif status_id == 5:
                mapped_status = "TIME_LIMIT_EXCEEDED"
            elif status_id == 6:
                mapped_status = "COMPILATION_ERROR"
            elif 7 <= status_id <= 12:
                mapped_status = "RUNTIME_ERROR"
            else:
                mapped_status = "RUNTIME_ERROR" if stderr else "ACCEPTED"

            return ExecutionResult(
                status=mapped_status,
                stdout=stdout,
                stderr=stderr,
                compile_output=compile_output,
                time_ms=time_ms,
                memory_kb=memory_kb,
                is_success=(status_id == 3 or not (stderr or compile_output))
            )
        except Exception as e:
            return ExecutionResult(
                status="INTERNAL_ERROR",
                stderr=f"Judge0 connection error: {str(e)}"
            )


class SandboxedProcessExecutor(BaseExecutor):
    """
    Isolated local process execution with clean environment, strict subprocess timeout,
    and output size limits. Safe fallback when Judge0 API is not configured or in local development.
    """
    MAX_OUTPUT_BYTES = 64 * 1024  # 64 KB cap

    def execute(self, language: str, source_code: str, stdin: str, time_limit_sec: float = 2.0, memory_limit_mb: int = 256) -> ExecutionResult:
        lang = language.lower()
        clean_env = {
            'PATH': os.environ.get('PATH', ''),
            'SYSTEMROOT': os.environ.get('SYSTEMROOT', 'C:\\Windows'),
            'TMP': tempfile.gettempdir(),
            'TEMP': tempfile.gettempdir(),
        }

        with tempfile.TemporaryDirectory(prefix="ls_sandbox_") as tmpdir:
            start_time = time.perf_counter()

            if lang in ('python', 'py'):
                script_path = os.path.join(tmpdir, "solution.py")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(source_code)

                cmd = [sys.executable, "-I", script_path]  # -I isolates from sys.path & site-packages
                try:
                    proc = subprocess.run(
                        cmd,
                        input=stdin.encode("utf-8") if stdin else b"",
                        capture_output=True,
                        timeout=time_limit_sec,
                        env=clean_env,
                        cwd=tmpdir
                    )
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                    stdout = proc.stdout[:self.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                    stderr = proc.stderr[:self.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

                    if proc.returncode != 0:
                        return ExecutionResult(
                            status="RUNTIME_ERROR",
                            stdout=stdout,
                            stderr=stderr,
                            time_ms=elapsed_ms,
                            exit_code=proc.returncode
                        )
                    return ExecutionResult(
                        status="ACCEPTED",
                        stdout=stdout,
                        stderr=stderr,
                        time_ms=elapsed_ms,
                        is_success=True
                    )
                except subprocess.TimeoutExpired:
                    return ExecutionResult(
                        status="TIME_LIMIT_EXCEEDED",
                        time_ms=int(time_limit_sec * 1000),
                        stderr="Execution timed out."
                    )
                except Exception as e:
                    return ExecutionResult(status="INTERNAL_ERROR", stderr=str(e))

            elif lang in ('cpp', 'c'):
                is_c = (lang == 'c')
                src_ext = ".c" if is_c else ".cpp"
                src_path = os.path.join(tmpdir, f"solution{src_ext}")
                exe_name = "solution.exe" if os.name == 'nt' else "solution"
                exe_path = os.path.join(tmpdir, exe_name)

                with open(src_path, "w", encoding="utf-8") as f:
                    f.write(source_code)

                # Use gcc for C, g++ for C++
                compiler = "gcc" if is_c else "g++"
                compile_cmd = [compiler, "-O2", "-Wall", src_path, "-o", exe_path]
                try:
                    compile_proc = subprocess.run(
                        compile_cmd,
                        capture_output=True,
                        timeout=5.0,
                        env=clean_env,
                        cwd=tmpdir
                    )
                    if compile_proc.returncode != 0:
                        compile_out = compile_proc.stderr[:self.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                        return ExecutionResult(
                            status="COMPILATION_ERROR",
                            compile_output=compile_out,
                            stderr=compile_out
                        )
                except FileNotFoundError:
                    # If gcc not found, try g++ as fallback for C
                    if is_c:
                        try:
                            compile_proc = subprocess.run(
                                ["g++", "-O2", "-Wall", src_path, "-o", exe_path],
                                capture_output=True,
                                timeout=5.0,
                                env=clean_env,
                                cwd=tmpdir
                            )
                            if compile_proc.returncode != 0:
                                compile_out = compile_proc.stderr[:self.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                                return ExecutionResult(
                                    status="COMPILATION_ERROR",
                                    compile_output=compile_out,
                                    stderr=compile_out
                                )
                        except FileNotFoundError:
                            return ExecutionResult(
                                status="INTERNAL_ERROR",
                                stderr="C/C++ compiler (gcc/g++) is not available on this server environment."
                            )
                    else:
                        return ExecutionResult(
                            status="INTERNAL_ERROR",
                            stderr="C++ compiler (g++) is not available on this server environment."
                        )
                except subprocess.TimeoutExpired:
                    return ExecutionResult(status="COMPILATION_ERROR", stderr="Compilation timed out.")

                # Run executable
                try:
                    proc = subprocess.run(
                        [exe_path],
                        input=stdin.encode("utf-8") if stdin else b"",
                        capture_output=True,
                        timeout=time_limit_sec,
                        env=clean_env,
                        cwd=tmpdir
                    )
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                    stdout = proc.stdout[:self.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                    stderr = proc.stderr[:self.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

                    if proc.returncode != 0:
                        return ExecutionResult(
                            status="RUNTIME_ERROR",
                            stdout=stdout,
                            stderr=stderr,
                            time_ms=elapsed_ms
                        )
                    return ExecutionResult(
                        status="ACCEPTED",
                        stdout=stdout,
                        time_ms=elapsed_ms,
                        is_success=True
                    )
                except subprocess.TimeoutExpired:
                    return ExecutionResult(
                        status="TIME_LIMIT_EXCEEDED",
                        time_ms=int(time_limit_sec * 1000),
                        stderr="Execution timed out."
                    )

            elif lang == 'java':
                src_path = os.path.join(tmpdir, "Solution.java")
                with open(src_path, "w", encoding="utf-8") as f:
                    f.write(source_code)

                try:
                    # Compile
                    compile_proc = subprocess.run(
                        ["javac", src_path],
                        capture_output=True,
                        timeout=6.0,
                        env=clean_env,
                        cwd=tmpdir
                    )
                    if compile_proc.returncode != 0:
                        compile_out = compile_proc.stderr[:self.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                        return ExecutionResult(
                            status="COMPILATION_ERROR",
                            compile_output=compile_out,
                            stderr=compile_out
                        )
                    # Run
                    proc = subprocess.run(
                        ["java", "-Xmx256m", "Solution"],
                        input=stdin.encode("utf-8") if stdin else b"",
                        capture_output=True,
                        timeout=time_limit_sec,
                        env=clean_env,
                        cwd=tmpdir
                    )
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                    stdout = proc.stdout[:self.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                    stderr = proc.stderr[:self.MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

                    if proc.returncode != 0:
                        return ExecutionResult(
                            status="RUNTIME_ERROR",
                            stdout=stdout,
                            stderr=stderr,
                            time_ms=elapsed_ms
                        )
                    return ExecutionResult(
                        status="ACCEPTED",
                        stdout=stdout,
                        time_ms=elapsed_ms,
                        is_success=True
                    )
                except FileNotFoundError:
                    return ExecutionResult(
                        status="INTERNAL_ERROR",
                        stderr="Java SDK (javac/java) is not installed on this server environment."
                    )
                except subprocess.TimeoutExpired:
                    return ExecutionResult(
                        status="TIME_LIMIT_EXCEEDED",
                        time_ms=int(time_limit_sec * 1000),
                        stderr="Execution timed out."
                    )

            return ExecutionResult(status="INTERNAL_ERROR", stderr=f"Unsupported language: {language}")


class MockExecutor(BaseExecutor):
    """
    Mock Executor for automated test cases or offline simulation.
    """
    def __init__(self, should_pass=True, mock_stdout=None):
        self.should_pass = should_pass
        self.mock_stdout = mock_stdout

    def execute(self, language: str, source_code: str, stdin: str, time_limit_sec: float = 2.0, memory_limit_mb: int = 256, mock_stdout: Optional[str] = None, **kwargs) -> ExecutionResult:
        if "SYNTAX_ERROR" in source_code or "compile_fail" in source_code:
            return ExecutionResult(status="COMPILATION_ERROR", compile_output="Mock compile error")
        if "TIMEOUT" in source_code:
            return ExecutionResult(status="TIME_LIMIT_EXCEEDED", stderr="Mock timeout")
        if "RUNTIME_ERROR" in source_code:
            return ExecutionResult(status="RUNTIME_ERROR", stderr="Mock zero division error")

        out = mock_stdout if mock_stdout is not None else self.mock_stdout
        if out is None:
            if "print(5)" in source_code:
                out = "5"
            else:
                try:
                    parts = stdin.strip().split()
                    if len(parts) == 2 and all(p.lstrip('-').isdigit() for p in parts):
                        out = str(int(parts[0]) + int(parts[1]))
                    else:
                        out = stdin.strip()
                except Exception:
                    out = stdin.strip()

        return ExecutionResult(
            status="ACCEPTED" if self.should_pass else "WRONG_ANSWER",
            stdout=out,
            time_ms=45,
            memory_kb=1024,
            is_success=self.should_pass
        )


def get_executor() -> BaseExecutor:
    mode = getattr(settings, 'EXECUTION_SERVICE_MODE', 'sandbox').lower()
    if mode == 'judge0' and getattr(settings, 'JUDGE0_API_KEY', None):
        return Judge0Executor()
    elif mode == 'mock':
        return MockExecutor()
    return SandboxedProcessExecutor()


def normalize_output(text: str) -> str:
    """Normalize output for fair comparison (stripping whitespace and normalizing linebreaks)."""
    if not text:
        return ""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(lines)


def evaluate_test_cases(question, language: str, source_code: str, test_cases, executor: Optional[BaseExecutor] = None) -> Dict[str, Any]:
    """
    Runs code against a set of test cases and calculates outcomes.
    """
    if executor is None:
        executor = get_executor()

    results = []
    all_passed = True
    first_failure_status = None
    compiler_output = ""
    max_time_ms = 0
    max_memory_kb = 0
    passed_count = 0
    total_count = len(test_cases)
    
    time_limit = float(question.time_limit_seconds)
    memory_limit = int(question.memory_limit_mb)

    for tc in test_cases:
        res = executor.execute(
            language=language,
            source_code=source_code,
            stdin=tc.input_data,
            time_limit_sec=time_limit,
            memory_limit_mb=memory_limit
        )

        max_time_ms = max(max_time_ms, res.time_ms)
        max_memory_kb = max(max_memory_kb, res.memory_kb)

        if res.status == "COMPILATION_ERROR":
            compiler_output = res.compile_output or res.stderr
            return {
                "status": "COMPILATION_ERROR",
                "passed_count": 0,
                "total_count": total_count,
                "marks_awarded": 0.0,
                "compiler_output": compiler_output,
                "execution_time_ms": max_time_ms,
                "memory_kb": max_memory_kb,
                "test_results": [{
                    "test_case_id": tc.id,
                    "is_sample": tc.is_sample,
                    "status": "COMPILATION_ERROR",
                    "passed": False,
                    "error_message": compiler_output,
                    "time_ms": 0,
                }]
            }

        # Compare outputs
        norm_actual = normalize_output(res.stdout)
        norm_expected = normalize_output(tc.expected_output)

        passed = (res.status == "ACCEPTED" and norm_actual == norm_expected)
        tc_status = "ACCEPTED" if passed else (res.status if res.status != "ACCEPTED" else "WRONG_ANSWER")

        if passed:
            passed_count += 1
        else:
            all_passed = False
            if not first_failure_status:
                first_failure_status = tc_status

        # Store result (hide expected output details if private test case)
        results.append({
            "test_case_id": tc.id,
            "is_sample": tc.is_sample,
            "status": tc_status,
            "passed": passed,
            "time_ms": res.time_ms,
            "user_stdout": res.stdout if tc.is_sample else (norm_actual[:100] + "..." if len(norm_actual) > 100 else norm_actual),
            "expected_output": tc.expected_output if tc.is_sample else "[Hidden Test Case]",
            "input_data": tc.input_data if tc.is_sample else "[Hidden Input]",
            "error_message": res.stderr if tc.is_sample else (res.stderr[:200] if res.stderr else ""),
        })

    # Marks calculation: proportional to passed test cases
    if total_count > 0:
        score_ratio = passed_count / total_count
        marks_awarded = round(float(question.max_marks) * score_ratio, 2)
    else:
        marks_awarded = float(question.max_marks) if all_passed else 0.0

    final_status = "ACCEPTED" if all_passed and total_count > 0 else (first_failure_status or "WRONG_ANSWER")

    return {
        "status": final_status,
        "passed_count": passed_count,
        "total_count": total_count,
        "marks_awarded": marks_awarded,
        "compiler_output": compiler_output,
        "execution_time_ms": max_time_ms,
        "memory_kb": max_memory_kb,
        "test_results": results,
    }
