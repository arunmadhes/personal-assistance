import subprocess
import tempfile

def run_python(code):

    try:

        with tempfile.NamedTemporaryFile(delete=False,suffix=".py") as f:

            f.write(code.encode())

            path = f.name

        result = subprocess.run(
            ["python",path],
            capture_output=True,
            text=True
        )

        return result.stdout + result.stderr

    except Exception as e:

        return str(e)