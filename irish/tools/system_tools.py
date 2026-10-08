import subprocess

def run_command(cmd):

    try:

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )

        return result.stdout + result.stderr

    except Exception as e:

        return str(e)